# Data Contracts

> **Protected / contract file.** Changes require a PR labeled `contract-change`.
> SPEC-002. Source of truth: Pydantic/SQLModel in `packages/shared-schemas`; TypeScript
> types are generated from these (never hand-edited).

## Conventions

### Stable IDs
String IDs with a type prefix + a ULID (lexicographically sortable, time-ordered):
`<prefix>_<ULID>`, e.g. `proj_01J9Z3...`.

| Entity | Prefix |
|---|---|
| Project | `proj_` |
| Dataset | `ds_` |
| DatasetSchemaProfile | `sp_` |
| AnalysisPlan | `plan_` |
| AnalysisResult | `res_` |
| PlotArtifact | `plot_` |
| EvidenceSource | `src_` |
| EvidenceChunk | `chunk_` |
| EvidenceAttachment | `evd_` |
| ReportArtifact | `rep_` |
| ToolCallTrace | `tc_` |

For the demo, the single seeded project uses a stable readable id: `proj_demo`.

### Versioning
- `packages/shared-schemas` is semver'd. Additive optional fields → minor; renames/removals/
  type changes → major + a migration note in the PR.
- Every persisted top-level record carries `schema_version: str` (the shared-schemas version
  that wrote it) so old artifacts remain interpretable.
- Timestamps are UTC ISO-8601 (`created_at`, `updated_at`).

### Artifact references
File-like artifacts (CSV/parquet/plot/report) are **not** inlined. They are referenced by an
`ArtifactRef` resolved through the storage adapter (see `docs/ARCHITECTURE.md` → Storage).

```python
class ArtifactRef(BaseModel):
    uri: str            # storage-adapter URI, e.g. "project://proj_demo/datasets/normalized_long.parquet"
    media_type: str     # "text/csv" | "application/parquet" | "application/json" | "text/markdown" | "image/png"
    bytes: int | None = None
    sha256: str | None = None
```

The storage adapter maps `project://` URIs onto the file-like project tree (HANDOFF §12.5),
backed by local FS (dev) / Railway volume (deploy). Structured state lives in Postgres.

## v0.1 core entities

> Trimmed to what the hero workflow touches. Chat entities are specified in
> `docs/TRACE_MODEL.md`; eval entities in `docs/EVALS.md`. Deferred (HANDOFF §16.2):
> standalone `entities` table — entity tags are embedded on chunks for v0.1.

### Project — the unit of state
```python
class Project(BaseModel):
    id: str                       # proj_*
    schema_version: str
    title: str
    status: Literal["created", "dataset_pending", "validated", "analyzed", "reported"]
    context_md: str | None = None # free-form project context ("context.md")
    created_at: datetime
    updated_at: datetime
```
Relationships: a Project **has many** Datasets, AnalysisPlans, AnalysisResults,
EvidenceAttachments, ReportArtifacts, ToolCallTraces (and ChatSessions / EvalRuns, defined
elsewhere).

### Dataset
```python
class Dataset(BaseModel):
    id: str                       # ds_*
    project_id: str
    schema_version: str
    name: str
    source: Literal["uploaded", "selected_public"]   # public = direct Perturb-PBMC subset
    raw_ref: ArtifactRef                              # original CSV/parquet
    normalized_ref: ArtifactRef | None = None         # processed long/wide parquet
    validation: "DatasetValidation"
    created_at: datetime
```

```python
class DatasetValidation(BaseModel):
    status: Literal["pending", "passed", "failed"]
    row_count: int | None = None
    issues: list["ValidationIssue"] = []

class ValidationIssue(BaseModel):
    severity: Literal["error", "warning"]
    code: str
    message: str
    column: str | None = None
```

### DatasetSchemaProfile
```python
class DatasetSchemaProfile(BaseModel):
    id: str                       # sp_*
    schema_version: str
    dataset_id: str
    layout: Literal["long", "wide"]
    columns: list["ColumnProfile"]
    detected_axes: "ExperimentAxes"   # which columns are donor / stimulation / perturbagen / protein / value

class ColumnProfile(BaseModel):
    name: str
    dtype: Literal["string", "float", "int", "categorical"]
    role: Literal["donor", "stimulation", "perturbagen", "protein", "value", "metadata", "unknown"]
    n_unique: int | None = None
    examples: list[str] = []

class ExperimentAxes(BaseModel):
    donor: str | None
    stimulation: str | None
    perturbagen: str | None
    protein: str | None
    value: str | None
```

