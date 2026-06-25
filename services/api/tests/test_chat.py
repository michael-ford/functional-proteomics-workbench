import asyncio

import pytest
from fastapi.testclient import TestClient

from fpw_api import create_app
from fpw_api.chat import (
    MockChatModelAdapter,
    OpenRouterAdapterError,
    OpenRouterChatModelAdapter,
    create_default_chat_model_adapter,
)
from fpw_api.tools import InMemoryTraceSink, create_default_tool_registry


@pytest.fixture(autouse=True)
def _use_mock_chat_adapter_by_default(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.delenv("FPW_USE_MOCK_MODEL", raising=False)


def test_default_chat_adapter_uses_mock_without_openrouter_key(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "openrouter")

    adapter = create_default_chat_model_adapter()

    assert isinstance(adapter, MockChatModelAdapter)
    assert adapter.model_name == "mock/openrouter-kimi-structural"
    assert adapter.runtime_mode == "deterministic_mock"
    assert adapter.runtime_reason == "missing_openrouter_key"


def test_default_chat_adapter_uses_openrouter_when_key_is_configured(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "moonshotai/kimi-k2-test")

    adapter = create_default_chat_model_adapter()

    assert isinstance(adapter, OpenRouterChatModelAdapter)
    assert adapter.model_name == "moonshotai/kimi-k2-test"
    assert adapter.runtime_mode == "openrouter_live"


def test_default_chat_adapter_can_force_mock_for_ci(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("FPW_USE_MOCK_MODEL", "true")

    adapter = create_default_chat_model_adapter()

    assert isinstance(adapter, MockChatModelAdapter)
    assert adapter.runtime_reason == "FPW_USE_MOCK_MODEL"


def test_default_chat_adapter_marks_unsupported_provider_unavailable(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "unsupported")

    adapter = create_default_chat_model_adapter()

    assert adapter.model_name == "unavailable"
    assert adapter.runtime_mode == "unavailable"
    assert adapter.runtime_reason == "unsupported_model_provider"


def test_openrouter_adapter_rejects_tools_outside_safe_chat_allowlist_without_fallback() -> None:
    class UnsafeToolAdapter(OpenRouterChatModelAdapter):
        def _request_decision(self, *_args, **_kwargs):
            return {
                "tool_name": "create_project",
                "arguments": {"title": "Injected"},
                "rationale": "Unsafe mutating tool.",
            }

    adapter = UnsafeToolAdapter(api_key="test-key")
    with pytest.raises(OpenRouterAdapterError, match="unsafe_tool_choice"):
        asyncio.run(
            adapter.choose_tool(
                message="project status",
                project_id="proj_demo",
                registry=create_default_tool_registry(),
            )
        )


def test_openrouter_adapter_rejects_invalid_decision_schema_without_fallback() -> None:
    class InvalidDecisionAdapter(OpenRouterChatModelAdapter):
        def _request_decision(self, *_args, **_kwargs):
            return {
                "tool_name": "get_project_status",
                "arguments": {"project_id": "proj_demo"},
            }

    adapter = InvalidDecisionAdapter(api_key="test-key")
    with pytest.raises(OpenRouterAdapterError, match="provider_decision_invalid"):
        asyncio.run(
            adapter.choose_tool(
                message="project status",
                project_id="proj_demo",
                registry=create_default_tool_registry(),
            )
        )


@pytest.mark.parametrize(
    "provider_code",
    [
        "provider_http_500",
        "provider_unavailable",
        "provider_response_not_json",
        "provider_response_invalid",
    ],
)
def test_chat_surfaces_openrouter_provider_failures_without_mock_response(
    provider_code: str,
) -> None:
    class BrokenOpenRouterAdapter(OpenRouterChatModelAdapter):
        def _request_decision(self, *_args, **_kwargs):
            raise OpenRouterAdapterError(provider_code)

    sink = InMemoryTraceSink()
    app = create_app(
        trace_sink=sink,
        chat_model_adapter=BrokenOpenRouterAdapter(api_key="test-key"),
    )

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"project_id": "proj_demo", "message": "What is the project status?"},
        )

    assert response.status_code == 502
    body = response.json()
    assert body["detail"]["code"] == provider_code
    assert body["detail"]["runtime"]["mode"] == "openrouter_live"
    assert body["detail"]["runtime"]["provider"] == "openrouter"
    assert sink.traces == []


