# Open Questions

> **Rule (from HANDOFF §23.11):** Do not silently resolve open questions in implementation
> PRs. If implementation requires resolving one, label the issue `needs-decision`.

This file tracks unresolved decisions and records resolutions with rationale.

---

## Resolved in session — 2026-06-23

| # | Decision | Resolution | Rationale |
|---|----------|------------|-----------|
| R1 | Repo home & visibility | `michael-ford`, **public** | Personal job-application demo; transparency |
| R2 | Merge policy | **All PRs auto-merge on green**, no human review | Demonstrate a strong automated gate; reverses HANDOFF §26 |
| R3 | Review trigger | **Automatic** on PR open + synchronize + ready_for_review | Reliable for an auto-merge pipeline; no PR slips ungated |
| R4 | Review agents | **Claude + Codex**, both as local **CLI sessions in tmux** on a self-hosted Mac runner | Inherits local subscription auth → no API-key secrets; unified spawn script |
| R5 | Runner | Self-hosted macOS, **fresh registration** for this repo | bestguy runners are bound to another repo; cannot reuse |
| R6 | Spec sprint method | **In-session interview** for critical specs; hand off data/stats/corpus specs to runners | Faster than round-tripping 8 issues |
| R7 | Package managers | **uv** (Python) + **pnpm** (JS) | uv locked by global rule; pnpm = standard JS monorepo manager |
| R8 | ORM / model layer | **SQLModel** | One class = DB table + API schema; fits Pydantic-first contracts |
| R9 | Schema source of truth | **Pydantic-first → generate TS** | Single source of truth in `packages/shared-schemas` |
| R10 | MCP server layout | **Mounted in the FastAPI process** | Web/MCP parity by construction; one Railway deployable |
| R11 | Agent / web-chat LLM | **OpenRouter → Kimi** (thin swappable adapter, mock in CI) | Easiest to implement; OpenAI-compatible API. Needs `OPENROUTER_API_KEY` |
| R12 | Artifact storage | **Postgres state + local FS (dev) / Railway volume (deploy)** behind storage adapter | Simplest path to a working demo |
| R13 | Trace storage | **Postgres tables (source of truth) + JSONL export** | Queryable dashboard/replay + file-like inspectability |
| R14 | v0.1 contract scope | **Trimmed core (~12 entities)**; chat→TRACE_MODEL, eval→EVALS, rest deferred | Keep contracts stable but small |
| R15 | Primary demo persona | **Nomic internal scientist** | Best fits MCP/web shared state, traceability, evals, and Nomic-specific internal workflow |
| R16 | Demo shape | **Hybrid**: biological analysis as the story, traces/evals as proof | Keeps domain relevance while foregrounding the agent-native engineering harness |
| R17 | v0.1 data flow | **Select a curated public Perturb-PBMC subset inside the app**; do not prioritize generic upload | Reduces scope and matches the public-data demo constraint |
| R18 | Biological claim level | **Conservative**: donor-consistent protein changes plus source-grounded evidence | Avoids mechanism claims and overinterpretation |
| R19 | Analysis direction | Include p-values if STAT-001 validates a defensible test; pair with effect size and donor consistency | p-values matter, but assumptions and multiple-testing handling must be explicit |
| R20 | Corpus direction | Deterministic indexed corpus: Nomic/Perturb-PBMC plus small curated public biology sources | Avoids live-search nondeterminism while supporting evidence-backed reports |
| R21 | Eval direction | Evals primarily prove agent workflow correctness; real model evals run for agent/tool/prompt changes | Keeps CI deterministic while still testing agent behavior when it changes |
| R22 | DATA-001 hero comparison | **IL-10 vs matched no-cytokine control under LPS 2000 ng/mL** | Clearest donor-consistent visual signal; conservative anti-inflammatory interpretation (see `docs/DEMO_DECISIONS.md`, issue #12) |

See `docs/DEVELOPMENT_WORKFLOW.md` for the pipeline; `docs/DATA_CONTRACTS.md` /
`docs/TRACE_MODEL.md` / `docs/MCP_TOOLS.md` / `docs/ARCHITECTURE.md` for contracts; and
`docs/DEMO_DECISIONS.md` for current demo-story decisions and DATA-001 candidate comparisons.

---

## Still open

### Product / user story
- Final screen-recording script (data subset + hero question now chosen; script finalized near demo).

### Data
- ✅ Hero comparison + Perturb-PBMC subset chosen → **R22** / DATA-001 (issue #12).
- Exact fixture columns, units, preprocessing state, provenance, and validation contract →
  being finalized in **SPEC-006** (#15).

### Statistics
- Exact v0.1 method menu; normalization assumptions; donor-consistency metric; paired vs
  unpaired; p-value test; multiple-testing method; best-practice source list.
- → handoff issue **STAT-001**.

### RAG / corpus
- Exact source list; entity-extraction method; exact figure/caption inclusion threshold;
  chunking parameters; retrieval-eval design.

### Architecture
- Kimi/OpenRouter integration details and fallback behavior.

### Evals
- Exact first eval cases and report display details.

### Autoresearch
- Include live autoresearch only if it visibly improves a metric; otherwise ship policy files + eval dashboard + documented loop and defer the live loop.