### AnalysisPlan  (HANDOFF §8.4 — the auditable "why")
```python
class AnalysisPlan(BaseModel):
    id: str                       # plan_*
    schema_version: str
    project_id: str
    dataset_id: str
    method_id: str                # must be a supported method (see docs/MCP_TOOLS.md → run_comparison)
    comparison: "ComparisonSpec"
    rationale: str                # why this method was selected
    assumptions: list[str]
    donor_handling: str
    replicate_handling: str | None = None
    multiple_testing: str | None = None
    limitations: list[str]
    unsupported_assumptions: list[str] = []
    created_at: datetime

class ComparisonSpec(BaseModel):
    group_a: dict[str, str]       # e.g. {"perturbagen": "IFNG"}
    group_b: dict[str, str]       # e.g. {"perturbagen": "control"}
    stimulation_context: str | None = None
    paired_by: str | None = None  # e.g. "donor"
    proteins: list[str] | None = None   # None = all in subset
```

### AnalysisResult + ProteinRanking
```python
class AnalysisResult(BaseModel):
    id: str                       # res_*
    schema_version: str
    project_id: str
    plan_id: str
    method_id: str
    ranking: "ProteinRanking"
    donor_consistency: list["DonorConsistencyRow"] = []
    plot_id: str | None = None    # -> PlotArtifact
    table_ref: ArtifactRef        # full differential results (CSV/parquet)
    created_at: datetime

class ProteinRanking(BaseModel):
    rows: list["RankedProtein"]   # ordered, strongest first
    metric: str                   # "effect_size" | "log2_fold_change" | ...
    correction: str | None = None

class RankedProtein(BaseModel):
    protein: str
    effect_size: float
    direction: Literal["up", "down"]
    p_value: float | None = None
    q_value: float | None = None
    donor_consistency: float | None = None

class DonorConsistencyRow(BaseModel):
    donor: str
    agrees_with_consensus: bool
    note: str | None = None
```

### PlotArtifact
```python
class PlotArtifact(BaseModel):
    id: str                       # plot_*
    schema_version: str
    project_id: str
    result_id: str
    plot_type: Literal["ranked_effect_bar", "volcano", "donor_consistency"]
    spec_ref: ArtifactRef         # Plotly JSON spec
    image_ref: ArtifactRef | None = None  # rendered PNG (optional)
    created_at: datetime
```

### Evidence (corpus side)
```python
class EvidenceSource(BaseModel):
    id: str                       # src_*
    schema_version: str
    title: str
    source_type: Literal["paper", "docs", "github", "webpage", "supplement"]
    url: str | None = None
    doi: str | None = None
    license_note: str | None = None

class EvidenceChunk(BaseModel):
    id: str                       # chunk_*
    schema_version: str
    source_id: str
    text: str
    section: str | None = None
    entities: list[str] = []      # ["IL6","CXCL10","LPS","IFNG","PBMC"]
    assay_context: list[str] = [] # ["nELISA","secretome","perturbation"]
    citation: "Citation"
    embedding_status: Literal["pending", "embedded"] = "pending"

class Citation(BaseModel):
    url: str | None = None
    doi: str | None = None
    paper_title: str | None = None
    authors: str | None = None
    year: str | None = None

class EvidenceAttachment(BaseModel):
    id: str                       # evd_*
    schema_version: str
    project_id: str
    chunk_ids: list[str]
    supports_report_id: str | None = None
    note: str | None = None
```

### ReportArtifact  (claim-typed — HANDOFF §9.5)
```python
class ReportArtifact(BaseModel):
    id: str                       # rep_*
    schema_version: str
    project_id: str
    markdown_ref: ArtifactRef
    claims: list["Claim"]
    created_at: datetime

class Claim(BaseModel):
    text: str
    kind: Literal["data-derived", "source-derived", "interpretive", "limitation"]
    evidence_chunk_ids: list[str] = []   # REQUIRED non-empty when kind == "source-derived"
```

### ToolCallTrace
Defined fully in `docs/TRACE_MODEL.md` (it is the spine of both the MCP and web surfaces).
Every entity above that is *created or mutated by a tool* is produced inside a traced tool
call; the trace references the affected `project_id` and any resulting artifact refs.

## Invariants (enforced in code, not by the model)
- A `source-derived` Claim MUST reference ≥1 `EvidenceChunk`.
- An `AnalysisResult.method_id` MUST be a supported method id.
- An `AnalysisPlan` MUST exist before its `AnalysisResult`.
- All artifact bytes are reached via `ArtifactRef` + the storage adapter — never raw paths
  from a tool argument.
