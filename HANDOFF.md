Agent-Native Functional Proteomics Workbench

Comprehensive Handoff Document for Spec Completion, Monorepo Scaffolding, CI Harness, and Multi-Agent Implementation Workflow

0. Purpose of This Document

This document is a comprehensive handoff for continuing development of the Agent-Native Functional Proteomics Workbench in a new Codex, Claude Code, or similar AI-assisted development session.

It captures:

1. The product concept.
2. The decisions that have been locked.
3. The open questions that remain unresolved.
4. The intended Pareto-scoped v0.1 demo.
5. The architecture direction.
6. The required specification sprint.
7. The monorepo and CI harness direction.
8. The multi-agent development workflow.
9. The GitHub issue/PR governance model.
10. The implementation roadmap after specs are complete.
11. The reference materials a future agent should read before continuing.

This document should be treated as the authoritative handoff from the planning conversation so far.

The immediate goal is not yet to implement the full product.

The immediate goal is to:

1. Create a GitHub monorepo.
2. Add the core repo constitution and agent-readable docs.
3. Define stable contracts and boundaries.
4. Build the CI/eval/development harness.
5. Prepare high-quality GitHub issues for implementation agents.
6. Then begin implementation through PR-based, multi-agent development.

The key instruction for any future agent: do not invent answers to open questions. Preserve open questions as open questions until explicitly resolved.

---

1. Project Summary

1.1 Working Title

The working title is:

«Agent-Native Functional Proteomics Workbench»

Product naming is not currently a priority. Do not spend time naming the product unless explicitly asked.

Previously discussed candidate names included:

- nELISA Agent Workbench
- Functional Proteomics Agent Console
- Proteomics Copilot Workbench
- Agent-Native Functional Proteomics Workbench

The current working title is acceptable for internal docs and scaffolding.

1.2 Why This Project Exists

The project is a high-impact supplemental demo for an application to a Nomic Bio software engineering role.

The demo should communicate that the builder understands:

- scientific software,
- biological data pipelines,
- functional proteomics workflows,
- LIMS-like state and project management,
- agent-native architecture,
- MCP/server-tool design,
- web application development,
- RAG over scientific documents,
- entity-aware biomedical retrieval,
- eval-driven agent reliability,
- AI-assisted development harnesses,
- and software engineering best practices in the AI-agent era.

This should not feel like a generic chatbot or a generic dashboard.

It should feel like a narrow but high-signal vertical slice of future scientific software: a stateful, auditable, agent-operated analysis workspace for functional proteomics.

---

2. Core Product Thesis

The central product thesis is:

«Scientists should be able to bring a biological question and a proteomics dataset to an agent, and the agent should be able to create an analysis project, request data, validate the upload, run appropriate analysis tools, retrieve supporting evidence, generate plots, and produce a findings report.»

The same project should be usable through:

1. a browser-based web app, and
2. an external MCP client such as Claude Desktop, ChatGPT, Codex, Claude Code, or similar tools where MCP/server tools are supported.

The browser UI and MCP tools should operate over the same project state.

This is not “chat bolted onto a dashboard.”
It is an agent-native scientific workspace.

---

3. Core Demo Narrative

The core demo story is:

«A scientist asks an AI assistant to create a functional proteomics analysis project. The agent calls an MCP tool, creates project state in the web app, returns an upload URL, the user uploads or selects a direct subset of public Nomic Perturb-PBMC data, the agent resumes analysis, validates the dataset, runs a bounded statistical comparison, retrieves relevant Nomic/nELISA evidence, generates a plot and report, and the web app displays the result with tool traces and eval traces.»

The signature moment is the handoff:

Agent creates project
→ tool returns upload/dashboard URL
→ user opens app
→ dataset is uploaded or selected
→ app state updates
→ agent resumes analysis
→ dashboard/report appears

This handoff is the most important product interaction. Do not cut it.

---

4. Target Audience for the Demo

The demo needs to impress several overlapping reviewers.

4.1 Hiring Manager Perspective

The hiring manager should see:

- direct relevance to Nomic,
- domain understanding,
- ability to ship a polished applied demo,
- AI-agent fluency,
- and practical product judgment.

Most important artifacts for this audience:

- deployed app link,
- short walkthrough video,
- concise application note,
- direct mapping to job needs.

4.2 Lead Software Engineer Perspective

A senior software engineer should see:

- clean service boundaries,
- typed contracts,
- tests,
- CI,
- evals,
- traceability,
- deployment discipline,
- reasonable scope control,
- no fake data presented as real,
- no giant unreviewable AI-generated code dump.

Most important artifacts for this audience:

- GitHub repo,
- architecture docs,
- CI status,
- tests/evals,
- PR workflow,
- tool schemas,
- clear storage and trace models.

4.3 Lead AI Agent Engineer Perspective

An agent engineer should see:

- MCP-first design,
- web/MCP parity,
- atomic tools,
- shared state,
- tool-call traces,
- eval-driven reliability,
- bounded autonomy,
- entity-aware RAG,
- safe tool execution,
- agent-readable repo documentation,
- and a development harness for AI-assisted coding.

Most important artifacts for this audience:

- MCP tool trace,
- web-chat full trace,
- eval dashboard,
- "AGENTS.md",
- tool registry design,
- issue/PR agent workflow.

---

5. Primary User Persona

The preferred primary persona is:

«A Nomic internal scientist using agent-native tools to analyze functional proteomics data.»

A strong secondary persona is:

«A field application scientist helping a customer interpret a functional proteomics dataset.»

A previously used working persona:

«Dr. Chen, a translational scientist, has received secreted-proteomics data from a PBMC perturbation experiment. She wants to identify which perturbations produce biologically meaningful inflammatory responses, compare the results against public reference data and scientific literature, and generate a short evidence-backed report for her project team.»

The current preference is Nomic internal scientist, with field application scientist as an acceptable secondary framing.

Open question remains:

- Should the final video/story optimize for a Nomic internal scientist, a field application scientist, or a customer-facing translational scientist?

Do not resolve this without explicit user input.

---

6. Dataset Strategy

6.1 Locked Decision

The demo should use a direct subset of public Nomic Perturb-PBMC data.

This is locked.

Avoid synthetic-first data. Synthetic data can be used only as test fixtures or tiny controlled eval fixtures, not as the main demo substrate.

6.2 Current Understanding

The relevant public data anchor is Nomic/nplexbio’s public Perturb-PBMC / nELISA-PBMC dataset.

Known high-level attributes from Nomic materials:

- PBMC secretome / functional proteomics dataset.
- Public Perturb-PBMC dataset.
- Thousands of samples.
- Multiple donors.
- Multiple stimulations.
- Many perturbagens.
- Many secreted-protein measurements.

