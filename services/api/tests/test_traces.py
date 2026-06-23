from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from shared_schemas import ArtifactRef
from sqlmodel import Session, create_engine

from fpw_api.traces import (
    ChatMessage,
    ChatSession,
    EvalCheck,
    EvalTraceStep,
    ToolCallTrace,
    TraceError,
    TraceOrigin,
    TraceStore,
    create_trace_tables,
    export_tool_calls_jsonl,
)

ULID = "01K1M9M8J6T2P3R4S5T6V7W8X9"


@pytest.fixture
def utc_now() -> datetime:
    return datetime(2026, 6, 23, 19, 30, tzinfo=UTC)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    create_trace_tables(engine)
    with Session(engine) as db_session:
        yield db_session


def test_tool_call_trace_validates_contract_shape(utc_now: datetime) -> None:
    trace = _tool_call_trace(utc_now)

    assert trace.id == f"tc_{ULID}"
    assert trace.origin.surface == "eval"
    assert trace.artifact_refs[0].uri == "project://proj_demo/traces/output.json"


def test_trace_rejects_inconsistent_error_status(utc_now: datetime) -> None:
    with pytest.raises(ValidationError, match="error tool calls must include"):
        _tool_call_trace(utc_now, status="error")

    with pytest.raises(ValidationError, match="ok tool calls must not include"):
        _tool_call_trace(utc_now, error=TraceError(code="bad_input", message="Invalid input."))


def test_trace_requires_surface_linkage(utc_now: datetime) -> None:
    with pytest.raises(ValidationError, match="web_chat tool calls must include chat_session_id"):
        _tool_call_trace(
            utc_now,
            origin=TraceOrigin(surface="web_chat", client="web"),
            chat_session_id=None,
            eval_run_id=None,
        )

    with pytest.raises(ValidationError, match="eval tool calls must include eval_run_id"):
        _tool_call_trace(utc_now, eval_run_id=None)


def test_trace_store_persists_and_reads_tool_calls(session: Session, utc_now: datetime) -> None:
    store = TraceStore(session)
    trace = _tool_call_trace(utc_now)

    created = store.add_tool_call(trace)
    fetched = store.get_tool_call(trace.id)
    project_traces = store.list_tool_calls(project_id="proj_demo")
    eval_traces = store.list_tool_calls(eval_run_id=f"eval_run_{ULID}")

    assert created == trace
    assert fetched == trace
    assert project_traces == [trace]
    assert eval_traces == [trace]


def test_trace_store_persists_chat_and_eval_replay_state(
    session: Session,
    utc_now: datetime,
) -> None:
    store = TraceStore(session)
    trace = _tool_call_trace(utc_now)
    chat_session = ChatSession(
        id=f"chat_{ULID}",
        project_id="proj_demo",
        model="openrouter/moonshotai/kimi-k2",
        created_at=utc_now,
    )
    chat_message = ChatMessage(
        id=f"msg_{ULID}",
        session_id=chat_session.id,
        role="assistant",
        content="Created a trace-backed analysis step.",
        tool_call_ids=[trace.id],
        model_meta={"finish_reason": "stop", "latency_ms": 12},
        created_at=utc_now + timedelta(milliseconds=12),
    )
    eval_step = EvalTraceStep(
        tool_call_id=trace.id,
        expectation="rank proteins from fixture data",
        checks=[
            EvalCheck(
                kind="trace_completeness",
                passed=True,
                detail="tool call includes input, output, timing, and eval linkage",
            )
        ],
    )

    store.add_tool_call(trace)
    assert store.add_chat_session(chat_session) == chat_session
    assert store.add_chat_message(chat_message) == chat_message
    assert store.add_eval_step(f"eval_run_{ULID}", eval_step) == eval_step

    assert store.list_chat_messages(chat_session.id) == [chat_message]
    assert store.list_eval_steps(f"eval_run_{ULID}") == [eval_step]


def test_export_tool_calls_jsonl_matches_replay_shape(utc_now: datetime) -> None:
    trace = _tool_call_trace(utc_now)

    exported = export_tool_calls_jsonl([trace])
    line = json.loads(exported)

    assert exported.endswith("\n")
    assert line["id"] == trace.id
    assert line["origin"] == {"client": "eval-runner", "surface": "eval", "token_id": None}
    assert line["artifact_refs"] == [
        {
            "bytes": 42,
            "media_type": "application/json",
            "sha256": None,
            "uri": "project://proj_demo/traces/output.json",
        }
    ]
    assert line["started_at"] == "2026-06-23T19:30:00Z"
    assert line["ended_at"] == "2026-06-23T19:30:00.125000Z"


def _tool_call_trace(
    started_at: datetime,
    *,
    origin: TraceOrigin | None = None,
    status: str = "ok",
    error: TraceError | None = None,
    chat_session_id: str | None = f"chat_{ULID}",
    eval_run_id: str | None = f"eval_run_{ULID}",
) -> ToolCallTrace:
    return ToolCallTrace(
        id=f"tc_{ULID}",
        project_id="proj_demo",
        origin=origin or TraceOrigin(surface="eval", client="eval-runner"),
        tool_name="rank_proteins",
        input={"result_id": f"res_{ULID}"},
        output={"top_protein": "IL6"},
        artifact_refs=[
            ArtifactRef(
                uri="project://proj_demo/traces/output.json",
                media_type="application/json",
                bytes=42,
            )
        ],
        status=status,  # type: ignore[arg-type]
        error=error,
        started_at=started_at,
        ended_at=started_at + timedelta(milliseconds=125),
        latency_ms=125,
        chat_session_id=chat_session_id if origin and origin.surface == "web_chat" else None,
        eval_run_id=eval_run_id,
    )
