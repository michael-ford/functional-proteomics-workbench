import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatPanel } from "./chat-panel";

describe("ChatPanel", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts chat turns to the API proxy and renders the returned tool trace", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        session_id: "chat_01KCYAG0000000000000000000",
        project_id: "proj_demo",
        model: "mock/openrouter-kimi-structural",
        messages: [
          {
            id: "msg_01KCYAG0000000000000000001",
            session_id: "chat_01KCYAG0000000000000000000",
            role: "user",
            content: "project status",
            tool_call_ids: [],
            model_meta: null,
            created_at: "2026-06-24T00:00:00Z",
          },
          {
            id: "msg_01KCYAG0000000000000000002",
            session_id: "chat_01KCYAG0000000000000000000",
            role: "tool",
            content: "get_project_status ok",
            tool_call_ids: ["tc_01KCYAG0000000000000000003"],
            model_meta: null,
            created_at: "2026-06-24T00:00:00Z",
          },
          {
            id: "msg_01KCYAG0000000000000000004",
            session_id: "chat_01KCYAG0000000000000000000",
            role: "assistant",
            content: "v0.1 Perturb-PBMC IL-10/LPS demo is validated.",
            tool_call_ids: ["tc_01KCYAG0000000000000000003"],
            model_meta: { finish_reason: "tool_call" },
            created_at: "2026-06-24T00:00:00Z",
          },
        ],
        assistant_message: {
          id: "msg_01KCYAG0000000000000000004",
          session_id: "chat_01KCYAG0000000000000000000",
          role: "assistant",
          content: "v0.1 Perturb-PBMC IL-10/LPS demo is validated.",
          tool_call_ids: ["tc_01KCYAG0000000000000000003"],
          model_meta: { finish_reason: "tool_call" },
          created_at: "2026-06-24T00:00:00Z",
        },
        tool_traces: [
          {
            id: "tc_01KCYAG0000000000000000003",
            project_id: "proj_demo",
            origin: { surface: "web_chat", client: "web", token_id: null },
            tool_name: "get_project_status",
            input: { project_id: "proj_demo" },
            output: {
              project: {
                title: "v0.1 Perturb-PBMC IL-10/LPS demo",
                status: "validated",
              },
            },
            status: "ok",
            error: null,
            latency_ms: 3,
            chat_session_id: "chat_01KCYAG0000000000000000000",
            chat_message_id: "msg_01KCYAG0000000000000000002",
          },
        ],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ChatPanel />);

    fireEvent.change(screen.getByLabelText("Message"), {
      target: { value: "project status" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    await screen.findByText("v0.1 Perturb-PBMC IL-10/LPS demo is validated.");
    expect(screen.getByText("get_project_status")).toBeVisible();
    expect(screen.getByText("web_chat")).toBeVisible();
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/fpw/chat",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            project_id: "proj_demo",
            session_id: null,
            message: "project status",
          }),
        }),
      );
    });
  });
});
