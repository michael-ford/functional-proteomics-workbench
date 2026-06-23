"""Shared tool registry skeleton for API, web chat, MCP, and eval callers."""

from __future__ import annotations

import inspect
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

ToolSurface = Literal["web_chat", "mcp", "eval", "api"]
ToolStatus = Literal["ok", "error"]
ToolPayload = BaseModel | dict[str, Any]
ToolHandler = Callable[[BaseModel, "ToolContext"], ToolPayload | Awaitable[ToolPayload]]


class ToolPermissions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: Literal["project", "global"]
    mutates_state: bool
    reads_corpus: bool = False
    external_model_call: bool = False


class TracePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    redact_input_keys: list[str] = Field(default_factory=list)
    redact_output_keys: list[str] = Field(default_factory=list)


class TraceOrigin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surface: ToolSurface
    client: str | None = None
    token_id: str | None = None


class TraceError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    retryable: bool = False


class ToolCallTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    project_id: str | None
    origin: TraceOrigin
    tool_name: str
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    status: ToolStatus
    error: TraceError | None = None
    started_at: datetime
    ended_at: datetime
    latency_ms: int
    chat_session_id: str | None = None
    chat_message_id: str | None = None
    eval_run_id: str | None = None


class ToolInvocationResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    output: BaseModel | None
    trace: ToolCallTrace

    @property
    def error(self) -> TraceError | None:
        return self.trace.error


class TraceSink(Protocol):
    def record(self, trace: ToolCallTrace) -> None:
        """Persist or buffer a completed tool call trace."""


class InMemoryTraceSink:
    """Trace sink for tests and local callers until durable trace storage lands."""

    def __init__(self) -> None:
        self.traces: list[ToolCallTrace] = []

    def record(self, trace: ToolCallTrace) -> None:
        self.traces.append(trace)


@dataclass(frozen=True)
class ToolContext:
    origin: TraceOrigin
    trace_sink: TraceSink
    project_id: str | None = None
    chat_session_id: str | None = None
    chat_message_id: str | None = None
    eval_run_id: str | None = None
    state: dict[str, Any] = field(default_factory=dict)


class ToolDefinition(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    error_codes: list[str]
    permissions: ToolPermissions
    trace: TracePolicy
    eval_tags: list[str] = Field(default_factory=list)
    handler: ToolHandler


class ToolRegistryError(ValueError):
    """Raised for registry configuration and lookup errors."""


class ToolExecutionError(RuntimeError):
    """Structured tool-handler failure converted into a trace error."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class ToolRegistry:
    """Registry that owns validation, dispatch, and trace emission for tool calls."""

    def __init__(self) -> None:
        self._definitions: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._definitions:
            raise ToolRegistryError(f"tool already registered: {definition.name}")
        self._definitions[definition.name] = definition

    def lookup(self, name: str) -> ToolDefinition:
        try:
            return self._definitions[name]
        except KeyError as exc:
            raise ToolRegistryError(f"unknown tool: {name}") from exc

    def list_definitions(self) -> list[ToolDefinition]:
        return [self._definitions[name] for name in sorted(self._definitions)]

    async def invoke(
        self,
        name: str,
        payload: dict[str, Any],
        context: ToolContext,
    ) -> ToolInvocationResult:
        definition = self.lookup(name)
        started_at = datetime.now(UTC)
        monotonic_start = time.perf_counter()
        trace_input: dict[str, Any] = _redact_mapping(payload, definition.trace.redact_input_keys)

        try:
            tool_input = definition.input_model.model_validate(payload)
        except ValidationError as exc:
            trace = _close_trace(
                definition=definition,
                context=context,
                started_at=started_at,
                monotonic_start=monotonic_start,
                trace_input=trace_input,
                output=None,
                status="error",
                error=TraceError(
                    code=_declared_error_code(definition, "invalid_input"),
                    message=str(exc),
                    retryable=False,
                ),
            )
            context.trace_sink.record(trace)
            return ToolInvocationResult(output=None, trace=trace)

        trace_input = _redact_model(tool_input, definition.trace.redact_input_keys)

        try:
            raw_output = definition.handler(tool_input, context)
            if inspect.isawaitable(raw_output):
                raw_output = await raw_output
            output = definition.output_model.model_validate(raw_output)
            trace = _close_trace(
                definition=definition,
                context=context,
                started_at=started_at,
                monotonic_start=monotonic_start,
                trace_input=trace_input,
                output=_redact_model(output, definition.trace.redact_output_keys),
                status="ok",
                error=None,
            )
            context.trace_sink.record(trace)
            return ToolInvocationResult(output=output, trace=trace)
        except ValidationError as exc:
            trace = _close_trace(
                definition=definition,
                context=context,
                started_at=started_at,
                monotonic_start=monotonic_start,
                trace_input=trace_input,
                output=None,
                status="error",
                error=TraceError(
                    code=_declared_error_code(definition, "internal_error"),
                    message=str(exc),
                    retryable=False,
                ),
            )
        except ToolExecutionError as exc:
            trace = _close_trace(
                definition=definition,
                context=context,
                started_at=started_at,
                monotonic_start=monotonic_start,
                trace_input=trace_input,
                output=None,
                status="error",
                error=TraceError(
                    code=_declared_error_code(definition, exc.code),
                    message=exc.message,
                    retryable=exc.retryable,
                ),
            )
        except Exception as exc:  # pragma: no cover - defensive boundary for future handlers
            trace = _close_trace(
                definition=definition,
                context=context,
                started_at=started_at,
                monotonic_start=monotonic_start,
                trace_input=trace_input,
                output=None,
                status="error",
                error=TraceError(
                    code=_declared_error_code(definition, "internal_error"),
                    message=str(exc),
                    retryable=False,
                ),
            )

        context.trace_sink.record(trace)
        return ToolInvocationResult(output=None, trace=trace)


def _close_trace(
    *,
    definition: ToolDefinition,
    context: ToolContext,
    started_at: datetime,
    monotonic_start: float,
    trace_input: dict[str, Any],
    output: dict[str, Any] | None,
    status: ToolStatus,
    error: TraceError | None,
) -> ToolCallTrace:
    ended_at = datetime.now(UTC)
    latency_ms = max(0, round((time.perf_counter() - monotonic_start) * 1000))
    return ToolCallTrace(
        id=f"tc_{uuid4().hex}",
        project_id=context.project_id,
        origin=context.origin,
        tool_name=definition.name,
        input=trace_input,
        output=output,
        status=status,
        error=error,
        started_at=started_at,
        ended_at=ended_at,
        latency_ms=latency_ms,
        chat_session_id=context.chat_session_id,
        chat_message_id=context.chat_message_id,
        eval_run_id=context.eval_run_id,
    )


def _declared_error_code(definition: ToolDefinition, code: str) -> str:
    if code in definition.error_codes:
        return code
    if "internal_error" in definition.error_codes:
        return "internal_error"
    return code


def _redact_model(model: BaseModel, keys: list[str]) -> dict[str, Any]:
    return _redact_mapping(model.model_dump(mode="json"), keys)


def _redact_mapping(payload: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    redacted = dict(payload)
    for key in keys:
        if key in redacted:
            redacted[key] = "[redacted]"
    return redacted
