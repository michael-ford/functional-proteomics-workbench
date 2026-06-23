"""Shared tool registry exports."""

from fpw_api.tools.adapters import invoke_for_mcp, invoke_for_web_chat
from fpw_api.tools.mvp import create_default_tool_registry, mvp_tool_definitions
from fpw_api.tools.registry import (
    InMemoryTraceSink,
    ToolCallTrace,
    ToolContext,
    ToolDefinition,
    ToolExecutionError,
    ToolInvocationResult,
    ToolPermissions,
    ToolRegistry,
    ToolRegistryError,
    TraceError,
    TraceOrigin,
    TracePolicy,
    TraceSink,
)

__all__ = [
    "InMemoryTraceSink",
    "ToolCallTrace",
    "ToolContext",
    "ToolDefinition",
    "ToolExecutionError",
    "ToolInvocationResult",
    "ToolPermissions",
    "ToolRegistry",
    "ToolRegistryError",
    "TraceError",
    "TraceOrigin",
    "TracePolicy",
    "TraceSink",
    "create_default_tool_registry",
    "invoke_for_mcp",
    "invoke_for_web_chat",
    "mvp_tool_definitions",
]