A future implementation agent must verify the current dataset location, format, license, and exact fields before coding data ingestion.

6.3 Pareto Scope for v0.1

Use a curated subset, not the full dataset in every workflow.

Candidate subset shape:

6 donors
1 stimulation context
2–4 perturbagens
20–50 proteins
1 primary comparison

The exact subset is not locked.

The subset should be chosen after data exploration, not guessed.

6.4 Open Questions

- Which exact stimulation context should be used?
- Which perturbagen/control comparison should be used?
- Which proteins should be included?
- Should the subset include all donors?
- Should the subset be wide or long internally?
- Should the uploaded demo dataset be a direct extract of Perturb-PBMC or a transformed direct subset?
- Should public Perturb-PBMC also be used as a reference dataset against a separate uploaded subset?

Do not invent these answers. Create an early data-exploration issue to propose candidate subsets.

---

7. Biological Question

7.1 Current State

The hero biological question is not locked.

Candidate direction discussed:

Compare IFNG perturbation against control under an LPS or related stimulation context, identify strongest secreted-protein changes, check donor consistency, and ground interpretation in nELISA/Perturb-PBMC evidence.

This is only a candidate.

7.2 Requirements for Final Hero Question

The final hero question should:

- be answerable from the selected Perturb-PBMC subset,
- produce visually interesting ranked results or a plot,
- involve recognizable immunology/proteomics entities,
- exercise donor-aware interpretation,
- require evidence retrieval from the corpus,
- be explainable in a short video,
- and not require extensive biological caveats beyond the demo’s scope.

7.3 Open Question

The exact biological question remains open and should be selected after exploring the public dataset.

Create an issue:

DATA-001 Explore Perturb-PBMC and propose 3 candidate hero comparisons

Each candidate should include:

- stimulation context,
- perturbagen/control groups,
- donors,
- proteins affected,
- expected plot,
- why it is biologically interpretable,
- why it is good for a demo,
- limitations.

---

8. Statistical Methods Strategy

8.1 Locked Direction

The statistical-method layer should be agent-native but bounded.

The agent should not simply run a hardcoded test from a dropdown.
The agent also should not have unconstrained freedom to invent arbitrary methods.

The desired pattern:

Agent inspects dataset
→ retrieves/statements analysis guidance
→ proposes analysis plan
→ validates supported method
→ runs approved method
→ records assumptions and limitations

8.2 Important Principle

The agent should be able to reason through method choice using tools, but only within a safe, supported, logged set of methods.

The product should demonstrate that the system can help choose analysis methods, not merely execute one.

8.3 Pareto Scope

For v0.1, do not solve full statistical-method autonomy.

Implement one defensible path plus the scaffolding for method choice.

Candidate minimal method menu:

effect_size_summary
donor_aware_paired_difference
simple_group_test
multiple_testing_correction
donor_consistency_score

This exact menu is not fully locked. It is a candidate minimal menu.

8.4 Required AnalysisPlan Artifact

Any analysis should generate an "AnalysisPlan" artifact containing:

chosen method
why it was selected
dataset assumptions
donor handling
replicate handling if relevant
multiple-testing correction status
limitations
unsupported assumptions

8.5 Open Questions

- What is the exact v0.1 method menu?
- What normalization does the public data already use?
- Should analysis happen on raw, normalized, log-transformed, or fold-change values?
- What donor-consistency metric should be used?
- Should the comparison be paired by donor?
- Should p-values be included in the Pareto demo or should the first demo emphasize effect size and consistency?
- What sources should guide method choice?

Create a research/spec issue:

STAT-001 Research statistical best practices for Perturb-PBMC subset comparisons

Acceptance criteria:

- Read relevant dataset docs and methods.
- Determine what preprocessing exists in the public data.
- Propose 2–3 supported analysis methods.
- Recommend one for v0.1.
- Specify assumptions and limitations.
- Avoid overclaiming.

---

9. RAG and Corpus Strategy

9.1 Locked Direction

The system should include RAG, but not generic document chat.

The RAG system should be:

- entity-aware,
- source-grounded,
- designed for biological/proteomics questions,
- able to retrieve exact protein/stimulus/perturbagen terms,
- and able to support final report claims.

9.2 Pareto Scope

Do not scrape dozens of papers in v0.1.

Use a small but high-coverage corpus for the hero workflow.

Minimum corpus candidates:

Nomic Perturb-PBMC page
Nomic / nELISA public documentation or pages
nELISA Nature Methods paper text
nELISA-PBMC GitHub README / dataset notes
selected figure captions / supplementary methods if available
1–3 background sources only if needed for the hero biology

9.3 Entity-Aware Chunking

Chunks should preserve biomedical metadata.

Example chunk metadata:

{
  "chunk_id": "chunk_...",
  "text": "...",
  "source_id": "source_...",
  "source_type": "paper|docs|github|webpage|supplement",
  "title": "...",
  "section": "...",
  "entities": ["IL6", "CXCL10", "LPS", "IFNG", "PBMC"],
  "assay_context": ["nELISA", "secretome", "perturbation"],
  "citation": {
    "url": "...",
    "doi": "...",
    "paper_title": "...",
    "authors": "...",
    "year": "..."
  }
}

9.4 Corpus Manifest

The corpus build should generate a manifest.

Candidate manifest fields:

source_id
title
source_type
url_or_reference
license_or_access_note
topics_covered
entities_extracted
sections_included
chunk_count
embedding_status
full_text_status
citation_metadata
known_gaps

9.5 Corpus Acceptance Criteria

The corpus is acceptable for v0.1 when it can retrieve evidence for:

Perturb-PBMC dataset provenance
nELISA assay context
PBMC perturbation design
selected stimulation biology
selected perturbagen biology
selected top-protein biology
donor/stimulation interpretation
analysis limitations

Additional acceptance criteria:

Every final report claim must be classified as:
  data-derived
  source-derived
  interpretive
  limitation/uncertainty

Every source-derived claim must point to retrieved evidence.

Every entity in the hero workflow should be entity-indexed.

Retrieval evals should include exact symbol/name queries and synonym-style queries where relevant.

9.6 Open Questions

- Exact source list.
- Exact entity extraction approach.
- Whether external biology references are needed.
- Whether figure captions and supplements are included in v0.1.
- Whether the user’s paper extraction system is used immediately or later.
- Whether to build broad corpus ingestion now or only a curated fixture.

---

10. Product Surfaces

The system has three surfaces.

10.1 Web App

The web app is the human-facing interface.

Pareto v0.1 pages:

/
  Landing page + demo entry + MCP instructions

/projects/demo
  Project dashboard

/projects/demo/upload
  Upload or select demo dataset

/projects/demo/evals
  Engineering harness / eval output

The dashboard should show:

