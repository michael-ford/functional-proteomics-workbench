# Trace & Eval Replay Model

> **Protected / contract file (blocking).** Changes require a PR labeled `contract-change`.
> SPEC-004. This schema is consumed by the MCP server, web chat, tool registry, eval runner,
> eval page, dashboard, and report generation — so it is frozen early.

## Storage

Traces are persisted as **Postgres tables** (queryable for the dashboard + eval replay) and
**exported to JSONL** into the file-like project tree (`traces/tool_calls.jsonl`,
`traces/chat_trace.jsonl`, `traces/eval_trace.jsonl`) for inspectability. Postgres is the
source of truth; JSONL is a derived export.

## The spine: ToolCallTrace

Every tool invocation — whether it originated from the web chat, an external MCP client, or
the eval runner — produces exactly one `ToolCallTrace`. Tools cannot write project state
outside a traced call (enforced in the registry, not by the model).

```python
class ToolCallTrace(BaseModel):
    id: str                       # tc_*
    project_id: str | None        # None only for non-project tools
    origin: "TraceOrigin"         # where the call came from
    tool_name: str
    input: dict                   # validated tool input (secrets redacted)
    output: dict | None           # validated tool output
    artifact_refs: list[ArtifactRef] = []
    status: Literal["ok", "error"]
    error: "TraceError | None" = None
    started_at: datetime
    ended_at: datetime
    latency_ms: int
    # linkage
    chat_session_id: str | None = None   # set when origin == "web_chat"
    chat_message_id: str | None = None
    eval_run_id: str | None = None       # set when origin == "eval"

class TraceOrigin(BaseModel):
    surface: Literal["web_chat", "mcp", "eval", "api"]
    client: str | None = None     # e.g. "claude-desktop", "codex", "web", "eval-runner"
    token_id: str | None = None   # demo/MCP token id if present (never the token itself)

class TraceError(BaseModel):
    code: str
    message: str
    retryable: bool = False
```

## Two trace modes

### Web-chat full trace
Available when the interaction runs through the built-in web chat (we control the whole
loop, so we can record more than an external client exposes).

```python
class ChatSession(BaseModel):
    id: str                       # chat_*
    project_id: str
    model: str                    # e.g. "openrouter/moonshotai/kimi-k2"
    created_at: datetime

class ChatMessage(BaseModel):
    id: str                       # msg_*
    session_id: str
    role: Literal["user", "assistant", "tool"]
    content: str | None = None
    tool_call_ids: list[str] = [] # -> ToolCallTrace.id
    model_meta: dict | None = None   # tokens, finish_reason, latency
    created_at: datetime
```
A `ChatTrace` is the ordered view of a session: its messages + the `ToolCallTrace`s they
reference + retrieved chunks + analysis/report artifact refs + final response + per-step
timing + errors/retries. It is assembled by query, not stored as a separate blob.

### MCP server-side trace
Available when an external MCP client drives the tools. We see the tool calls but **not** the
client's full conversation. Captured fields = the `ToolCallTrace` itself (with
`origin.surface == "mcp"`, `origin.client`, optional `token_id`), the affected project,
artifact refs, status, error, timing. No fabricated conversational context is ever invented
to fill the gap.

## Eval trace & replay

An eval case runs the same tools through the registry with `origin.surface == "eval"`. The
resulting `ToolCallTrace`s (linked by `eval_run_id`) ARE the replay: the eval page renders
the exact tool sequence, inputs, outputs, and checks.

```python
class EvalTraceStep(BaseModel):
    tool_call_id: str             # -> ToolCallTrace
    expectation: str | None = None
    checks: list["EvalCheck"] = []

class EvalCheck(BaseModel):
    kind: Literal["tool_choice", "schema_validity", "numeric", "citation_support",
                  "entity_grounding", "unsupported_claim", "report_structure", "trace_completeness"]
    passed: bool
    detail: str | None = None
```
(The `EvalCase` / `EvalResult` / `EvalRun` envelopes live in `docs/EVALS.md`.)

## Replay behavior
- Replay is **trace-driven**, not model-re-run by default: the eval page shows the recorded
  `ToolCallTrace`s and the check verdicts computed against them.
- Deterministic tools (analysis on fixture data) reproduce identically on re-run.
- Model-dependent steps (the agent's choices) are replayed from the recorded trace unless a
  `--live` eval is explicitly requested.

## UI requirements
- **Dashboard tool-trace panel:** ordered tool calls for the project, each expandable to
  input/output/artifacts/latency, error rows highlighted.
- **Eval page:** per-case step list with check pass/fail badges and the underlying trace.
- Secrets/tokens never rendered (`token_id` only, never the token value).

## Retention (non-production)
Demo-grade. Traces persist for the life of the demo project and may be reset
(`make demo-reset`). No production retention guarantees; documented in `docs/SECURITY.md`.
