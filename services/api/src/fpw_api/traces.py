"""Trace persistence models and replay/export helpers.

The stable trace contract lives in ``docs/TRACE_MODEL.md``. These service-local models
implement that shape without changing the protected shared schema package in this PR.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, ClassVar, Literal, cast

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from pydantic import Field as PydanticField
from shared_schemas import ArtifactRef, EntityPrefix, validate_prefixed_ulid
from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, Session, SQLModel, col, select

TraceSurface = Literal["web_chat", "mcp", "eval", "api"]
TraceStatus = Literal["ok", "error"]
ChatRole = Literal["user", "assistant", "tool"]
EvalCheckKind = Literal[
    "tool_choice",
    "schema_validity",
    "numeric",
    "citation_support",
    "entity_grounding",
    "unsupported_claim",
    "report_structure",
    "trace_completeness",
]


class TraceContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("created_at", "started_at", "ended_at", check_fields=False)
    @classmethod
    def _require_utc_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("trace timestamps must be timezone-aware UTC datetimes")
        return value.astimezone(UTC)


class TraceOrigin(TraceContractModel):
    surface: TraceSurface
    client: str | None = None
    token_id: str | None = None


class TraceError(TraceContractModel):
    code: str
    message: str
    retryable: bool = False


class ToolCallTrace(TraceContractModel):
    id: str
    project_id: str | None = None
    origin: TraceOrigin
    tool_name: str
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    artifact_refs: list[ArtifactRef] = PydanticField(default_factory=list)
    status: TraceStatus
    error: TraceError | None = None
    started_at: datetime
    ended_at: datetime
    latency_ms: int = PydanticField(ge=0)
    chat_session_id: str | None = None
    chat_message_id: str | None = None
    eval_run_id: str | None = None

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.TOOL_CALL_TRACE)

    @field_validator("project_id")
    @classmethod
    def _validate_project_id(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_prefixed_ulid(value, EntityPrefix.PROJECT, allow_demo_project=True)

    @field_validator("chat_session_id")
    @classmethod
    def _validate_chat_session_id(cls, value: str | None) -> str | None:
        return _validate_optional_prefixed_ulid(value, "chat_")

    @field_validator("chat_message_id")
    @classmethod
    def _validate_chat_message_id(cls, value: str | None) -> str | None:
        return _validate_optional_prefixed_ulid(value, "msg_")

    @field_validator("eval_run_id")
    @classmethod
    def _validate_eval_run_id(cls, value: str | None) -> str | None:
        return _validate_optional_prefixed_ulid(value, "eval_run_")

    @model_validator(mode="after")
    def _validate_trace_consistency(self) -> ToolCallTrace:
        if self.ended_at < self.started_at:
            raise ValueError("ended_at must be greater than or equal to started_at")
        if self.status == "ok" and self.error is not None:
            raise ValueError("ok tool calls must not include an error")
        if self.status == "error" and self.error is None:
            raise ValueError("error tool calls must include a TraceError")
        if self.origin.surface == "web_chat" and self.chat_session_id is None:
            raise ValueError("web_chat tool calls must include chat_session_id")
        if self.origin.surface == "eval" and self.eval_run_id is None:
            raise ValueError("eval tool calls must include eval_run_id")
        return self


class ChatSession(TraceContractModel):
    id: str
    project_id: str
    model: str
    created_at: datetime

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, "chat_")

    @field_validator("project_id")
    @classmethod
    def _validate_project_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.PROJECT, allow_demo_project=True)


class ChatMessage(TraceContractModel):
    id: str
    session_id: str
    role: ChatRole
    content: str | None = None
    tool_call_ids: list[str] = PydanticField(default_factory=list)
    model_meta: dict[str, Any] | None = None
    created_at: datetime

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, "msg_")

    @field_validator("session_id")
    @classmethod
    def _validate_session_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, "chat_")

    @field_validator("tool_call_ids")
    @classmethod
    def _validate_tool_call_ids(cls, value: list[str]) -> list[str]:
        for tool_call_id in value:
            validate_prefixed_ulid(tool_call_id, EntityPrefix.TOOL_CALL_TRACE)
        return value


class EvalCheck(TraceContractModel):
    kind: EvalCheckKind
    passed: bool
    detail: str | None = None


class EvalTraceStep(TraceContractModel):
    tool_call_id: str
    expectation: str | None = None
    checks: list[EvalCheck] = PydanticField(default_factory=list)

    @field_validator("tool_call_id")
    @classmethod
    def _validate_tool_call_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.TOOL_CALL_TRACE)


class ToolCallTraceRecord(SQLModel, table=True):
    __tablename__: ClassVar[str] = "tool_call_traces"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: str = Field(primary_key=True)
    project_id: str | None = Field(default=None, index=True)
    origin: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    tool_name: str = Field(index=True)
    input: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    output: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    artifact_refs: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )
    status: str = Field(index=True)
    error: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    started_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    ended_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    latency_ms: int
    chat_session_id: str | None = Field(default=None, index=True)
    chat_message_id: str | None = Field(default=None, index=True)
    eval_run_id: str | None = Field(default=None, index=True)


class ChatSessionRecord(SQLModel, table=True):
    __tablename__: ClassVar[str] = "chat_sessions"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: str = Field(primary_key=True)
    project_id: str = Field(index=True)
    model: str
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class ChatMessageRecord(SQLModel, table=True):
    __tablename__: ClassVar[str] = "chat_messages"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: str = Field(primary_key=True)
    session_id: str = Field(index=True)
    role: str = Field(index=True)
    content: str | None = None
    tool_call_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    model_meta: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))


class EvalTraceStepRecord(SQLModel, table=True):
    __tablename__: ClassVar[str] = "eval_trace_steps"  # pyright: ignore[reportIncompatibleVariableOverride]

    tool_call_id: str = Field(primary_key=True)
    eval_run_id: str = Field(index=True)
    expectation: str | None = None
    checks: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False),
    )


def create_trace_tables(engine: Any) -> None:
    """Create trace tables for local/test databases.

    Production schema migration files are intentionally not introduced here because
    ``services/api/migrations/**`` is a protected contract path for this issue.
    """

    SQLModel.metadata.create_all(engine)


class TraceStore:
    def __init__(self, session: Session):
        self._session = session

    def add_tool_call(self, trace: ToolCallTrace) -> ToolCallTrace:
        record = ToolCallTraceRecord(
            id=trace.id,
            project_id=trace.project_id,
            origin=trace.origin.model_dump(mode="json"),
            tool_name=trace.tool_name,
            input=trace.input,
            output=trace.output,
            artifact_refs=[artifact.model_dump(mode="json") for artifact in trace.artifact_refs],
            status=trace.status,
            error=trace.error.model_dump(mode="json") if trace.error else None,
            started_at=trace.started_at,
            ended_at=trace.ended_at,
            latency_ms=trace.latency_ms,
            chat_session_id=trace.chat_session_id,
            chat_message_id=trace.chat_message_id,
            eval_run_id=trace.eval_run_id,
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return _tool_call_from_record(record)

    def get_tool_call(self, trace_id: str) -> ToolCallTrace | None:
        record = self._session.get(ToolCallTraceRecord, trace_id)
        if record is None:
            return None
        return _tool_call_from_record(record)

    def list_tool_calls(
        self,
        *,
        project_id: str | None = None,
        eval_run_id: str | None = None,
    ) -> list[ToolCallTrace]:
        statement = select(ToolCallTraceRecord).order_by(col(ToolCallTraceRecord.started_at))
        if project_id is not None:
            statement = statement.where(ToolCallTraceRecord.project_id == project_id)
        if eval_run_id is not None:
            statement = statement.where(ToolCallTraceRecord.eval_run_id == eval_run_id)
        return [_tool_call_from_record(record) for record in self._session.exec(statement).all()]

    def add_chat_session(self, chat_session: ChatSession) -> ChatSession:
        record = ChatSessionRecord(
            id=chat_session.id,
            project_id=chat_session.project_id,
            model=chat_session.model,
            created_at=chat_session.created_at,
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return _chat_session_from_record(record)

    def add_chat_message(self, chat_message: ChatMessage) -> ChatMessage:
        record = ChatMessageRecord(
            id=chat_message.id,
            session_id=chat_message.session_id,
            role=chat_message.role,
            content=chat_message.content,
            tool_call_ids=chat_message.tool_call_ids,
            model_meta=chat_message.model_meta,
            created_at=chat_message.created_at,
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return _chat_message_from_record(record)

    def list_chat_messages(self, session_id: str) -> list[ChatMessage]:
        statement = (
            select(ChatMessageRecord)
            .where(ChatMessageRecord.session_id == session_id)
            .order_by(col(ChatMessageRecord.created_at))
        )
        return [_chat_message_from_record(record) for record in self._session.exec(statement).all()]

    def add_eval_step(self, eval_run_id: str, step: EvalTraceStep) -> EvalTraceStep:
        validate_prefixed_ulid(eval_run_id, "eval_run_")
        record = EvalTraceStepRecord(
            tool_call_id=step.tool_call_id,
            eval_run_id=eval_run_id,
            expectation=step.expectation,
            checks=[check.model_dump(mode="json") for check in step.checks],
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return _eval_step_from_record(record)

    def list_eval_steps(self, eval_run_id: str) -> list[EvalTraceStep]:
        statement = (
            select(EvalTraceStepRecord)
            .where(EvalTraceStepRecord.eval_run_id == eval_run_id)
            .order_by(EvalTraceStepRecord.tool_call_id)
        )
        return [_eval_step_from_record(record) for record in self._session.exec(statement).all()]


def export_tool_calls_jsonl(traces: list[ToolCallTrace]) -> str:
    """Return the replay-facing ``traces/tool_calls.jsonl`` export shape."""

    lines = [
        json.dumps(trace.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        for trace in traces
    ]
    return "\n".join(lines) + ("\n" if lines else "")


def _validate_optional_prefixed_ulid(value: str | None, prefix: str) -> str | None:
    if value is None:
        return value
    return validate_prefixed_ulid(value, prefix)


def _stored_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _tool_call_from_record(record: ToolCallTraceRecord) -> ToolCallTrace:
    return ToolCallTrace(
        id=record.id,
        project_id=record.project_id,
        origin=TraceOrigin.model_validate(record.origin),
        tool_name=record.tool_name,
        input=record.input,
        output=record.output,
        artifact_refs=[ArtifactRef.model_validate(artifact) for artifact in record.artifact_refs],
        status=cast(TraceStatus, record.status),
        error=TraceError.model_validate(record.error) if record.error is not None else None,
        started_at=_stored_datetime(record.started_at),
        ended_at=_stored_datetime(record.ended_at),
        latency_ms=record.latency_ms,
        chat_session_id=record.chat_session_id,
        chat_message_id=record.chat_message_id,
        eval_run_id=record.eval_run_id,
    )


def _chat_session_from_record(record: ChatSessionRecord) -> ChatSession:
    return ChatSession(
        id=record.id,
        project_id=record.project_id,
        model=record.model,
        created_at=_stored_datetime(record.created_at),
    )


def _chat_message_from_record(record: ChatMessageRecord) -> ChatMessage:
    return ChatMessage(
        id=record.id,
        session_id=record.session_id,
        role=cast(ChatRole, record.role),
        content=record.content,
        tool_call_ids=record.tool_call_ids,
        model_meta=record.model_meta,
        created_at=_stored_datetime(record.created_at),
    )


def _eval_step_from_record(record: EvalTraceStepRecord) -> EvalTraceStep:
    return EvalTraceStep(
        tool_call_id=record.tool_call_id,
        expectation=record.expectation,
        checks=[EvalCheck.model_validate(check) for check in record.checks],
    )