Project status
Dataset validation summary
Comparison definition
Ranked protein table
One plot
Evidence cards
Generated report
Tool-call trace

10.2 Web Chat

Web chat remains in scope.

The web chat should use the same tool registry as the MCP server.

The web chat is important because it allows the system to record a richer trace than external MCP clients.

For web chat, trace should include:

user messages
assistant messages
model used
tool calls
tool inputs
tool outputs
retrieved evidence
analysis artifacts
final answer
report artifacts
errors/retries if any

The likely model for web chat is Kimi, but exact integration details remain open.

Open questions:

- Which exact Kimi model/endpoint?
- Does it support native tool calling in the desired way?
- Should a fallback provider be implemented?
- Should model calls be mocked in CI?

10.3 MCP Server

The MCP server is the agent-facing programmable interface.

It should expose tools that operate over the same project state as the web app.

The MCP server should support at least one external client path well. Do not attempt to perfect every possible MCP client before the demo.

Target clients / compatibility goals:

Claude Desktop / Claude MCP usage
ChatGPT / Apps SDK-style MCP usage where available
Codex / Claude Code style local or remote tool interaction where practical

Do not overbuild the client matrix.

10.4 Eval Page

The eval page is a demo-only engineering credibility surface.

It should show:

eval suite status
case-level pass/fail
tool-call trace
citation checks
numeric checks
unsupported-claim checks
latest score

For web chat evals, it can show full replay.
For external MCP usage, it can show server-side tool traces.

The eval page would not necessarily exist in a production user-facing product. It exists here to demonstrate engineering quality.

---

11. Trace Model

11.1 Locked Direction

Traceability is a core feature, not just debugging.

The system should trace:

- web-chat interactions,
- MCP tool calls,
- analysis outputs,
- retrieval events,
- report generation,
- eval replay,
- errors,
- timings,
- artifact URLs.

11.2 Two Trace Modes

Web Chat Full Trace

Available when interaction happens through the built-in web chat.

Includes:

chat session id
user messages
assistant messages
model metadata
tool call sequence
tool inputs
tool outputs
retrieval chunks
analysis artifact refs
report refs
final response
latency/timing
errors/retries

MCP Server-Side Trace

Available when interaction happens through external MCP clients.

Includes:

session/token/project id if available
tool name
tool input
tool output
project affected
artifact refs
status
error
timing

The external client’s full conversational state is not available unless explicitly exported or proxied through the system.

11.3 Trace Schema Must Be Specified Early

The trace schema is a blocking contract before broad implementation because it is used by:

- MCP server,
- web chat,
- tool registry,
- eval runner,
- eval page,
- dashboard,
- report generation,
- and debugging.

Create a spec issue:

SPEC-004 Trace and eval replay schema

---

12. Agent-Native Architecture Principles

The system should follow these principles.

12.1 UI/MCP Parity

Every major web app action should have a corresponding tool action.

Examples:

Create project       ↔ create_project
Upload/select data   ↔ create_upload_url / dataset selection tool
Validate dataset     ↔ validate_dataset
Inspect schema       ↔ inspect_dataset_schema
Define comparison    ↔ define_comparison
Run analysis         ↔ run_comparison
Rank proteins        ↔ rank_proteins
Create plot          ↔ create_plot
Search evidence      ↔ search_corpus
Attach evidence      ↔ attach_evidence
Export report        ↔ export_report
View traces          ↔ get_trace
Run evals            ↔ run_eval_suite

12.2 Atomic Tools First

Tools should be composable primitives.

Avoid only exposing large magic tools.

Higher-level convenience tools are allowed later if they internally compose atomic tools and expose their traces.

12.3 Shared Tool Registry

The MCP server and web chat should not separately implement tool logic.

Use a shared tool registry:

ToolRegistry
  used by:
    web chat
    MCP server
    backend API
    eval runner

Tool definition should include:

name
description
input schema
output schema
handler
permissions
trace policy
eval tags

12.4 Shared Project State

The project is the core unit of state.

The project contains:

dataset files
schema profiles
analysis plans
analysis results
plots
retrieved evidence
reports
tool traces
chat traces
eval traces

12.5 File-Like Inspectability

Even if storage is implemented in Postgres/object storage, the app should expose project state in a file-like, inspectable way.

Example conceptual project tree:

/projects/proj_042/
  project.json
  context.md

  uploads/
    raw_dataset.csv

  datasets/
    normalized_long.parquet
    schema_profile.json

  analyses/
    comparison_001/
      analysis_spec.json
      differential_results.csv
      volcano_plot.json
      donor_variability.csv
      notes.md

  evidence/
    retrieved_chunks.json
    source_cards.md

  reports/
    findings_report.md

  traces/
    tool_calls.jsonl
    chat_trace.jsonl
    eval_trace.jsonl

This project tree is conceptual and may be backed by database/object storage.

---

13. Storage Direction

13.1 Locked Preference

Avoid pure local filesystem as primary source of truth because remote MCP clients need durable URLs and project state.

Prefer:

Postgres for structured state
object storage or Railway volume for file artifacts
storage adapter exposing file-like project paths

13.2 Candidate Storage Model

Postgres:
  projects
  sessions
  datasets
  analyses
  tool_calls
  chat_messages
  corpus_sources
  corpus_chunks
  entities
  evidence_attachments
  reports
  eval_runs
  eval_cases

Object storage / Railway volume:
  uploaded CSVs
  processed parquet files
  plots
  reports
  exported artifacts

13.3 Open Questions

- Railway volume vs S3-compatible bucket vs Postgres byte storage.
- Whether to use local filesystem for dev and object storage for deployment.
- How long demo uploads persist.
- Whether uploaded data is deleted automatically.
- Whether each viewer gets a fresh demo project.
- Whether a single persistent demo project is enough.

Current pragmatic stance:

- Since this is a job-application demo, persistent production-grade retention policy is not a priority.
- The app can be shut down after utility is complete.
- Still avoid sloppy handling of uploaded data and avoid promising privacy guarantees that are not implemented.

---

14. Authentication and Demo Sessions

14.1 Locked Decision

No real account system is required for v0.1.

Use demo mode.

The UI may look account-like, but authentication should not become a major feature.

Possible UX:

Continue as demo user

14.2 MCP Token

MCP may use a demo token.

Example conceptual config:

{
  "mcpServers": {
    "functional-proteomics-workbench": {
      "url": "https://example.railway.app/mcp",
      "headers": {
        "Authorization": "Bearer DEMO_TOKEN"
      }
    }
  }
}

Exact MCP client configuration remains open.

14.3 Open Questions

- Should the demo token be static?
- Should each browser session generate a token?
- Should MCP access require a project-scoped token?
- Should the external MCP client be read/write or read-mostly?
- What is the minimum safe auth boundary for the demo?

