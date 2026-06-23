# Open Questions

> **Rule (from HANDOFF §23.11):** Do not silently resolve open questions in implementation
> PRs. If implementation requires resolving one, label the issue `needs-human-decision`.

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

See `docs/DEVELOPMENT_WORKFLOW.md` for the pipeline and `docs/DATA_CONTRACTS.md` /
`docs/TRACE_MODEL.md` / `docs/MCP_TOOLS.md` / `docs/ARCHITECTURE.md` for the contracts drafted
in this session.

---

## Still open

### Product / user story
- Final primary persona: Nomic internal scientist vs field application scientist vs customer translational scientist.
- Final hero biological question (not selected — depends on data exploration).
- Final screen-recording script (deferred until data subset + hero question chosen).

### Data
- Exact Perturb-PBMC subset; stimulation context; perturbagen/control comparison; protein panel.
- Data format & preprocessing state; direct subset vs transformed direct subset.
- → handoff issue **DATA-001** (explore + propose 3 candidate hero comparisons).

### Statistics
- Exact v0.1 method menu; normalization assumptions; donor-consistency metric; paired vs unpaired; whether p-values are central; multiple-testing method; best-practice source list.
- → handoff issue **STAT-001**.

### RAG / corpus
- Exact source list; entity-extraction method; whether external biology refs / figure captions / supplements are included; chunking parameters; retrieval-eval design.

### Architecture
- Package managers (Python: uv? — owner default is uv; Node: pnpm/npm); SQLAlchemy vs SQLModel; MCP server process layout (separate service vs mounted in API); storage backend & object storage; schema-generation approach (Pydantic→TS vs OpenAPI); Kimi integration details.

### Evals
- Exact eval-case schema; which evals run in CI; which require real model calls; score threshold gating merge; how reports are displayed.

### Autoresearch
- Include live autoresearch only if it visibly improves a metric; otherwise ship policy files + eval dashboard + documented loop and defer the live loop.
