from fastapi.testclient import TestClient

from fpw_api import create_app
from fpw_api.tools import InMemoryTraceSink, create_default_tool_registry


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
    assert body["assistant_message"]["role"] == "assistant"
    assert "Perturb-PBMC IL-10/LPS demo is validated" in body["assistant_message"]["content"]
    assert body["tool_traces"][0]["tool_name"] == "get_project_status"
    assert body["tool_traces"][0]["status"] == "ok"
    assert body["tool_traces"][0]["origin"]["surface"] == "web_chat"
    assert body["tool_traces"][0]["chat_session_id"] == body["session_id"]
    assert len(sink.traces) == 1
    assert sink.traces[0].id == body["tool_traces"][0]["id"]
    assert sink.traces[0].project_id == "proj_demo"
    assert sink.traces[0].origin.surface == "web_chat"


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