def test_chat_surfaces_unsafe_openrouter_tool_choice_without_mock_response() -> None:
    class UnsafeToolAdapter(OpenRouterChatModelAdapter):
        def _request_decision(self, *_args, **_kwargs):
            return {
                "tool_name": "create_project",
                "arguments": {"title": "Injected"},
                "rationale": "Unsafe mutating tool.",
            }

    sink = InMemoryTraceSink()
    app = create_app(trace_sink=sink, chat_model_adapter=UnsafeToolAdapter(api_key="test-key"))

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"project_id": "proj_demo", "message": "What is the project status?"},
        )

    assert response.status_code == 502
    body = response.json()
    assert body["detail"]["code"] == "unsafe_tool_choice"
    assert body["detail"]["runtime"]["mode"] == "openrouter_live"
    assert sink.traces == []


def test_openrouter_adapter_accepts_safe_tool_choice() -> None:
    class SafeToolAdapter(OpenRouterChatModelAdapter):
        def _request_decision(self, *_args, **_kwargs):
            return {
                "tool_name": "get_project_status",
                "arguments": {"project_id": "proj_demo"},
                "rationale": "Read project state.",
            }

    adapter = SafeToolAdapter(api_key="test-key")
    decision = asyncio.run(
        adapter.choose_tool(
            message="project status",
            project_id="proj_demo",
            registry=create_default_tool_registry(),
        )
    )

    assert decision is not None
    assert decision.tool_name == "get_project_status"
    assert decision.arguments == {"project_id": "proj_demo"}


def test_chat_invokes_safe_tool_through_shared_registry_and_records_trace() -> None:
    sink = InMemoryTraceSink()
    app = create_app(trace_sink=sink)

    with TestClient(app) as client:
        response = client.post(
            "/chat",
            json={"project_id": "proj_demo", "message": "What is the project status?"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == "proj_demo"
    assert body["model"] == "mock/openrouter-kimi-structural"
    assert body["runtime"] == {
        "mode": "deterministic_mock",
        "provider": "mock",
        "model": "mock/openrouter-kimi-structural",
        "limitation": "v0.1 chat is limited to read-only project status tools.",
        "reason": "missing_openrouter_key",
    }
    assert body["assistant_message"]["role"] == "assistant"
    assert body["assistant_message"]["model_meta"]["runtime"]["mode"] == "deterministic_mock"
    assert "Perturb-PBMC IL-10/LPS demo is validated" in body["assistant_message"]["content"]
    assert body["tool_traces"][0]["tool_name"] == "get_project_status"
    assert body["tool_traces"][0]["status"] == "ok"
    assert body["tool_traces"][0]["origin"]["surface"] == "web_chat"
    assert body["tool_traces"][0]["chat_session_id"] == body["session_id"]
    assert len(sink.traces) == 1
    assert sink.traces[0].id == body["tool_traces"][0]["id"]
    assert sink.traces[0].project_id == "proj_demo"
    assert sink.traces[0].origin.surface == "web_chat"
    assert app.state.project_state == {}


def test_chat_sessions_persist_messages_across_turns() -> None:
    app = create_app()

    with TestClient(app) as client:
        first = client.post(
            "/chat",
            json={"project_id": "proj_demo", "message": "project status"},
        ).json()
        second = client.post(
            "/chat",
            json={
                "project_id": "proj_demo",
                "session_id": first["session_id"],
                "message": "dataset state",
            },
        ).json()

    assert second["session_id"] == first["session_id"]
    assert [message["role"] for message in second["messages"]] == [
        "user",
        "tool",
        "assistant",
        "user",
        "tool",
        "assistant",
    ]


def test_web_chat_and_mcp_read_the_same_project_state(monkeypatch) -> None:
    monkeypatch.setenv("MCP_DEMO_TOKEN", "test-token")
    registry = create_default_tool_registry()
    project_state = {
        "projects": {
            "proj_demo": {
                "project": {
                    "id": "proj_demo",
                    "schema_version": "0.1.0",
                    "title": "Injected shared demo state",
                    "status": "analyzed",
                    "context_md": None,
                    "created_at": "2026-06-24T00:00:00Z",
                    "updated_at": "2026-06-24T00:00:00Z",
                },
                "datasets": [{"id": "ds_test"}],
            }
        }
    }
    app = create_app(tool_registry=registry, project_state=project_state)

    with TestClient(app) as client:
        chat_response = client.post(
            "/chat",
            json={"project_id": "proj_demo", "message": "project status"},
        )
        mcp_response = client.post(
            "/mcp",
            headers={"Authorization": "Bearer test-token"},
            json={
                "jsonrpc": "2.0",
                "id": "call-1",
                "method": "tools/call",
                "params": {
                    "name": "get_project_status",
                    "arguments": {"project_id": "proj_demo"},
                },
            },
        )

    assert chat_response.status_code == 200
    assert mcp_response.status_code == 200
    chat_trace = chat_response.json()["tool_traces"][0]
    mcp_content = mcp_response.json()["result"]["structuredContent"]
    assert chat_trace["output"]["project"]["title"] == "Injected shared demo state"
    assert mcp_content["project"]["title"] == "Injected shared demo state"