---

15. MVP Tool List

15.1 Locked Direction

Use atomic, project-centered tools.

Do not define every possible tool before implementation.

15.2 Pareto v0.1 Tool List

Freeze this MVP tool list unless explicitly changed:

create_project
get_project_status
create_upload_url
validate_dataset
inspect_dataset_schema
define_comparison
run_comparison
rank_proteins
create_plot
search_corpus
attach_evidence
export_report
run_eval_suite
get_trace

This is the current recommended MVP set.

15.3 Deferred Tools

These may be valuable later but should not block v0.1:

list_project_files
preview_dataset
profile_dataset
infer_experimental_design
select_samples
retrieve_analysis_best_practices
propose_analysis_plan
validate_analysis_plan
list_supported_methods
read_source_chunk
write_project_note
run_eval_case
get_eval_results
run_autoresearch_loop

Some deferred tools may become necessary during schema design. If so, explicitly promote them with rationale.

15.4 Tool Schema Requirements

Every tool must define:

input schema
output schema
error schema
permissions
trace behavior
artifact behavior
eval tags

15.5 Tool Result Pattern

Where appropriate, tools should return URLs and next actions.

Example conceptual output:

{
  "project_id": "proj_demo_042",
  "status": "created",
  "upload_url": "https://app.example.com/projects/proj_demo_042/upload",
  "dashboard_url": "https://app.example.com/projects/proj_demo_042",
  "next_actions": [
    "upload_dataset",
    "validate_dataset",
    "define_comparison"
  ]
}

Exact schemas remain open and must be specified in "docs/MCP_TOOLS.md" and shared schema packages.

---

16. Core Data Contracts

16.1 Blocking Need

Before multi-agent implementation begins, define initial shared contracts.

They do not need to be perfect, but IDs and relationships must be stable enough to allow parallel work.

16.2 Required Contract Types

Initial contracts:

Project
Dataset
DatasetSchemaProfile
AnalysisPlan
AnalysisResult
ProteinRanking
PlotArtifact
EvidenceSource
EvidenceChunk
EvidenceAttachment
ReportArtifact
ToolCallTrace
ChatSession
ChatMessage
ChatTrace
EvalCase
EvalResult
EvalRun

16.3 Minimal Relationship Model

Project
  has many Datasets
  has many AnalysisPlans
  has many AnalysisResults
  has many EvidenceAttachments
  has many Reports
  has many ToolCallTraces
  has many ChatSessions
  has many EvalRuns

Dataset
  belongs to Project
  has one/many DatasetSchemaProfiles

AnalysisPlan
  belongs to Project
  references Dataset
  produces AnalysisResult

AnalysisResult
  belongs to Project
  references AnalysisPlan
  may include ProteinRanking
  may include PlotArtifact

EvidenceAttachment
  belongs to Project
  references EvidenceChunks
  may support ReportArtifact

ToolCallTrace
  belongs to Project where project-scoped
  belongs to ChatSession or EvalRun where applicable

ChatTrace
  belongs to ChatSession
  references ToolCallTraces

EvalRun
  contains EvalResults
  may replay tool traces

16.4 Open Questions

- Exact field names.
- Whether schemas are generated from Pydantic to TypeScript or manually duplicated.
- Whether SQLModel is used.
- Whether OpenAPI schema is used as source of truth for frontend clients.
- How versioning works for schema changes.

---

17. Technical Stack Direction

17.1 Current Recommended Stack

The current recommended stack is:

Monorepo

Frontend:
  Next.js
  TypeScript
  Tailwind
  shadcn/ui or similar component system
  Plotly or comparable plotting library

Backend:
  FastAPI
  Python
  Pydantic
  SQLAlchemy or SQLModel
  Alembic migrations

MCP:
  Python MCP server
  ideally sharing service/tool code with FastAPI backend

Database:
  Postgres
  pgvector for vector search

Analysis:
  Python
  pandas or polars
  scipy
  statsmodels
  pydantic models for analysis contracts

RAG/corpus:
  Python ingestion scripts
  entity-aware chunking
  pgvector + full-text/entity search

Evals:
  pytest
  JSON/YAML eval cases
  deterministic fixture data
  eval result artifacts

Deployment:
  Railway

17.2 Open Questions

- Exact package managers.
- Whether to use "uv", Poetry, Hatch, or another Python package tool.
- Whether frontend uses npm, pnpm, or yarn.
- Whether to use SQLAlchemy or SQLModel.
- Whether MCP server is separate service or mounted in the backend process.
- Whether object storage is separate or simulated.
- Which exact Kimi model/integration for web chat.

Do not decide these silently if creating specification docs. Record rationale when locking them.

---

18. Pareto v0.1 Scope

18.1 Build This

The 20% of the product that delivers 80% of the impact:

1. Landing page
2. Demo project page
3. Upload/select dataset page
4. Web chat using same tool layer as MCP
5. MCP server with the MVP tool set
6. Direct Perturb-PBMC subset
7. Dataset validation
8. One comparison analysis
9. One plot
10. Small entity-aware RAG corpus
11. Evidence-backed report
12. Tool-call audit trace
13. Eval dashboard
14. AGENTS.md + Makefile + tests
15. Screen recording

18.2 Do Not Build Yet

Explicit non-goals for v0.1:

1. Real auth/account system
2. Arbitrary user datasets beyond the demo schema
3. Full statistical-method autonomy
4. Broad paper scraping pipeline
5. Full autoresearch loop unless visibly useful
6. Multiple complex analysis workflows
7. Production-grade storage/data-retention policy
8. Full Nomic Portal clone
9. Complex LIMS
10. General scientific-paper chatbot

18.3 Critical Demo Features Not to Cut

Do not cut:

Agent/app handoff
Web chat + MCP parity
Tool-call traces
Real public data subset
Small but real RAG
Eval page
Clean repo/harness docs

---

19. Eval Strategy

19.1 Locked Direction

The eval system should be small, visible, and workflow-grounded.

It exists to demonstrate that the system is not just a free-form chatbot.

19.2 Eval Page

The eval page should show:

Eval suite status
Case-level pass/fail
Tool-call trace
Citation check
Numeric check
Unsupported-claim check
Overall score

19.3 First Eval Suite

Initial eval cases should mirror the demo workflow:

1. Create project from user request
2. Return upload URL
3. Validate demo PBMC dataset
4. Infer/define comparison
5. Select supported analysis method
6. Rank proteins correctly from fixture data
7. Retrieve relevant evidence chunks
8. Generate report without unsupported claims

Optional additional cases:

9. Refuse or constrain unsupported arbitrary analysis request
10. Maintain distinction between data-derived, source-derived, and interpretive claims

19.4 Eval Metrics

