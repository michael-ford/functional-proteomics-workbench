"""Surface-specific adapter shims that dispatch through the shared registry."""

from __future__ import annotations

from typing import Any

from fpw_api.tools.registry import (
    InMemoryTraceSink,
    ToolContext,
    ToolInvocationResult,
    ToolRegistry,
    TraceOrigin,
    TraceSink,
)


async def invoke_for_web_chat(
    registry: ToolRegistry,
    name: str,
    payload: dict[str, Any],
    *,
    trace_sink: TraceSink | None = None,
    project_id: str | None = None,
    client: str = "web",
    chat_session_id: str | None = None,
    chat_message_id: str | None = None,
    state: dict[str, Any] | None = None,
) -> ToolInvocationResult:
    context = ToolContext(
        origin=TraceOrigin(surface="web_chat", client=client),
        trace_sink=trace_sink or InMemoryTraceSink(),
        project_id=project_id,
        chat_session_id=chat_session_id,
        chat_message_id=chat_message_id,
        state=state if state is not None else {},
    )
    return await registry.invoke(name, payload, context)


async def invoke_for_mcp(
    registry: ToolRegistry,
    name: str,
    payload: dict[str, Any],
    *,
    trace_sink: TraceSink | None = None,
    project_id: str | None = None,
    client: str | None = None,
    token_id: str | None = None,
    state: dict[str, Any] | None = None,
) -> ToolInvocationResult:
    context = ToolContext(
        origin=TraceOrigin(surface="mcp", client=client, token_id=token_id),
        trace_sink=trace_sink or InMemoryTraceSink(),
        project_id=project_id,
        state=state if state is not None else {},
    )
    return await registry.invoke(name, payload, context)
