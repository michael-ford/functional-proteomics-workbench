"""Web chat API path backed by the shared tool registry."""

from __future__ import annotations

import asyncio
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from shared_schemas import new_id

from fpw_api.tools import InMemoryTraceSink, ToolRegistry, TraceSink, invoke_for_web_chat
from fpw_api.tools.mvp import DEMO_PROJECT_ID
from fpw_api.tools.registry import ToolRegistryError

DEFAULT_CHAT_MODEL = "mock/openrouter-kimi-structural"
DEFAULT_OPENROUTER_MODEL = "moonshotai/kimi-k2"
OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = DEMO_PROJECT_ID
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=4000)


class ChatMessageView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    role: Literal["user", "assistant", "tool"]
    content: str | None = None
    tool_call_ids: list[str] = Field(default_factory=list)
    model_meta: dict[str, Any] | None = None
    created_at: datetime


class ChatToolTraceView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    project_id: str | None = None
    origin: dict[str, Any]
    tool_name: str
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    status: Literal["ok", "error"]
    error: dict[str, Any] | None = None
    started_at: datetime
    ended_at: datetime
    latency_ms: int
    chat_session_id: str | None = None
    chat_message_id: str | None = None


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    project_id: str
    model: str
    messages: list[ChatMessageView]
    assistant_message: ChatMessageView
    tool_traces: list[ChatToolTraceView] = Field(default_factory=list)


class ChatToolDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    arguments: dict[str, Any]
    rationale: str


class ChatModelAdapter(Protocol):
    model_name: str

    async def choose_tool(
        self,
        *,
        message: str,
        project_id: str,
        registry: ToolRegistry,
    ) -> ChatToolDecision | None:
        """Return the next safe tool call, or None for a text-only response."""
        ...

    def render_response(
        self,
        *,
        decision: ChatToolDecision | None,
        tool_output: dict[str, Any] | None,
        tool_error: dict[str, Any] | None,
    ) -> str:
        """Render a deterministic assistant response from the model decision and tool result."""
        ...


class MockChatModelAdapter:
    """CI-safe model adapter for the structural web-chat path."""

    model_name = DEFAULT_CHAT_MODEL

    async def choose_tool(
        self,
        *,
        message: str,
        project_id: str,
        registry: ToolRegistry,
    ) -> ChatToolDecision | None:
        normalized = message.casefold()
        wants_status = any(
            token in normalized
            for token in ("project", "status", "state", "dataset", "trace", "workspace")
        )
        if not wants_status:
            return None

        registry.lookup("get_project_status")
        return ChatToolDecision(
            tool_name="get_project_status",
            arguments={"project_id": project_id},
            rationale="Read the shared project state through the registry.",
        )

    def render_response(
        self,
        *,
        decision: ChatToolDecision | None,
        tool_output: dict[str, Any] | None,
        tool_error: dict[str, Any] | None,
    ) -> str:
        if decision is None:
            return "I can inspect the shared project state for this demo workspace."
        if tool_error is not None:
            code = tool_error.get("code", "tool_error")
            message = tool_error.get("message", "Tool call failed.")
            return f"{decision.tool_name} returned {code}: {message}"
        if decision.tool_name == "get_project_status" and tool_output is not None:
            project = tool_output.get("project", {})
            summary_counts = tool_output.get("summary_counts", {})
            if isinstance(project, dict) and isinstance(summary_counts, dict):
                title = str(project.get("title", "Project"))
                status_value = str(project.get("status", "unknown"))
                dataset_count = int(summary_counts.get("datasets", 0))
                trace_count = int(summary_counts.get("tool_calls", 0))
                return (
                    f"{title} is {status_value}. "
                    f"Datasets: {dataset_count}. Prior tool traces: {trace_count}."
                )
        return f"{decision.tool_name} completed through the shared ToolRegistry."


