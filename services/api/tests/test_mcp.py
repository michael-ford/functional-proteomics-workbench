from typing import Literal

from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

from fpw_api import create_app
from fpw_api.tools import (
    InMemoryTraceSink,
    ToolContext,
    ToolDefinition,
    ToolPermissions,
    ToolRegistry,
    TracePolicy,
    create_default_tool_registry,
)


class EchoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    value: int


class EchoOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    value: int
    surface: Literal["mcp"]


def test_mcp_startup_smoke(monkeypatch) -> None:
    monkeypatch.setenv("MCP_DEMO_TOKEN", "test-token")
    app = create_app()

    with TestClient(app) as client:
        health = client.get("/mcp/health")
        initialized = client.post(
            "/mcp",
            headers={"Authorization": "Bearer test-token"},
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        )
        notification = client.post(
            "/mcp",
            headers={"Authorization": "Bearer test-token"},
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )

    assert health.status_code == 200
    assert health.json() == {"status": "ok", "service": "functional-proteomics-mcp"}
    assert initialized.status_code == 200
    assert initialized.json()["result"]["capabilities"] == {"tools": {"listChanged": False}}
    assert notification.status_code == 202
    assert notification.content == b""


def test_mcp_requires_configured_demo_token(monkeypatch) -> None:
    monkeypatch.delenv("MCP_DEMO_TOKEN", raising=False)
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            headers={"Authorization": "Bearer test-token"},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        )

    assert response.status_code == 503
    assert response.json()["detail"] == "MCP_DEMO_TOKEN is not configured."


def test_mcp_tool_schema_parity_uses_shared_registry(monkeypatch) -> None:
    monkeypatch.setenv("MCP_DEMO_TOKEN", "test-token")
    registry = create_default_tool_registry()
    app = create_app(tool_registry=registry)

    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            headers={"Authorization": "Bearer test-token"},
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        )

    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    by_name = {tool["name"]: tool for tool in tools}
    for definition in registry.list_definitions():
        assert (
            by_name[definition.name]["inputSchema"]
            == definition.input_model.model_json_schema()
        )
        assert (
            by_name[definition.name]["outputSchema"]
            == definition.output_model.model_json_schema()
        )
        assert (
            by_name[definition.name]["_meta"]["permissions"]
            == definition.permissions.model_dump(mode="json")
        )


def test_mcp_tool_call_dispatches_shared_handler_and_records_trace(monkeypatch) -> None:
    monkeypatch.setenv("MCP_DEMO_TOKEN", "test-token")
    registry = ToolRegistry()
    calls: list[tuple[EchoInput, ToolContext]] = []

    def handler(tool_input: BaseModel, context: ToolContext) -> EchoOutput:
        typed_input = EchoInput.model_validate(tool_input)
        calls.append((typed_input, context))
        return EchoOutput(
            project_id=typed_input.project_id,
            value=typed_input.value,
            surface="mcp",
        )

    definition = ToolDefinition(
        name="echo",
        description="Echo a value for MCP smoke tests.",
        input_model=EchoInput,
        output_model=EchoOutput,
        error_codes=["invalid_input", "internal_error"],
        permissions=ToolPermissions(scope="project", mutates_state=False),
        trace=TracePolicy(),
        handler=handler,
    )
    registry.register(definition)
    sink = InMemoryTraceSink()
    app = create_app(tool_registry=registry, trace_sink=sink)

    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            headers={"Authorization": "Bearer test-token", "x-mcp-client": "codex"},
            json={
                "jsonrpc": "2.0",
                "id": "call-1",
                "method": "tools/call",
                "params": {"name": "echo", "arguments": {"project_id": "proj_demo", "value": 42}},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["structuredContent"] == {
        "project_id": "proj_demo",
        "value": 42,
        "surface": "mcp",
    }
    assert body["result"]["isError"] is False
    assert len(calls) == 1
    assert calls[0][1].origin.surface == "mcp"
    assert calls[0][1].origin.client == "codex"
    assert calls[0][1].origin.token_id == "demo"
    assert len(sink.traces) == 1
    assert sink.traces[0].id.startswith("tc_")
    assert len(sink.traces[0].id) == 29
    assert sink.traces[0].project_id == "proj_demo"
    assert sink.traces[0].origin.surface == "mcp"
    assert body["result"]["_meta"] == {"trace_id": sink.traces[0].id}


def test_mcp_tool_errors_still_emit_trace(monkeypatch) -> None:
    monkeypatch.setenv("MCP_DEMO_TOKEN", "test-token")
    sink = InMemoryTraceSink()
    app = create_app(tool_registry=create_default_tool_registry(), trace_sink=sink)

    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            headers={"Authorization": "Bearer test-token"},
            json={
                "jsonrpc": "2.0",
                "id": "call-1",
                "method": "tools/call",
                "params": {
                    "name": "validate_dataset",
                    "arguments": {
                        "project_id": "proj_demo",
                        "dataset_id": "ds_01KCYAG0000000000000000001",
                    },
                },
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["isError"] is True
    assert body["result"]["structuredContent"]["error"]["code"] == "out_of_scope"
    assert body["result"]["structuredContent"]["trace_id"] == sink.traces[0].id
    assert sink.traces[0].status == "error"
    assert sink.traces[0].origin.surface == "mcp"


def test_mcp_route_does_not_wrap_unknown_tool_as_trace(monkeypatch) -> None:
    monkeypatch.setenv("MCP_DEMO_TOKEN", "test-token")
    sink = InMemoryTraceSink()
    app = create_app(trace_sink=sink)

    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            headers={"Authorization": "Bearer test-token"},
            json={
                "jsonrpc": "2.0",
                "id": "call-1",
                "method": "tools/call",
                "params": {"name": "not_registered", "arguments": {}},
            },
        )

    assert response.status_code == 200
    assert response.json()["error"]["message"] == "unknown tool: not_registered"
    assert sink.traces == []
