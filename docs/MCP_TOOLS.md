# MCP Tools

> **Protected / contract file.** Changes require a PR labeled `contract-change`.
> SPEC-005. The MVP tool list is **frozen** (HANDOFF §15.2) unless explicitly changed.

## Tool registry architecture

There is exactly **one** `ToolRegistry`, imported by the FastAPI backend, the MCP server
(mounted in the same process — see `docs/ARCHITECTURE.md`), the web chat, and the eval
runner. Tool *logic is never duplicated* across surfaces. Each tool is a `ToolDefinition`:

```python
class ToolDefinition(BaseModel):
    name: str
    description: str
    input_model: type[BaseModel]   # Pydantic — also the JSON Schema exposed over MCP
    output_model: type[BaseModel]
    error_codes: list[str]
    permissions: "ToolPermissions"
    trace: "TracePolicy"           # always traced; this tunes redaction/verbosity
    eval_tags: list[str] = []
    handler: Callable              # (input, ctx) -> output ; ctx carries project + storage + trace sink

class ToolPermissions(BaseModel):
    scope: Literal["project", "global"]
    mutates_state: bool
    reads_corpus: bool = False
    external_model_call: bool = False

class TracePolicy(BaseModel):
    redact_input_keys: list[str] = []
    redact_output_keys: list[str] = []
```

Invoking any tool through the registry **always** opens a `ToolCallTrace` (see
`docs/TRACE_MODEL.md`), validates input against `input_model`, runs the handler, validates
output against `output_model`, and closes the trace. A handler that raises returns a
structured `TraceError` with one of its declared `error_codes`.

## Result envelope

Where useful, tool outputs include resolvable URLs and suggested next actions (HANDOFF
§15.5), so an agent can drive the handoff:

```python
class ToolResult(BaseModel):
    # tool-specific fields...
    next_actions: list[str] = []   # tool names the agent may call next
```

## Standard error codes
`invalid_input` · `not_found` · `unsupported_method` · `unsupported_plot` ·
`dataset_not_validated` · `corpus_unindexed` · `out_of_scope` · `internal_error`.

## MVP tool list (FROZEN — HANDOFF §15.2)

UI action ↔ tool parity (HANDOFF §12.1) is mandatory: every tool below has a corresponding
web-app action and vice-versa.

| Tool | Scope / mutates | First-pass input → output |
|---|---|---|
| `create_project` | project / yes | `{title}` → `{project_id, status, upload_url, dashboard_url, next_actions}` |
| `get_project_status` | project / no | `{project_id}` → `Project` + summary counts |
| `create_upload_url` | project / yes | `{project_id}` → `{upload_url, expires_at}` |
| `validate_dataset` | project / yes | `{project_id, dataset_id}` → `DatasetValidation` |
| `inspect_dataset_schema` | project / no | `{project_id, dataset_id}` → `DatasetSchemaProfile` |
| `define_comparison` | project / yes | `{project_id, dataset_id, comparison: ComparisonSpec}` → `AnalysisPlan` (draft) |
| `run_comparison` | project / yes | `{project_id, plan_id}` → `AnalysisResult` |
| `rank_proteins` | project / no | `{project_id, result_id, metric?}` → `ProteinRanking` |
| `create_plot` | project / yes | `{project_id, result_id, plot_type}` → `PlotArtifact` |
| `search_corpus` | project / no, reads corpus | `{query, entities?, k?}` → `list[EvidenceChunk]` (scored) |
| `attach_evidence` | project / yes | `{project_id, chunk_ids, supports_report_id?}` → `EvidenceAttachment` |
| `export_report` | project / yes | `{project_id, result_id, attachment_ids?}` → `ReportArtifact` |
| `run_eval_suite` | global / no, external_model_call? | `{suite?}` → `EvalRun` summary |
| `get_trace` | project / no | `{project_id, kind?}` → ordered `list[ToolCallTrace]` (project-scoped only) |

### Guardrails (enforced by the tool, not the model — HANDOFF §32.2)
- `run_comparison` accepts **only** supported `method_id`s. v0.1 candidate menu (final menu
  pending **STAT-001**): `effect_size_summary`, `donor_aware_paired_difference`,
  `simple_group_test`, `multiple_testing_correction`, `donor_consistency_score`.
- `create_plot` accepts only `plot_type ∈ {ranked_effect_bar, volcano, donor_consistency}`.
- `search_corpus` queries only the indexed corpus; never the open web.
- `get_trace` returns only traces for the requested project.
- `export_report` references only existing project artifacts; emits claim-typed output and
  fails if a `source-derived` claim lacks evidence.

## Deferred tools (HANDOFF §15.3)
`list_project_files`, `preview_dataset`, `profile_dataset`, `infer_experimental_design`,
`select_samples`, `retrieve_analysis_best_practices`, `propose_analysis_plan`,
`validate_analysis_plan`, `list_supported_methods`, `read_source_chunk`,
`write_project_note`, `run_eval_case`, `get_eval_results`, `run_autoresearch_loop`.
Promote a deferred tool only with explicit rationale in the PR.

## Auth (demo)
MCP uses a demo bearer token (`MCP_DEMO_TOKEN`). Scope/lifetime details in
`docs/SECURITY.md`. Exact MCP client config is an open question (HANDOFF §14).
