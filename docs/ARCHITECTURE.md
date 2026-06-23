# Architecture

> SPEC-003. The shared tool registry + MCP/web parity is the architectural crux.

## System overview

```
                         ┌───────────────────────────────────────────┐
   Browser (Next.js) ───▶│  FastAPI process (single deployable)        │
     - dashboard         │                                             │
     - upload            │   ┌─────────────┐   web chat loop           │
     - web chat          │   │ ToolRegistry│◀──(OpenRouter→Kimi adapter)│
     - eval page         │   └─────┬───────┘                           │
                         │         │ same object                       │
   External MCP    ─────▶│   MCP server (mounted) ─┘                   │
   (Claude Desktop,      │         │                                   │
    Codex, ...)          │   ┌─────▼──────┐   ┌───────────────┐        │
                         │   │ services   │   │ packages:     │        │
                         │   │ /api logic │   │ analysis,     │        │
                         │   └─────┬──────┘   │ corpus,       │        │
                         │         │          │ storage,      │        │
                         │         │          │ shared-schemas│        │
                         │         │          └───────────────┘        │
                         └─────────┼───────────────────────────────────┘
                                   │
                 ┌─────────────────┴───────────────────┐
                 ▼                                      ▼
        Postgres + pgvector                   Storage adapter
        (state, traces, embeddings)           local FS (dev) / Railway volume (deploy)
                                              → file-like project tree (project:// URIs)
```

## Services / packages
- **`apps/web`** — Next.js + Tailwind + shadcn/ui + Plotly. Human surface. Calls the API;
  TS types are generated from the Pydantic shared-schemas.
- **`services/api`** — FastAPI. Hosts the `ToolRegistry`, REST endpoints, and the **MCP
  server mounted in-process** (decision R10) so web and MCP share one registry object — parity
  by construction, not by discipline.
- **`packages/shared-schemas`** — Pydantic/SQLModel contracts (`docs/DATA_CONTRACTS.md`),
  source of truth; generates TS types.
- **`packages/analysis`** — deterministic, unit-tested analysis methods (pandas/scipy/
  statsmodels) behind the supported-method menu.
- **`packages/corpus`** — entity-aware chunking + retrieval (pgvector + full-text/entity).
- **`packages/storage`** — the storage adapter resolving `project://` URIs.

## Shared tool registry (the crux)
One `ToolRegistry` (`docs/MCP_TOOLS.md`) is imported by API, MCP server, web chat, and eval
runner. Every invocation is traced (`docs/TRACE_MODEL.md`). The web chat's agent loop and an
external MCP client call the *same* handlers; the only difference is `TraceOrigin.surface`.

## Data flow — the hero handoff (HANDOFF §3)
```
agent: create_project ─▶ ToolCallTrace + Project(created) ─▶ returns upload_url + dashboard_url
user:  opens upload_url ─▶ selects direct Perturb-PBMC subset ─▶ Dataset(selected_public)
agent: validate_dataset ─▶ inspect_dataset_schema ─▶ define_comparison ─▶ AnalysisPlan
agent: run_comparison ─▶ AnalysisResult ─▶ rank_proteins ─▶ create_plot ─▶ PlotArtifact
agent: search_corpus ─▶ attach_evidence ─▶ export_report ─▶ ReportArtifact (claim-typed)
dashboard renders: status · validation · ranked table · plot · donor consistency · evidence · report · trace
```

## Storage model
- **Postgres + pgvector**: structured state (entities in `docs/DATA_CONTRACTS.md`), traces
  (`docs/TRACE_MODEL.md`), corpus chunk embeddings.
- **Storage adapter**: file artifacts via `ArtifactRef` `project://` URIs → local FS (dev) /
  Railway volume (deploy). The conceptual project tree (HANDOFF §12.5) is the adapter's view.

## Web-chat flow
Browser ↔ API chat endpoint ↔ agent loop (OpenRouter → Kimi via a thin, swappable adapter;
mockable in CI) ↔ `ToolRegistry`. Full trace recorded (`ChatSession`/`ChatMessage` +
`ToolCallTrace`s).

## MCP flow
External client connects to the mounted MCP server with `MCP_DEMO_TOKEN`, calls the same
tools. Server-side trace only (no client conversation).

## Eval flow
`run_eval_suite` drives tools through the registry with `origin.surface == "eval"`; recorded
traces ARE the replay shown on the eval page (`docs/EVALS.md`).

## Deployment
Railway. Single FastAPI deployable (API + mounted MCP), Postgres add-on with pgvector, a
volume for artifacts, the Next.js app. CI gates deploy (`docs/DEVELOPMENT_WORKFLOW.md`).