Candidate metrics:

tool_choice_accuracy
schema_validity
numeric_correctness
citation_support
entity_grounding
unsupported_claim_rate
report_structure_score
trace_completeness

19.5 CI Role

A smoke eval should run in CI.

The full eval suite may run manually or on labeled PRs if model calls are expensive.

Open questions:

- Which evals are deterministic and CI-safe?
- Which evals require model calls?
- How are model calls mocked in CI?
- What score is required for merge?
- Should eval reports be uploaded as artifacts?
- Should eval summaries be posted as PR comments?

---

20. Autoresearch-Style Improvement Loop

20.1 Locked Direction

Autoresearch-style improvement is attractive but should only be included if it visibly improves an eval metric.

Do not include a fake or purely theatrical autoresearch loop.

20.2 Minimal Viable Autoresearch Demo

The useful version:

Before score: 7/10
Agent proposes edit to retrieval_policy.md or tool_selection_policy.yaml
Eval suite reruns
After score: 8/10
Change accepted
Trace visible

Editable targets should be limited to policy/config files:

agent_policies/retrieval_policy.md
agent_policies/tool_selection_policy.yaml
agent_policies/report_style.md

20.3 Acceptance Rule

Accept a proposed policy change only if:

total score improves
unsupported-claim rate does not increase
numeric correctness does not decrease
all safety evals still pass

20.4 Open Question

Include autoresearch in deployed v0.1 only if it can be made visibly useful without distracting from the main demo.

Otherwise, include:

policy files
eval dashboard
documented improvement loop

and defer live autoresearch.

---

21. Development Harness Philosophy

The development harness is central to the project.

The goal is not only to build the demo, but also to show that the demo itself was built with a mature AI-assisted development process.

The harness should communicate:

typed schemas
service boundaries
migrations
testable analysis functions
deterministic eval cases
tool-call audit logs
CI running tests/evals
seeded demo data
storage abstraction
security constraints
structured project state
agent-readable docs
PR-based agent workflow
human-gated merging

The repo should be designed so coding agents can work effectively without guessing architecture.

---

22. Monorepo Layout

22.1 Candidate Layout

Use this as the starting point unless changed explicitly:

.
├── README.md
├── AGENTS.md
├── HANDOFF.md
├── Makefile
├── docker-compose.yml
├── railway.toml
├── .env.example
│
├── docs/
│   ├── PROJECT_BRIEF.md
│   ├── ARCHITECTURE.md
│   ├── DATA_CONTRACTS.md
│   ├── MCP_TOOLS.md
│   ├── TRACE_MODEL.md
│   ├── EVALS.md
│   ├── SECURITY.md
│   ├── ROADMAP.md
│   ├── DEVELOPMENT_WORKFLOW.md
│   └── OPEN_QUESTIONS.md
│
├── apps/
│   └── web/
│
├── services/
│   ├── api/
│   └── mcp/
│
├── packages/
│   ├── analysis/
│   ├── corpus/
│   ├── storage/
│   └── shared-schemas/
│
├── evals/
│   ├── cases/
│   ├── runners/
│   └── results/
│
├── demo_data/
│   ├── raw/
│   ├── processed/
│   └── manifest.json
│
├── agent_policies/
│   ├── retrieval_policy.md
│   ├── tool_selection_policy.yaml
│   └── report_style.md
│
├── scripts/
│   ├── ingest_demo_data.py
│   ├── build_corpus.py
│   ├── seed_demo_project.py
│   ├── run_eval_suite.py
│   └── run_autoresearch_loop.py
│
└── .github/
    ├── workflows/
    ├── ISSUE_TEMPLATE/
    ├── pull_request_template.md
    └── CODEOWNERS

22.2 Open Questions

- Exact package managers.
- Whether "services/mcp" is a standalone deployable service or imports/hosts the API tool registry.
- Whether "packages/shared-schemas" is Python-first or generated into TypeScript.
- Whether the repo uses workspace tooling across Python and Node.
- Whether docker-compose is required immediately.

---

23. Required Repo Docs

Create these docs early.

23.1 "README.md"

Should include:

What this project is
Why it exists
Demo architecture diagram
Quickstart
How to run locally
How to run tests
How to run evals
How to seed demo data
How to connect MCP
Links to key docs

23.2 "AGENTS.md"

This is one of the most important files.

Should include:

Project mission
Architecture overview
Repo layout
Setup commands
Test commands
Eval commands
Stable contracts
Files agents may edit
Files requiring human approval
How to add MCP tools
How to add analysis methods
How to update corpus ingestion
How to update frontend components
How to handle open questions
PR expectations
Definition of done
Do-not-do list

23.3 "docs/PROJECT_BRIEF.md"

Should include:

Product thesis
Target user
Demo flow
Pareto scope
Non-goals
Application-positioning statement

23.4 "docs/ARCHITECTURE.md"

Should include:

System diagram
Services
Shared tool registry
Data flow
Project state model
Storage model
Web chat flow
MCP flow
Eval flow
Deployment model

23.5 "docs/DATA_CONTRACTS.md"

Should include:

Core entities
Relationships
Pydantic/schema definitions or pseudocode
Versioning rules
Stable ID conventions
Artifact references

23.6 "docs/MCP_TOOLS.md"

Should include:

Tool registry architecture
MVP tool list
Deferred tool list
Tool schema style
Per-tool input/output/error schemas
Trace expectations
Permission expectations
Examples

23.7 "docs/TRACE_MODEL.md"

Should include:

Trace types
Web chat full trace
MCP tool trace
Eval trace
Tool call trace schema
Artifact refs
Replay behavior
UI requirements
Retention assumptions

23.8 "docs/EVALS.md"

Should include:

Eval philosophy
First eval suite
Eval case schema
Metrics
Pass/fail criteria
CI role
Eval dashboard behavior
How to add eval cases

23.9 "docs/SECURITY.md"

Should include:

Demo auth assumptions
MCP token behavior
No arbitrary SQL
Tool allowlist
Project-scoped access
No secrets in repo
External model calls
Uploaded data cautions
Known non-production assumptions

23.10 "docs/DEVELOPMENT_WORKFLOW.md"

Should include:

Spec sprint
Implementation waves
Agent issue workflow
Labels
PR governance
Review requirements
CI gates
Human merge policy
Agent activation commands

23.11 "docs/OPEN_QUESTIONS.md"

Should maintain unresolved decisions.

Important instruction:

«Do not silently resolve open questions in implementation PRs. If an implementation requires resolving an open question, label the issue "needs-decision".»

---

24. Makefile Commands

Minimum desired commands:

make setup
make ingest-demo-data
make build-corpus
make seed-demo-project
make test
make eval
make run-local
make railway-check
make demo-reset

Possible later commands:

