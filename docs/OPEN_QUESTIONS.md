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

See `docs/DEVELOPMENT_WORKFLOW.md` for the full pipeline.

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
