# AGENTS.md

Operating guide for coding and review agents working in this repo.

> **Status:** placeholder — expanded during the spec sprint (SPEC-001/003). The
> authoritative project plan is `HANDOFF.md`.

## Mission

Build a narrow, polished, agent-native functional proteomics workbench over a direct
subset of public Nomic Perturb-PBMC data. Optimize for minimizing human specification/
review bottlenecks — not lines of code.

## Architecture (one paragraph)

A Next.js web app and a Python MCP server operate over **shared project state** via a
**shared tool registry** (the MCP server and web chat must not reimplement tool logic).
FastAPI backend, Postgres + pgvector, Python analysis/corpus packages, pytest-based evals.
See `docs/ARCHITECTURE.md`.

## Setup / test / eval commands

See `Makefile`: `make setup`, `make test`, `make eval`, `make run-local`. (Stubs until the
IMPL wave.)

## Stable contracts (change only in a PR labeled `contract-change`)

- `packages/shared-schemas/**`
- `docs/DATA_CONTRACTS.md`, `docs/MCP_TOOLS.md`, `docs/TRACE_MODEL.md`
- `services/api/migrations/**`, `services/mcp/**`
- `evals/cases/**`

## PR expectations

- Every PR flows through CI + Claude review + Codex review and **auto-merges on green**
  (see `docs/DEVELOPMENT_WORKFLOW.md`). There is no human merge step.
- Tools that are added/modified **must be traced**.
- Do not change contract files outside a `contract-change` PR.
- No secrets committed; no fake data, citations, or tool traces.

## Handling open questions

Do **not** silently resolve items in `docs/OPEN_QUESTIONS.md`. If a task requires
resolving one, stop and surface it (label `needs-human-decision`).

## Do-not-do list (from HANDOFF §41)

Generic chatbot · generic omics platform · real auth · invented hero biological question ·
undocumented statistical assumptions · fake provenance/citations/traces · arbitrary SQL ·
tools that bypass tracing · duplicated tool logic across MCP/web · contract changes in
non-`contract-change` PRs.