class OpenRouterChatModelAdapter:
    """OpenRouter/Kimi adapter with deterministic fallback for demo/test environments."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = DEFAULT_OPENROUTER_MODEL,
        fallback: ChatModelAdapter | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._api_key = api_key
        self.model_name = model_name
        self._fallback = fallback or MockChatModelAdapter()
        self._timeout_seconds = timeout_seconds

    async def choose_tool(
        self,
        *,
        message: str,
        project_id: str,
        registry: ToolRegistry,
    ) -> ChatToolDecision | None:
        available_tools = [
            {"name": definition.name, "description": definition.description}
            for definition in registry.list_definitions()
            if definition.name == "get_project_status"
        ]
        try:
            raw_decision = await asyncio.to_thread(
                self._request_decision,
                message,
                project_id,
                available_tools,
            )
        except OpenRouterAdapterError:
            return await self._fallback.choose_tool(
                message=message,
                project_id=project_id,
                registry=registry,
            )

        if raw_decision is None:
            return None
        try:
            decision = ChatToolDecision.model_validate(raw_decision)
            registry.lookup(decision.tool_name)
        except (ValidationError, ToolRegistryError):
            return await self._fallback.choose_tool(
                message=message,
                project_id=project_id,
                registry=registry,
            )
        return decision

    def render_response(
        self,
        *,
        decision: ChatToolDecision | None,
        tool_output: dict[str, Any] | None,
        tool_error: dict[str, Any] | None,
    ) -> str:
        rendered = self._fallback.render_response(
            decision=decision,
            tool_output=tool_output,
            tool_error=tool_error,
        )
        return rendered

    def _request_decision(
        self,
        message: str,
        project_id: str,
        available_tools: list[dict[str, str]],
    ) -> dict[str, Any] | None:
        request_body = {
            "model": self.model_name,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the functional proteomics workbench router. "
                        "Return JSON only. If a safe project-state tool should be called, "
                        "return an object with tool_name, arguments, and rationale. "
                        "If no tool is needed, return {\"tool_name\": null}. "
                        "Only choose from the supplied tools."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "project_id": project_id,
                            "message": message,
                            "available_tools": available_tools,
                            "default_status_tool": {
                                "tool_name": "get_project_status",
                                "arguments": {"project_id": project_id},
                            },
                        },
                        sort_keys=True,
                    ),
                },
            ],
        }
        request = urllib.request.Request(
            OPENROUTER_CHAT_COMPLETIONS_URL,
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.environ.get("APP_BASE_URL", "http://localhost:8000"),
                "X-Title": "Functional Proteomics Workbench",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise OpenRouterAdapterError(f"provider_http_{exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise OpenRouterAdapterError("provider_unavailable") from exc

        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenRouterAdapterError("provider_response_invalid") from exc

        parsed = _parse_json_object(str(content))
        if parsed.get("tool_name") is None:
            return None
        return {
            "tool_name": parsed.get("tool_name"),
            "arguments": parsed.get("arguments") or {"project_id": project_id},
            "rationale": parsed.get("rationale") or "OpenRouter selected a safe registry tool.",
        }


class OpenRouterAdapterError(RuntimeError):
    def __init__(self, public_message: str) -> None:
        super().__init__(public_message)
        self.public_message = public_message


def create_default_chat_model_adapter() -> ChatModelAdapter:
    provider = os.environ.get("MODEL_PROVIDER", "openrouter").casefold()
    force_mock = os.environ.get("FPW_USE_MOCK_MODEL", "").casefold() in {"1", "true", "yes"}
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if provider == "openrouter" and api_key and not force_mock:
        return OpenRouterChatModelAdapter(
            api_key=api_key,
            model_name=os.environ.get("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL),
        )
    return MockChatModelAdapter()


def _parse_json_object(content: str) -> dict[str, Any]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise OpenRouterAdapterError("provider_response_not_json") from exc
    if not isinstance(parsed, dict):
        raise OpenRouterAdapterError("provider_response_invalid")
    return parsed


@dataclass
class ChatSessionState:
    id: str
    project_id: str
    model: str
    created_at: datetime
    messages: list[ChatMessageView] = field(default_factory=list)


class InMemoryChatStore:
    def __init__(self) -> None:
        self._sessions: dict[str, ChatSessionState] = {}

    def get_or_create_session(
        self,
        *,
        project_id: str,
        model: str,
        session_id: str | None,
    ) -> ChatSessionState:
        if session_id is not None:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(session_id)
            if session.project_id != project_id:
                raise ValueError("chat session project_id mismatch")
            return session

        created_at = datetime.now(UTC)
        session = ChatSessionState(
            id=new_id("chat_"),
            project_id=project_id,
            model=model,
            created_at=created_at,
        )
        self._sessions[session.id] = session
        return session

    def add_message(
        self,
        session: ChatSessionState,
        *,
        role: Literal["user", "assistant", "tool"],
        content: str | None,
        tool_call_ids: list[str] | None = None,
        model_meta: dict[str, Any] | None = None,
        message_id: str | None = None,
    ) -> ChatMessageView:
        message = ChatMessageView(
            id=message_id or new_id("msg_"),
            session_id=session.id,
            role=role,
            content=content,
            tool_call_ids=tool_call_ids or [],
            model_meta=model_meta,
            created_at=datetime.now(UTC),
        )
        session.messages.append(message)
        return message


def create_chat_router() -> APIRouter:
    router = APIRouter(prefix="/chat", tags=["chat"])

    @router.post("", response_model=ChatResponse)
    async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
        registry = _registry_from_app(request)
        trace_sink = _trace_sink_from_app(request)
        project_state = _project_state_from_app(request)
        chat_store = _chat_store_from_app(request)
        adapter = _chat_model_from_app(request)

        try:
            session = chat_store.get_or_create_session(
                project_id=payload.project_id,
                model=adapter.model_name,
                session_id=payload.session_id,
            )
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"chat session not found: {payload.session_id}",
            ) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

        chat_store.add_message(session, role="user", content=payload.message)
        started = time.perf_counter()
        decision = await adapter.choose_tool(
            message=payload.message,
            project_id=payload.project_id,
            registry=registry,
        )

        trace_views: list[ChatToolTraceView] = []
        tool_output: dict[str, Any] | None = None
        tool_error: dict[str, Any] | None = None
        tool_call_ids: list[str] = []
        if decision is not None:
            tool_message_id = new_id("msg_")
            try:
                result = await invoke_for_web_chat(
                    registry,
                    decision.tool_name,
                    decision.arguments,
                    trace_sink=trace_sink,
                    project_id=payload.project_id,
                    chat_session_id=session.id,
                    chat_message_id=tool_message_id,
                    state=project_state,
                )
            except ToolRegistryError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(exc),
                ) from exc

            tool_output = result.output.model_dump(mode="json") if result.output else None
            tool_error = result.error.model_dump(mode="json") if result.error else None
            tool_call_ids = [result.trace.id]
            trace_views.append(_trace_view(result.trace.model_dump(mode="json")))
            chat_store.add_message(
                session,
                role="tool",
                content=_tool_message_content(decision.tool_name, result.trace.status),
                tool_call_ids=tool_call_ids,
                message_id=tool_message_id,
            )

        assistant_content = adapter.render_response(
            decision=decision,
            tool_output=tool_output,
            tool_error=tool_error,
        )
        assistant_message = chat_store.add_message(
            session,
            role="assistant",
            content=assistant_content,
            tool_call_ids=tool_call_ids,
            model_meta={
                "adapter": adapter.model_name,
                "finish_reason": "tool_call" if decision else "stop",
                "latency_ms": max(0, round((time.perf_counter() - started) * 1000)),
            },
        )

        return ChatResponse(
            session_id=session.id,
            project_id=session.project_id,
            model=session.model,
            messages=session.messages,
            assistant_message=assistant_message,
            tool_traces=trace_views,
        )

    return router


def _trace_view(trace: dict[str, Any]) -> ChatToolTraceView:
    return ChatToolTraceView(
        id=str(trace["id"]),
        project_id=trace.get("project_id") if isinstance(trace.get("project_id"), str) else None,
        origin=dict(trace["origin"]),
        tool_name=str(trace["tool_name"]),
        input=dict(trace["input"]),
        output=dict(trace["output"]) if isinstance(trace.get("output"), dict) else None,
        status=trace["status"],
        error=dict(trace["error"]) if isinstance(trace.get("error"), dict) else None,
        started_at=trace["started_at"],
        ended_at=trace["ended_at"],
        latency_ms=int(trace["latency_ms"]),
        chat_session_id=(
            trace.get("chat_session_id")
            if isinstance(trace.get("chat_session_id"), str)
            else None
        ),
        chat_message_id=(
            trace.get("chat_message_id")
            if isinstance(trace.get("chat_message_id"), str)
            else None
        ),
    )


def _tool_message_content(tool_name: str, status_value: str) -> str:
    return f"{tool_name} {status_value}"


def _registry_from_app(request: Request) -> ToolRegistry:
    return request.app.state.tool_registry


def _trace_sink_from_app(request: Request) -> TraceSink:
    trace_sink = getattr(request.app.state, "trace_sink", None)
    if trace_sink is None:
        trace_sink = InMemoryTraceSink()
        request.app.state.trace_sink = trace_sink
    return trace_sink


def _project_state_from_app(request: Request) -> dict[str, Any]:
    project_state = getattr(request.app.state, "project_state", None)
    if project_state is None:
        project_state = {}
        request.app.state.project_state = project_state
    return project_state


def _chat_store_from_app(request: Request) -> InMemoryChatStore:
    chat_store = getattr(request.app.state, "chat_store", None)
    if chat_store is None:
        chat_store = InMemoryChatStore()
        request.app.state.chat_store = chat_store
    return chat_store


def _chat_model_from_app(request: Request) -> ChatModelAdapter:
    adapter = getattr(request.app.state, "chat_model_adapter", None)
    if adapter is None:
        adapter = MockChatModelAdapter()
        request.app.state.chat_model_adapter = adapter
    return adapter
