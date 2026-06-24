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
- 🔬 SPEC-006 demo dataset fixture contract (depends on DATA-001)
- 🟡 SPEC-008 labels/templates — templates done; label taxonomy mostly in place

## Handed-off research (async runners) 🔬
- ✅ **DATA-001** complete and **decided**: hero comparison = **IL-10 vs matched no-cytokine
  control under LPS 2000 ng/mL** (see `docs/DEMO_DECISIONS.md`). Unblocks SPEC-006.
- 🔬 **STAT-001** stats best practices → finalize the supported method menu.
- 🟡 Corpus direction set; exact source list still depends on the hero question.

## Phase 1 — the harness ✅
- ✅ `ci.yml` (lint/test/typecheck; `eval-smoke` path-conditional, non-blocking until gate
  activation)
- ✅ `review.yml` + `scripts/spawn-review-agent.sh` (Claude + Codex in tmux, verdict-gated)
- ✅ GitHub native auto-merge; validated end-to-end on PRs #1–#2
- ✅ runner registered + branch protection set

## Phase 2+ — implementation waves (HANDOFF §29.3, §30)
IMPL-001 scaffold · IMPL-002 shared schemas pkg · IMPL-003 FastAPI skeleton ·
IMPL-004 ToolRegistry skeleton · IMPL-005 trace models · IMPL-006 Next.js shell ·
IMPL-007 seeded demo project · IMPL-008 eval runner skeleton → web chat → dashboard →
eval page → deployment → polish + screen recording.

Foundational agents can start on FastAPI skeleton, Next.js shell, ToolRegistry skeleton, trace
models, and eval runner once issue decisions are reflected in docs. Data fixture, analysis,
corpus, dashboard/report, and deployment remain blocked until DATA-001 final selection,
STAT-001, CORPUS-001, and SPEC-006 are resolved.

## Eval-gate activation milestone
`eval-smoke` becomes a **required** check once the end-to-end hero workflow runs against the
seeded demo project (target: after IMPL of the analysis + tool pipeline, i.e. once
`run_comparison` → `rank_proteins` → `export_report` work on fixture data). Until then it runs
informationally only (`docs/EVALS.md`).
