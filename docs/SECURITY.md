# Security

> **Protected file.** SPEC-007. This is a **demonstration system**, not production software.
> See "Non-production assumptions" below.

## Demo auth
- No real account system (HANDOFF §14). The UI may look account-like ("Continue as demo
  user"); authentication is not a feature.
- The web app operates on the seeded demo project (`proj_demo`) and demo-created projects.

## MCP token
- External MCP clients authenticate with a demo bearer token (`MCP_DEMO_TOKEN`).
- Tokens are referenced in traces by `token_id` only — **the token value is never logged or
  rendered** (`docs/TRACE_MODEL.md`).
- Exact token model (static vs per-session vs project-scoped, read-mostly vs read/write)
  remains open (HANDOFF §14.3) and is tracked in `docs/OPEN_QUESTIONS.md`.

## Tool guardrails (enforced in code, not by the model — HANDOFF §32)
- **Tool allowlist:** only registry tools are callable; no arbitrary tool surface.
- **No arbitrary SQL** exposed to the agent; **no arbitrary filesystem access** — all
  artifact bytes go through the storage adapter via `ArtifactRef`.
- **Project-scoped access:** `get_trace` / project tools return only the requested project's
  data.
- **Bounded methods/plots:** `run_comparison` accepts only supported `method_id`s;
  `create_plot` only supported `plot_type`s; `search_corpus` only the indexed corpus.
- **No fabrication:** no fake citations, data provenance, or tool traces. A `source-derived`
  report claim must cite real evidence (`docs/DATA_CONTRACTS.md` invariant).
- Reference (public) data is read-only; uploaded demo data is scoped to its demo project.

## External model calls
- The agent loop calls OpenRouter (→ Kimi). The model adapter is **mockable in CI**; core
  eval pass/fail does not depend on paid model calls (`docs/EVALS.md`).
- Model provider keys (`OPENROUTER_API_KEY`, optional `OPENAI_/ANTHROPIC_API_KEY`) are
  supplied via environment/Railway secrets — never committed.

## Secrets
- No secrets in the repo. `.env.example` documents variable names only.
- The CI review agents (Claude + Codex) run as **local CLI sessions** inheriting local
  subscription auth on the self-hosted runner — so **no model API keys live in repo secrets**
  for review (`docs/DEVELOPMENT_WORKFLOW.md`).

## Uploaded-data cautions
- Do not upload sensitive data; demo data may be reset (`make demo-reset`).
- No privacy/compliance guarantees are made or implied.

## Non-production assumptions
Demonstration system · no real auth · demo data may be reset · data retention is not
production-grade · the app may be shut down after the demo's utility is complete.
