from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["functional-proteomics-api"]


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    service: Literal["functional-proteomics-api"]
    checks: dict[str, Literal["ok"]] = Field(default_factory=lambda: {"app": "ok"})


def create_app() -> FastAPI:
    application = FastAPI(
        title="Functional Proteomics Workbench API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    @application.get("/health", response_model=HealthResponse, tags=["operational"])
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", service="functional-proteomics-api")

    @application.get("/ready", response_model=ReadinessResponse, tags=["operational"])
    async def ready() -> ReadinessResponse:
        return ReadinessResponse(status="ready", service="functional-proteomics-api")

    return application


app = create_app()