make lint
make typecheck
make format
make test-backend
make test-frontend
make test-analysis
make eval-smoke
make eval-full
make mcp-inspect
make trace-demo
make clean

Exact commands depend on package manager choices.

---

25. CI / GitHub Actions Harness

25.1 Required Workflows

Create minimal GitHub Actions workflows before broad implementation.

Candidate workflows:

ci.yml
  Runs on pull_request and push to main.
  Includes lint, typecheck, backend tests, frontend build, analysis tests, eval smoke test.

eval.yml
  Runs on workflow_dispatch and optionally PR label/comment.
  Runs eval suite.
  Uploads eval report artifact.
  Optionally comments summary on PR.

agent-review.yml
  Optional.
  Runs AI review on label or comment.

deploy-preview.yml
  Optional.
  Creates preview deploy when ready.

security.yml
  Optional.
  Secret scan or dependency check.

25.2 Required Merge Gates

Branch protection should require:

CI passing
at least one human approval
CODEOWNERS review for protected files
no direct pushes to main

Agents may open PRs and review PRs.
Agents should not merge PRs.

25.3 Model Calls in CI

CI should not depend on paid model calls for core pass/fail unless explicitly configured.

Use:

deterministic fixtures
mock model adapters
eval smoke tests that can run without paid model calls
manual full eval with real model calls

Open question:

- Which evals run with real models and when?

---

26. PR Governance

26.1 Policy

Recommended policy:

Agents may open PRs.
Agents may review PRs.
Agents may respond to review feedback.
Agents may not merge PRs.
Human final merge required.

26.2 Protected Files

Require human approval for changes to:

