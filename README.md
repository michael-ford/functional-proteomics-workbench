# Agent-Native Functional Proteomics Workbench

A narrow, high-signal vertical slice of agent-native scientific software: a stateful,
auditable, agent-operated analysis workspace for functional proteomics, built on a
direct subset of public Nomic **Perturb-PBMC** data.

> **Status:** scaffolding + spec sprint. No application code yet. See `HANDOFF.md` for the
> full plan and `docs/OPEN_QUESTIONS.md` for what is intentionally unresolved.

## What it is

A scientist brings a biological question and a proteomics dataset to an agent. The agent
creates an analysis project, returns an upload/dashboard URL, validates the dataset, runs a
bounded statistical comparison, retrieves supporting evidence from a small entity-aware
Nomic/nELISA corpus, generates a plot and an evidence-backed report — all over **shared
project state** reachable from both a **web app** and an **MCP server**, with full
**tool-call traces** and a small **eval dashboard**.

## Repo layout

| Path | Purpose |
|------|---------|
| `docs/` | Architecture, data contracts, MCP tools, trace model, evals, security, workflow |
| `apps/web/` | Next.js web app (human-facing surface) |
| `services/api/` | FastAPI backend |
| `services/mcp/` | MCP server (shares the tool registry with the API) |
| `packages/` | `analysis`, `corpus`, `storage`, `shared-schemas` |
| `evals/` | Eval cases, runners, results |
| `demo_data/` | Perturb-PBMC subset + manifest |
| `agent_policies/` | Editable policy files (autoresearch targets) |
| `scripts/` | Ingest, corpus build, seed, eval, autoresearch |
| `.github/` | CI workflows, issue/PR templates, CODEOWNERS |

## Quickstart

> Filled in during the implementation wave. See `Makefile` for the intended entrypoints
> (`make setup`, `make test`, `make eval`, `make run-local`).

## Key docs

- `HANDOFF.md` — authoritative project plan
- `AGENTS.md` — how coding/review agents work in this repo
- `docs/DEVELOPMENT_WORKFLOW.md` — CI, dual-agent review, auto-merge
- `docs/OPEN_QUESTIONS.md` — unresolved decisions (do not silently resolve)

## Note

This is a demonstration system built as a supplemental demo for a Nomic Bio software
engineering application. It is not production software: no real account system, demo data
may be reset, and data retention is not production-grade.
