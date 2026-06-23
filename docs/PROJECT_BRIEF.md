# Project Brief

Condensed from `HANDOFF.md` §1–§5, §18. The authoritative plan is the HANDOFF.

## Product thesis
Scientists should be able to bring a biological question and a proteomics dataset to an
agent, and the agent should create an analysis project, request data, validate the upload,
run appropriate analysis tools, retrieve supporting evidence, generate plots, and produce a
findings report — operable identically through a **web app** and an **external MCP client**,
over the **same project state**. Not chat bolted onto a dashboard: an agent-native scientific
workspace.

## Target user
Primary persona: **a Nomic internal scientist** using agent-native tools to analyze
functional proteomics data. Secondary: a field application scientist helping a customer
interpret a dataset. (Final persona for the video remains open — `docs/OPEN_QUESTIONS.md`.)

## Demo flow — the hero handoff (do not cut)
```
agent creates project → tool returns upload/dashboard URL → user opens app →
selects a direct subset of public Nomic Perturb-PBMC data → app state updates →
agent resumes: validate → define comparison → run analysis → rank proteins →
plot → retrieve evidence → evidence-backed report → dashboard shows result + traces
```

## Pareto v0.1 scope (build this)
Landing page · demo project page · upload/select page · web chat over the shared tool layer ·
MCP server with the MVP tools · direct Perturb-PBMC subset · dataset validation · one
comparison analysis · one plot · small entity-aware RAG corpus · evidence-backed report ·
tool-call audit trace · eval dashboard · AGENTS.md + Makefile + tests · screen recording.

## Non-goals (do not build yet)
Real auth · arbitrary user datasets beyond the demo schema · full statistical-method
autonomy · broad paper-scraping · full autoresearch loop (unless visibly useful) · multiple
complex workflows · production storage/retention · Nomic Portal clone · complex LIMS · general
paper chatbot.

## Critical features not to cut
Agent/app handoff · web+MCP parity · tool-call traces · real public-data subset · small but
real RAG · eval page · clean repo/harness docs.

## Positioning statement (draft — not final, HANDOFF §34)
> A small agent-native functional proteomics workbench over public Perturb-PBMC data: a web
> app + MCP server over a shared tool registry, entity-aware RAG over Nomic/nELISA sources, a
> bounded analysis workflow, evidence-backed reporting, tool-call traces, and a small eval
> dashboard — demonstrating how I think about scientist-facing software, biological data
> pipelines, and agentic tooling for proteomics.
