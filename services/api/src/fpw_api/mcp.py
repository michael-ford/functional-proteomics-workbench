"""Mounted MCP JSON-RPC surface backed by the shared tool registry."""

from __future__ import annotations

import os
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from fpw_api.tools import InMemoryTraceSink, ToolRegistry, TraceSink, invoke_for_mcp
from fpw_api.tools.registry import ToolRegistryError

JSONRPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2025-03-26"
MCP_TOKEN_ENV = "MCP_DEMO_TOKEN"
MCP_DEMO_TOKEN_ID = "demo"


class JsonRpcRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    jsonrpc: Literal["2.0"] = JSONRPC_VERSION
    id: int | str | None = None
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


def create_mcp_router() -> APIRouter:
    router = APIRouter(prefix="/mcp", tags=["mcp"])

    @router.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "functional-proteomics-mcp"}

    @router.post("")
    async def handle_json_rpc(
        payload: JsonRpcRequest,
        request: Request,
        _: None = Depends(_require_demo_token),
    ) -> dict[str, Any]:
        registry = _registry_from_app(request)
        trace_sink = _trace_sink_from_app(request)

        if payload.method == "initialize":
            return _success(
                payload.id,
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {
                        "name": "functional-proteomics-workbench",
                        "version": "0.1.0",
                    },
                },
            )

        if payload.method == "tools/list":
            return _success(payload.id, {"tools": _tool_schemas(registry)})

        if payload.method == "tools/call":
            return await _call_tool(payload, request, registry, trace_sink)

        return _error(payload.id, code=-32601, message=f"method not found: {payload.method}")

    return router


async def _require_demo_token(authorization: str | None = Header(default=None)) -> None:
    expected_token = os.environ.get(MCP_TOKEN_ENV)
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{MCP_TOKEN_ENV} is not configured.",
        )
    if authorization != f"Bearer {expected_token}":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid MCP bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def _call_tool(
    payload: JsonRpcRequest,
    request: Request,
    registry: ToolRegistry,
    trace_sink: TraceSink,
) -> dict[str, Any]:
    name = payload.params.get("name")
    arguments = payload.params.get("arguments", {})
    if not isinstance(name, str) or not name:
        return _error(payload.id, code=-32602, message="tools/call requires params.name.")
    if not isinstance(arguments, dict):
        return _error(
            payload.id,
            code=-32602,
            message="tools/call params.arguments must be an object.",
        )

    try:
        result = await invoke_for_mcp(
            registry,
            name,
            arguments,
            trace_sink=trace_sink,
            project_id=_optional_string(payload.params.get("project_id")),
            client=_mcp_client_name(request),
            token_id=MCP_DEMO_TOKEN_ID,
        )
    except ToolRegistryError as exc:
        return _error(payload.id, code=-32602, message=str(exc))

    if result.output is not None:
        structured_content: dict[str, Any] = result.output.model_dump(mode="json")
    else:
        structured_content = {
            "error": result.error.model_dump(mode="json") if result.error else None,
            "trace_id": result.trace.id,
        }

    return _success(
        payload.id,
        {
            "content": [
                {
                    "type": "text",
                    "text": _tool_text_content(structured_content, is_error=result.output is None),
                }
            ],
            "structuredContent": structured_content,
            "isError": result.output is None,
            "_meta": {"trace_id": result.trace.id},
        },
    )


def _tool_schemas(registry: ToolRegistry) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for definition in registry.list_definitions():
        tools.append(
            {
                "name": definition.name,
                "description": definition.description,
                "inputSchema": definition.input_model.model_json_schema(),
                "outputSchema": definition.output_model.model_json_schema(),
                "_meta": {
                    "errorCodes": definition.error_codes,
                    "permissions": definition.permissions.model_dump(mode="json"),
                },
            }
        )
    return tools


def _registry_from_app(request: Request) -> ToolRegistry:
    return request.app.state.tool_registry


def _trace_sink_from_app(request: Request) -> TraceSink:
    trace_sink = getattr(request.app.state, "trace_sink", None)
    if trace_sink is None:
        trace_sink = InMemoryTraceSink()
        request.app.state.trace_sink = trace_sink
    return trace_sink


def _mcp_client_name(request: Request) -> str | None:
    explicit_client = request.headers.get("x-mcp-client")
    if explicit_client:
        return explicit_client
    return request.headers.get("user-agent")


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _success(rpc_id: int | str | None, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": rpc_id, "result": result}


def _error(rpc_id: int | str | None, *, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": JSONRPC_VERSION,
        "id": rpc_id,
        "error": {"code": code, "message": message},
    }


def _tool_text_content(payload: dict[str, Any], *, is_error: bool) -> str:
    if not is_error:
        return "Tool call completed."
    error = payload.get("error")
    if isinstance(error, dict):
        code = error.get("code", "tool_error")
        message = error.get("message", "Tool call failed.")
        return f"{code}: {message}"
    return "Tool call failed."
