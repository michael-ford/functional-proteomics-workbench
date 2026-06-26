"use client";

import { FormEvent, useMemo, useState } from "react";
import { GitBranch, Loader2, MessageSquare, Send } from "lucide-react";

import { EmptyState, Panel, PanelTitle, StatusPill } from "./workspace-shell";

type ChatRole = "user" | "assistant" | "tool";

type ChatMessage = {
  id: string;
  session_id: string;
  role: ChatRole;
  content: string | null;
  tool_call_ids: string[];
  model_meta: Record<string, unknown> | null;
  created_at: string;
};

type ChatToolTrace = {
  id: string;
  project_id: string | null;
  origin: {
    surface: string;
    client: string | null;
    token_id: string | null;
  };
  tool_name: string;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  status: "ok" | "error";
  error: Record<string, unknown> | null;
  latency_ms: number;
  chat_session_id: string | null;
  chat_message_id: string | null;
};

type ChatRuntime = {
  mode: "openrouter_live" | "deterministic_mock" | "unavailable";
  provider: string;
  model: string;
  limitation: string | null;
  reason: string | null;
};

type ChatResponse = {
  session_id: string;
  project_id: string;
  model: string;
  runtime: ChatRuntime;
  messages: ChatMessage[];
  assistant_message: ChatMessage;
  tool_traces: ChatToolTrace[];
};

const PROJECT_ID = "proj_demo";

export function ChatPanel() {
  const [message, setMessage] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [traceLog, setTraceLog] = useState<ChatToolTrace[]>([]);
  const [runtime, setRuntime] = useState<ChatRuntime | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const conversation = useMemo(
    () => messages.filter((item) => item.role !== "tool"),
    [messages],
  );

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || isSending) {
      return;
    }

    setIsSending(true);
    setError(null);
    try {
      const response = await fetch("/api/fpw/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: PROJECT_ID,
          session_id: sessionId,
          message: trimmed,
        }),
      });
      if (!response.ok) {
        throw new Error(await readChatError(response));
      }
      const payload = (await response.json()) as ChatResponse;
      setSessionId(payload.session_id);
      setMessages(payload.messages);
      setTraceLog((current) => [...payload.tool_traces, ...current].slice(0, 8));
      setRuntime(payload.runtime);
      setMessage("");
    } catch (caught) {
      setError(formatChatFailure(caught));
    } finally {
      setIsSending(false);
    }
  }

  return (
    <Panel>
      <PanelTitle icon={MessageSquare} title="Web chat" meta={runtimeLabel(runtime)} />
      <div className="grid min-h-[31rem] gap-px bg-border lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="flex min-h-[24rem] flex-col bg-surface">
          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {conversation.length === 0 ? (
              <EmptyState>
                Ask about project status, the selected Perturb-PBMC dataset, or a trace-backed result.
              </EmptyState>
            ) : (
              conversation.map((item) => (
                <div
                  key={item.id}
                  className={`max-w-[44rem] rounded border px-3 py-2 text-sm leading-6 ${
                    item.role === "user"
                      ? "ml-auto border-accent/30 bg-wash text-ink"
                      : "border-border bg-surface text-ink"
                  }`}
                >
                  <div className="mb-1 flex items-center justify-between gap-3 text-xs text-muted">
                    <span className="font-semibold uppercase">{item.role}</span>
                    {item.tool_call_ids.length > 0 ? (
                      <span className="truncate">{item.tool_call_ids[0]}</span>
                    ) : null}
                  </div>
                  <p>{item.content}</p>
                </div>
              ))
            )}
          </div>

          <form
            onSubmit={sendMessage}
            className="border-t border-border bg-wash px-3 py-3"
            aria-label="Web chat message"
          >
            <div className="flex items-center gap-2">
              <label htmlFor="web-chat-message" className="sr-only">
                Message
              </label>
              <input
                id="web-chat-message"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                className="min-h-10 min-w-0 flex-1 rounded border border-border bg-surface px-3 text-sm outline-none transition focus:border-accent"
                placeholder="Project status"
                disabled={isSending}
              />
              <button
                type="submit"
                className="flex size-10 shrink-0 items-center justify-center rounded border border-border bg-ink text-white transition hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
                aria-label="Send message"
                title="Send message"
                disabled={isSending || !message.trim()}
              >
                {isSending ? (
                  <Loader2 size={17} className="animate-spin" aria-hidden="true" />
                ) : (
                  <Send size={17} aria-hidden="true" />
                )}
              </button>
            </div>
            {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
            {runtime?.limitation ? (
              <p className="mt-2 text-xs text-muted">{runtime.limitation}</p>
            ) : null}
          </form>
        </div>

        <div className="bg-surface">
          <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <GitBranch size={16} aria-hidden="true" />
              Tool traces
            </div>
            <StatusPill>{traceLog.length}</StatusPill>
          </div>
          <div className="max-h-[30rem] divide-y divide-border overflow-y-auto">
            {traceLog.length === 0 ? (
              <EmptyState>Tool traces will appear here after the assistant runs a workspace tool.</EmptyState>
            ) : (
              traceLog.map((trace) => (
                <article key={trace.id} className="px-4 py-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="truncate font-semibold">{trace.tool_name}</h3>
                    <StatusPill>{trace.status}</StatusPill>
                  </div>
                  <dl className="mt-3 grid gap-2 text-xs text-muted">
                    <div className="flex justify-between gap-3">
                      <dt>Trace</dt>
                      <dd className="truncate font-mono">{trace.id}</dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt>Surface</dt>
                      <dd>{trace.origin.surface}</dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt>Latency</dt>
                      <dd>{trace.latency_ms} ms</dd>
                    </div>
                  </dl>
                  <p className="mt-3 line-clamp-3 text-xs leading-5 text-muted">
                    {traceSummary(trace)}
                  </p>
                </article>
              ))
            )}
          </div>
        </div>
      </div>
    </Panel>
  );
}

function runtimeLabel(runtime: ChatRuntime | null): string {
  if (!runtime) {
    return "model ready";
  }
  if (runtime.mode === "deterministic_mock") {
    return "deterministic mock";
  }
  if (runtime.mode === "openrouter_live") {
    return `live ${runtime.model}`;
  }
  return "model unavailable";
}

function formatChatFailure(caught: unknown): string {
  const fallback =
    "Chat is temporarily unavailable. Check your connection and try again.";
  if (!(caught instanceof Error)) {
    return fallback;
  }
  const message = caught.message.trim();
  if (!message || message === "Failed to fetch" || message === "NetworkError when attempting to fetch resource.") {
    return fallback;
  }
  return `${message} Try again in a moment.`;
}

async function readChatError(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as unknown;
    if (isRecord(payload) && isRecord(payload.detail)) {
      const message = payload.detail.message;
      const code = payload.detail.code;
      if (typeof message === "string" && typeof code === "string") {
        return `${message} (${code})`;
      }
      if (typeof message === "string") {
        return message;
      }
    }
  } catch {
    // Fall through to a generic HTTP error.
  }
  return `Chat request failed with HTTP ${response.status}`;
}

function traceSummary(trace: ChatToolTrace): string {
  if (trace.error) {
    const code = String(trace.error.code ?? "tool_error");
    const message = String(trace.error.message ?? "Tool call failed.");
    return `${code}: ${message}`;
  }
  const project = trace.output?.project;
  if (isRecord(project)) {
    const title = String(project.title ?? "Project");
    const status = String(project.status ?? "unknown");
    return `${title}: ${status}`;
  }
  return JSON.stringify(trace.output ?? trace.input);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
