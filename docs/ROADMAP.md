# Roadmap

Build DAG and implementation waves (HANDOFF §29–§30), annotated with current status.

## Critical dependency
**Shared schemas + Tool registry + Trace model** unblock everything else. Specs for all three
are drafted (`docs/DATA_CONTRACTS.md`, `docs/MCP_TOOLS.md`, `docs/TRACE_MODEL.md`).

## Status legend
✅ done · 🟡 in progress · ⬜ not started · 🔬 handed off (async research)

## Phase 0 — bootstrap ✅
- ✅ Public repo (`michael-ford/functional-proteomics-workbench`)
- ✅ Skeleton + governance docs (DEVELOPMENT_WORKFLOW, OPEN_QUESTIONS, AGENTS, README)
- ✅ Self-hosted runner `fpw-mac-runner` registered + online
- ✅ Branch protection requires `ci` + `review (claude)` + `review (codex)`; auto-merge on

## Spec sprint (in-session) 🟡
- ✅ SPEC-001 repo constitution / stack decisions (R7–R14)
- ✅ SPEC-002 data contracts
- ✅ SPEC-003 tool registry & MCP/web parity (ARCHITECTURE)
- ✅ SPEC-004 trace & eval replay model
- ✅ SPEC-005 MVP tool list + first-pass schemas
- ✅ SPEC-007 CI / governance / security (DEVELOPMENT_WORKFLOW, SECURITY)
- ✅ EVALS spec (eval-case schema + gating policy) drafted
- ✅ SPEC-006 demo dataset fixture contract
- 🟡 SPEC-008 labels/templates — templates done; label taxonomy mostly in place

## Handed-off research (async runners) 🔬
- ✅ **DATA-001** complete and **decided**: hero comparison = **IL-10 vs matched no-cytokine
  control under LPS 2000 ng/mL** (see `docs/DEMO_DECISIONS.md`). Unblocks SPEC-006.
- ✅ **STAT-001** method menu approved; see `docs/ANALYSIS_METHODS.md`.
- ✅ **CORPUS-002** paper-discovery tooling and IL-10/LPS candidate manifest complete.
- ✅ **CORPUS-001** v0.1 source list and retrieval policy frozen; see `docs/CORPUS.md`.

## Phase 1 — the harness ✅
- ✅ `ci.yml` (lint/test/typecheck; `eval-smoke` path-conditional, non-blocking until gate
  activation)
- ✅ `review.yml` + `scripts/spawn-review-agent.sh` (Claude + Codex in tmux, verdict-gated)
- ✅ GitHub native auto-merge; validated end-to-end on PRs #1–#2
- ✅ runner registered + branch protection set

## Phase 2+ — implementation waves (HANDOFF §29.3, §30)
✅ IMPL-001 scaffold · ✅ IMPL-002 shared schemas pkg · ✅ IMPL-003 FastAPI skeleton ·
✅ IMPL-004 ToolRegistry skeleton · ✅ IMPL-005 trace models · ✅ IMPL-006 Next.js shell ·
✅ IMPL-007 seeded demo project · ✅ IMPL-008 eval runner skeleton · ✅ IMPL-009 bounded
analysis package · ✅ IMPL-011 MCP server wiring · ✅ agent lifecycle hardening through
IMPL-017.

Next implementation sequence:

1. **IMPL-010** corpus ingestion and retrieval skeleton.
2. **IMPL-012** web chat/tool execution path over shared state.
3. **IMPL-013** dashboard, report view, and trace inspection UI.
4. **IMPL-014** deployment, demo reset, and screen-recording readiness.

IMPL-010 is now unblocked by `docs/CORPUS.md`. Later UI/report/deployment tickets still depend
on the corpus skeleton and the end-to-end hero workflow.

## Eval-gate activation milestone
`eval-smoke` becomes a **required** check once the end-to-end hero workflow runs against the
seeded demo project (target: after IMPL of the analysis + tool pipeline, i.e. once
`run_comparison` → `rank_proteins` → `export_report` work on fixture data). Until then it runs
informationally only (`docs/EVALS.md`).
