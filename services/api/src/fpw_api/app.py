from typing import Any, Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from fpw_api.chat import (
    ChatModelAdapter,
    InMemoryChatStore,
    create_chat_router,
    create_default_chat_model_adapter,
)
from fpw_api.mcp import create_mcp_router
from fpw_api.tools import ToolRegistry, create_default_tool_registry
from fpw_api.tools.registry import InMemoryTraceSink, TraceSink


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["functional-proteomics-api"]


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    service: Literal["functional-proteomics-api"]
    checks: dict[str, Literal["ok"]] = Field(default_factory=lambda: {"app": "ok"})


def create_app(
    tool_registry: ToolRegistry | None = None,
    trace_sink: TraceSink | None = None,
    project_state: dict[str, Any] | None = None,
    chat_store: InMemoryChatStore | None = None,
    chat_model_adapter: ChatModelAdapter | None = None,
) -> FastAPI:
    application = FastAPI(
        title="Functional Proteomics Workbench API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.state.tool_registry = tool_registry or create_default_tool_registry()
    application.state.trace_sink = trace_sink or InMemoryTraceSink()
    application.state.project_state = project_state if project_state is not None else {}
    application.state.chat_store = chat_store or InMemoryChatStore()
    application.state.chat_model_adapter = chat_model_adapter or create_default_chat_model_adapter()
    application.include_router(create_chat_router())
    application.include_router(create_mcp_router())

    @application.get("/health", response_model=HealthResponse, tags=["operational"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", service="functional-proteomics-api")

    @application.get("/ready", response_model=ReadinessResponse, tags=["operational"])
    async def ready() -> ReadinessResponse:
        return ReadinessResponse(status="ready", service="functional-proteomics-api")

    return application


app = create_app()