docs/ARCHITECTURE.md
docs/DATA_CONTRACTS.md
docs/MCP_TOOLS.md
docs/TRACE_MODEL.md
docs/EVALS.md
docs/SECURITY.md
packages/shared-schemas/**
services/api/migrations/**
services/mcp/**
evals/cases/**
.github/workflows/**
CODEOWNERS
AGENTS.md

This list can be refined later.

26.3 PR Template

Create ".github/pull_request_template.md" with:

## Summary

## Linked Issue

## What Changed

## Contracts Changed?
- [ ] No
- [ ] Yes — describe:

## Tests Run
- [ ] Unit tests
- [ ] Typecheck
- [ ] Frontend build
- [ ] Eval smoke
- [ ] Full eval
- [ ] Not applicable — explain:

## Does This Affect MCP Behavior?
- [ ] No
- [ ] Yes — describe:

## Does This Affect Web Chat Traces?
- [ ] No
- [ ] Yes — describe:

## Does This Affect Eval Replay?
- [ ] No
- [ ] Yes — describe:

## Does This Affect Dataset/Corpus Artifacts?
- [ ] No
- [ ] Yes — describe:

## Screenshots / Trace Output

## Known Limitations

## Risk Areas

## Follow-Up Issues

---

27. GitHub Labels

Recommended labels:

agent-ready
agent-codex
agent-claude
needs-decision
contract-change
implementation
spec
test
eval
frontend
backend
mcp
analysis
corpus
infra
docs
blocked
good-first-agent-task
human-review-required

Label semantics:

agent-ready:
  issue has enough context and acceptance criteria for an agent.

needs-decision:
  issue is blocked on unresolved product/architecture decision.

contract-change:
  touches stable schemas, tool contracts, trace models, eval case contracts, or architecture docs.

human-review-required:
  requires careful human review even if CI passes.

good-first-agent-task:
  limited scope, low ambiguity, safe for implementation agent.

agent-codex / agent-claude:
  intended target agent, if assigning by tool.

---

28. Issue Template

Create an implementation issue template:

# Goal

# Background / Context

# Relevant Docs

# Files Likely Involved

# Stable Contracts That Must Not Change

# Implementation Steps

# Acceptance Criteria

# Required Tests

# Required Evals

# UI / Screenshot Requirements

# Trace Requirements

# Out of Scope

# Open Questions / Blockers

Create a spec issue template:

# Specification Goal

# Decisions Already Locked

# Open Questions to Resolve

# Non-Goals

# Required Output Document(s)

# Acceptance Criteria

# Human Review Required

---

29. Multi-Agent Development Plan

29.1 Recommended Flow

Do not start with a swarm of implementation agents.

Use this sequence:

1. Create repo.
2. Add HANDOFF.md.
3. Add docs-only spec sprint issues.
4. Resolve and merge core specs.
5. Add CI and branch protection.
6. Scaffold monorepo.
7. Add shared schemas and tool registry skeleton.
8. Start implementation from small, contract-bound issues.

29.2 Spec Sprint Issues

Create these first:

SPEC-001 Repo constitution and monorepo layout
SPEC-002 Shared data contracts
SPEC-003 Tool registry and MCP/web parity architecture
SPEC-004 Trace and eval replay schema
SPEC-005 MVP MCP tool list and first-pass schemas
SPEC-006 Demo dataset fixture contract
SPEC-007 CI, branch protection, and PR governance
SPEC-008 Agent workflow: labels, issue templates, PR templates

These should be docs-heavy PRs.

29.3 First Implementation Wave After Specs

After the spec sprint is merged:

IMPL-001 Scaffold monorepo
IMPL-002 Add shared schemas package
IMPL-003 Add FastAPI service skeleton
IMPL-004 Add ToolRegistry skeleton
IMPL-005 Add trace logging tables/models
IMPL-006 Add Next.js app shell
IMPL-007 Add seeded demo project script
IMPL-008 Add eval runner skeleton

29.4 Parallelism Rule

Do not run many agents in parallel until:

shared schemas are stable
tool registry contract exists
trace schema exists
CI passes
issue acceptance criteria are clear

Agents can work in parallel on:

frontend shell
backend skeleton
analysis package
corpus package
eval runner
docs

only after contracts are stable.

---

30. Issue Dependency DAG

Recommended build DAG:

0. Handoff + repo setup

1. Repo constitution
2. Shared schemas
3. Tool registry skeleton
4. Trace model
5. Demo dataset fixture contract
6. Corpus fixture contract
7. Analysis method contract
8. API skeleton
9. MCP server skeleton
10. Web app shell
11. Web chat
12. Dashboard
13. Eval runner
14. Eval page
15. Deployment
16. Polish + screen recording

Critical dependency:

Shared schemas + Tool registry + Trace model

Everything else becomes easier after those are stable.

---

31. Definition of Done

31.1 General Implementation PR

A PR is done when:

tests pass
types pass
CI passes
no contract files changed unless issue is contract-change
tool calls are traced if a tool is added/modified
relevant evals updated or explicitly not needed
docs updated if public behavior changed
no secrets committed
no fake data presented as real

31.2 MCP Tool PR

Done when:

input schema defined
output schema defined
error behavior defined
handler implemented
permissions considered
trace logged
tests added
eval case added if user-visible behavior changes
web/API parity checked
docs updated

31.3 UI PR

Done when:

works with seeded demo project
uses real backend data or clearly marked fixture data
shows loading state
shows error state
shows empty state where relevant
screenshot included in PR
no untraced fake tool output

31.4 Analysis PR

Done when:

method documented
assumptions documented
unit tests with fixture data
numeric outputs deterministic
limitations captured in AnalysisPlan or docs
no unsupported biological claims

31.5 RAG/Corpus PR

Done when:

source manifest updated
chunks generated
entity metadata included where possible
retrieval tests added
citation metadata preserved
known gaps documented

31.6 Eval PR

Done when:

eval case schema respected
fixture data included or referenced
expected output criteria defined
pass/fail behavior deterministic where possible
eval result visible in report artifact

---

32. Security and Safety Guardrails

32.1 Locked Guardrail Principles

No arbitrary SQL exposed to agent.
No arbitrary filesystem access from tools.
Tool allowlist.
Project-scoped access.
Structured tool schemas.
Visible tool-call logs.
No fake citations.
No fake data provenance.
External model calls mockable in CI.
Secrets never committed.
Reference data read-only.
Uploaded demo data scoped to demo project.

32.2 MCP-Specific Guardrails

MCP tools should enforce their own guardrails.

Do not rely on the model to self-police.

For example:

run_comparison may only use supported method IDs.
search_corpus may only query indexed corpus.
create_plot may only use supported plot types.
get_trace may only return project-scoped traces.
export_report may only use existing project artifacts.

32.3 Non-Production Assumptions

It is acceptable for v0.1 to state:

This is a demonstration system.
No real account system.
Do not upload sensitive data.
Demo data may be reset.
Data retention is not production-grade.

Do not overpromise privacy or compliance.

---

33. Secrets and Environment Variables

Create ".env.example".

Candidate variables:

DATABASE_URL=
APP_BASE_URL=
MCP_DEMO_TOKEN=

MODEL_PROVIDER=
KIMI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

OBJECT_STORAGE_ENDPOINT=
OBJECT_STORAGE_BUCKET=
OBJECT_STORAGE_ACCESS_KEY=
OBJECT_STORAGE_SECRET_KEY=

RAILWAY_ENVIRONMENT=

Open questions:

- Which model provider variables are actually needed?
- Whether OpenAI/Anthropic keys are used for evals only.
- Whether Kimi is used in v0.1 web chat.
- Whether object storage is required in v0.1.

---

34. Application Package

The final Nomic application supplement should likely include:

App link
GitHub repo link
Screen recording link
Short feature bullets

Potential short application wording later:

I built a small agent-native functional proteomics workbench using public Perturb-PBMC data. It includes a web app, MCP server, shared tool registry, entity-aware RAG over Nomic/nELISA sources, a bounded analysis workflow, evidence-backed report generation, tool-call traces, and a small eval dashboard. The goal was to show how I think about scientist-facing software, biological data pipelines, and agentic tooling for proteomics workflows.

Do not finalize application copy yet.

---

35. Screen Recording Direction

The final screen recording should be a few minutes long.

It can include sped-up sections.

Recommended structure:

0:00–0:30
  Thesis and landing page.

0:30–1:15
  Agent creates project and returns upload/dashboard URL.

1:15–2:00
  User opens upload page and selects direct Perturb-PBMC subset.

2:00–3:00
  Agent validates dataset, runs analysis, retrieves evidence, creates plot/report.

3:00–4:00
  Dashboard shows ranked proteins, plot, donor consistency, evidence, report, trace.

4:00–5:00
  Engineering harness: eval page, repo docs, AGENTS.md, CI/eval command.

The script should not be finalized until the hero biological question and dataset subset are selected.

---

36. UI Design Direction

UI design is a human bottleneck. Avoid spending excessive time hand-designing.

Use:

Next.js
Tailwind
shadcn/ui or similar component system
prebuilt dashboard patterns
Plotly for plots
clean typography
clear cards
visible traces

Pareto UI goal:

Polished enough to look credible.
Not a full custom design system.
One excellent dashboard page is better than many mediocre pages.

Key UI components:

Landing hero
MCP setup card
Demo workspace button
Project status card
Dataset validation card
Analysis summary card
Ranked protein table
Plot card
Evidence cards
Report panel
Tool trace panel
Eval suite panel

---

37. Plotting Direction

Do not build many plot types in v0.1.

One excellent plot is enough.

Candidate plots:

ranked effect-size bar plot
volcano plot
donor-consistency plot

The exact plot depends on the selected subset and statistical method.

Open question:

- Which plot best supports the final hero biological question?

---

38. Reference List for Future Agent

A future agent should read or at least skim the following sources to reload context.

38.1 Nomic / Dataset / Domain

1. Nomic Bio main site
   URL: https://nomic.bio/

2. Nomic Portal page
   URL: https://www.nomic.bio/portal

3. Nomic Perturb-PBMC page
   URL: https://info.nomic.bio/perturb-pbmc

4. nplexbio / nELISA-PBMC GitHub repository
   URL: https://github.com/nplexbio/nELISA-PBMC

5. nELISA Nature Methods paper
   Search/title: “nELISA: A high-throughput, high-plex platform enables quantitative profiling of the inflammatory secretome”

6. Nomic software engineer job description
   Search/title: “Nomic Bio Software Engineer Mid to Sr Levels agentic backends LIMS data pipelines”

38.2 Agent-Native Architecture

1. Every guide: Agent-native Architectures
   URL: https://every.to/guides/agent-native

2. Every article: Agent-native Architectures: How to Build Apps After the End of Code
   URL: https://every.to/chain-of-thought/agent-native-architectures-how-to-build-apps-after-the-end-of-code

3. Every article: How to Build Agent-native: Lessons From Four Apps
   URL: https://every.to/source-code/how-to-build-agent-native-lessons-from-four-apps

4. Builder.io article: Agent-Native: The Next Architecture for Software
   URL: https://www.builder.io/blog/agent-native-architecture

38.3 Harness Engineering / Coding Agents

1. OpenAI article: Harness engineering: leveraging Codex in an agent-first world
   URL: https://openai.com/index/harness-engineering/

2. OpenAI article: Unrolling the Codex agent loop
   Search/title: “OpenAI Unrolling the Codex agent loop”

3. OpenAI Codex GitHub code review documentation
   URL: https://developers.openai.com/codex/integrations/github

4. OpenAI Codex Action repository
   URL: https://github.com/openai/codex-action

5. Claude Code GitHub Actions documentation
   URL: https://code.claude.com/docs/en/github-actions

6. Anthropic Claude Code Action repository
   URL: https://github.com/anthropics/claude-code-action

7. Anthropic: Building Effective AI Agents
   URL: https://www.anthropic.com/research/building-effective-agents

8. Anthropic: Writing tools for agents
   URL: https://www.anthropic.com/engineering/writing-tools-for-agents

38.4 MCP / ChatGPT Apps

1. OpenAI Apps SDK
   URL: https://developers.openai.com/apps-sdk

2. OpenAI Apps SDK Quickstart
   URL: https://developers.openai.com/apps-sdk/quickstart

3. OpenAI Apps SDK examples
   URL: https://github.com/openai/openai-apps-sdk-examples

4. Model Context Protocol documentation
   URL: https://modelcontextprotocol.io/

38.5 GitHub Actions / Repo Governance

1. GitHub Actions events that trigger workflows
   URL: https://docs.github.com/actions/using-workflows/events-that-trigger-workflows

2. GitHub branch protection documentation
   URL: https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches

3. GitHub managing branch protection rules
   URL: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule

4. GitHub CODEOWNERS documentation
   URL: https://docs.github.com/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners

38.6 Optional Background / Research

1. Karpathy autoresearch repository
   URL: https://github.com/karpathy/autoresearch

2. Relevant recent papers on harness engineering, agentic coding, and agent-native systems may be useful, but should not override the concrete project plan.

---

39. Historical Immediate Next Steps

This section records the original bootstrap plan from the planning handoff. It is historical:
the repo scaffolding and v0.1 demo implementation now exist on `main`; use `README.md`,
`AGENTS.md`, and `docs/DEVELOPMENT_WORKFLOW.md` for current operating instructions.

The next Codex/Claude Code session was originally expected to do the following.

Step 1: Create Repo and Add Handoff

Create the GitHub repo and add the initial placeholders:

HANDOFF.md
README.md
AGENTS.md
docs/OPEN_QUESTIONS.md

Application code was intentionally deferred during this bootstrap step.

Step 2: Add Spec Sprint Issues

Create the eight spec issues:

SPEC-001 Repo constitution and monorepo layout
SPEC-002 Shared data contracts
SPEC-003 Tool registry and MCP/web parity architecture
SPEC-004 Trace and eval replay schema
SPEC-005 MVP MCP tool list and first-pass schemas
SPEC-006 Demo dataset fixture contract
SPEC-007 CI, branch protection, and PR governance
SPEC-008 Agent workflow: labels, issue templates, PR templates

Step 3: Draft Docs Through PRs

For each spec issue, open a docs PR.

Do not merge broad implementation before the docs are stable.

Step 4: Add CI Harness

Add initial GitHub Actions:

ci.yml
eval.yml placeholder or smoke eval

Also add:

PR template
Issue templates
CODEOWNERS
labels if possible
branch protection instructions

Step 5: Scaffold Monorepo

After specs and CI:

apps/web
services/api
services/mcp
packages/analysis
packages/corpus
packages/storage
packages/shared-schemas
evals
scripts

Step 6: Begin Implementation Issues

Only after the above:

IMPL-001 Scaffold monorepo
IMPL-002 Add shared schemas package
IMPL-003 Add FastAPI service skeleton
IMPL-004 Add ToolRegistry skeleton
IMPL-005 Add trace logging models
IMPL-006 Add Next.js app shell
IMPL-007 Add seeded demo project script
IMPL-008 Add eval runner skeleton

---

40. Open Questions Summary

These must remain open until explicitly resolved.

Product / User Story

Final primary persona:
  Nomic internal scientist vs field application scientist vs customer translational scientist.

Final hero biological question:
  not selected.

Final screen recording script:
  deferred until data subset and hero question are chosen.

Data

Exact Perturb-PBMC subset.
Exact stimulation context.
Exact perturbagen/control comparison.
Exact protein panel.
Data format and preprocessing state.
Direct subset vs transformed direct subset.

Statistics

Exact method menu.
Normalization assumptions.
Donor-consistency metric.
Paired vs unpaired comparison.
Whether p-values are central to v0.1.
Multiple-testing method.
Best-practice source list.

RAG / Corpus

Exact source list.
Entity extraction method.
Whether external biology references are included.
Whether figure captions/supplements are included.
Corpus chunking parameters.
Retrieval eval design.

Architecture

Exact package managers.
SQLAlchemy vs SQLModel.
Python MCP server process layout.
Storage backend.
Object storage choice.
Schema generation approach.
Kimi integration details.

Evals

Exact eval case schema.
Which evals run in CI.
Which evals require real model calls.
What score threshold gates merges.
How eval reports are displayed.

Autoresearch

Include live autoresearch only if it visibly improves a metric.
Otherwise defer live loop and document policy/eval scaffolding.

---

41. Things Future Agents Must Not Do

Do not:

Do not build a generic chatbot.
Do not build a generic omics platform.
Do not build real auth unless explicitly requested.
Do not silently invent the hero biological question.
Do not silently choose statistical methods without documenting assumptions.
Do not fake data provenance.
Do not fake citations.
Do not fake tool traces.
Do not expose arbitrary SQL.
Do not create broad tools that bypass the trace system.
Do not duplicate tool logic separately in MCP and web chat.
Do not merge agent PRs without human approval.
Do not change contract files in implementation PRs unless labeled contract-change.
Do not overbuild paper scraping before the core demo works.
Do not overbuild plots before one excellent plot works.
Do not optimize for traditional line-of-code effort; optimize for minimizing human specification/review bottlenecks.

---

42. Things Future Agents Should Prioritize

Prioritize:

Narrow polished vertical slice.
Shared tool registry.
Stable schemas.
Traceability.
Eval visibility.
Real public data subset.
Entity-aware RAG.
Agent/app handoff.
Web chat + MCP parity.
Clean repo docs.
CI and PR governance.
Human-readable project state.

---

43. Final Locked Direction

The locked direction is:

«Build a Railway-hosted, agent-native functional proteomics workbench using a direct subset of public Nomic Perturb-PBMC data and a small entity-aware Nomic/nELISA corpus. The v0.1 demo should show a web app and MCP server operating over shared project state. A user should be able to create a project through an agent, receive an upload/dashboard URL, validate/select the demo dataset, run one bounded analysis, retrieve evidence, generate a plot and report, and inspect tool/eval traces. The repo itself should demonstrate modern AI-assisted software engineering through a monorepo, shared schemas, a tool registry, CI/eval harness, agent-readable docs, issue templates, PR templates, CODEOWNERS, and human-gated multi-agent development.»

The next step is not broad implementation.

The next step is:

«Create the repo, add this handoff, run the spec sprint, build the CI/governance harness, then create implementation issues for agent-driven PR work.»
