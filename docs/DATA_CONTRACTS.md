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

## Demo dataset fixture contract (SPEC-006)

The single seeded demo fixture that dataset validation, analysis, reporting, and evals all run
against. Decided after DATA-001 selected the hero comparison (`docs/DEMO_DECISIONS.md`); this
section is the frozen description of that fixture. Changes require `contract-change`.

### Source & license
- **Repo:** `https://github.com/nplexbio/nELISA-PBMC`
- **File:** `figure 4/data_pgmc_umap.h5ad` (AnnData; 7,376 samples × 191 proteins, 35 obs cols).
- **License:** data is **CC BY-NC 4.0**; code Apache-2.0. Non-commercial demo use only.
- **Required citation:** Dagher, M., Ongo, G., Robichaud, N. et al. *nELISA: a high-throughput,
  high-plex platform enables quantitative profiling of the inflammatory secretome.* Nat Methods
  (2025). DOI `10.1038/s41592-025-02861-6`.

### Hero comparison encoded by the fixture
IL-10 vs matched no-cytokine control, under LPS stimulation (DATA-001 Candidate 1):
- `stimulation = "LPS"`, `stimulus_concentration_ng_ml = 2000.0` (all rows)
- `perturbagen ∈ {"IL-10", "control"}`; `cytokine_concentration_ng_ml = 50.0` for IL-10, `0.0`
  for control
- all 6 donors; design observed in DATA-001: ~1 IL-10 sample/donor + ~18 matched controls/donor

### Layout & columns (long format)
One row per `(sample, protein)`. `DatasetSchemaProfile.layout = "long"`.

| column | dtype | units / allowed values | role |
|---|---|---|---|
| `sample_id` | string | stable id mapping back to the source H5AD obs row | metadata |
| `donor` | categorical | `donor_1` … `donor_6` (exactly 6) | donor |
| `stimulation` | categorical | `"LPS"` (only value in fixture) | stimulation |
| `stimulus_concentration_ng_ml` | float | `2000.0` | metadata |
| `perturbagen` | categorical | `"IL-10"` \| `"control"` (both present) | perturbagen |
| `cytokine_concentration_ng_ml` | float | `50.0` (IL-10) \| `0.0` (control) | metadata |
| `protein` | categorical | one of the curated panel (below) | protein |
| `response_value` | float | normalized response, finite (no NaN/inf) | value |

`value_type = "normalized_response"` — the public H5AD's normalized value, carried **verbatim**.
v0.1 does **not** renormalize and does **not** synthesize pg/mL or fold-change; the analysis
package derives donor-matched effect sizes from `response_value` (see STAT-001 / `run_comparison`).

### Curated protein panel (v0.1)
~21 inflammatory cytokines/chemokines, centered on the DATA-001 IL-10/LPS signal:
`TNF alpha, IL-1 beta, IL-1 alpha, IL-6, IL-12 p40, IFN gamma, CCL1, CCL2, CCL22, CCL24,
CCL5, CCL7, CCL8, CXCL1, CXCL10, CXCL16, G-CSF, GM-CSF, IL-1 RA RN, TNF RII, MMP-1`. The exact
panel (canonical protein names matching the source object) is frozen in `provenance.json`
(`selection.proteins`) when the fixture is generated.

### Allowed transforms (direct subset only)
Permitted, and the **only** permitted operations: row filter to the selection above;
wide→long melt; column rename to the contract names; donor integer → `donor_N` label mapping.
**Not** permitted: value recomputation, renormalization, imputation, outlier removal, or any
synthetic/augmented rows. The fixture is an honest direct subset.

### Provenance recording
The fixture ships with a sidecar `provenance.json` next to the data artifacts:
```python
class DatasetProvenance(BaseModel):
    source_repo: str                 # github URL
    source_commit: str               # pinned commit SHA of the public repo
    source_file: str                 # "figure 4/data_pgmc_umap.h5ad"
    source_file_sha256: str          # hash of the exact source object pulled
    source_value_field: str          # which AnnData field/layer response_value came from
    license: str                     # "CC BY-NC 4.0 (data)"
    citation: Citation               # reuses the Citation model (DOI/title/authors/year)
    value_type: Literal["normalized_response"]
    normalization_note: str          # "verbatim public H5AD normalized value; not renormalized"
    selection: dict                  # donors, stimulation, concentrations, perturbagens, proteins
    transforms_applied: list[str]    # the allowed transforms actually run
    row_count: int
    donor_counts: dict[str, int]     # rows per donor, for the matched-design check
    generated_by: str                # extraction script path + version
    extracted_at: datetime
```

### Storage refs (seeded `proj_demo`)
- `raw_ref`: `project://proj_demo/datasets/raw/nelisa_pbmc_il10_lps_subset.csv` (as-extracted long CSV)
- `normalized_ref`: `project://proj_demo/datasets/normalized/nelisa_pbmc_il10_lps_long.parquet`
- provenance: `project://proj_demo/datasets/raw/provenance.json`

(`source = "selected_public"`.) "normalized" here means the canonical long/typed parquet — the
values are already normalized in the source; no further normalization is applied.

### Validation the validator MUST assert (→ `DatasetValidation.status = "passed"`)
1. all required columns present with the dtypes above;
2. `donor` set == `{donor_1..donor_6}` (exactly 6 donors);
3. `stimulation == "LPS"` and `stimulus_concentration_ng_ml == 2000.0` for every row;
4. `perturbagen ⊆ {"IL-10","control"}` with **both** present;
5. `cytokine_concentration_ng_ml == 50.0` where IL-10 else `0.0`;
6. every `protein` is in the frozen panel, and all panel proteins are present;
7. `response_value` finite — no NaN/inf/nulls;
8. matched design: each donor has ≥1 IL-10 sample **and** ≥1 control sample;
9. rectangular: `row_count == n_samples × n_proteins`.

### Validation failures the fixture suite MUST exercise
Ship tiny deliberately-broken variants so the validator's failure paths are tested. Each maps to
a `ValidationIssue.code`:

| variant | injected defect | `code` | severity |
|---|---|---|---|
| `missing_column` | drop `perturbagen` | `SCHEMA_MISSING_COLUMN` | error |
| `unknown_protein` | a `protein` outside the panel | `PROTEIN_NOT_IN_PANEL` | error |
| `nan_value` | a NaN in `response_value` | `NULL_VALUE` | error |
| `wrong_stimulation` | a row with `stimulation != "LPS"` | `UNEXPECTED_CATEGORY` | error |
| `unbalanced_design` | a donor missing its IL-10 sample | `MISSING_GROUP_FOR_DONOR` | error |

These `code` values are the v0.1 vocabulary; additions require `contract-change`.

### Reproducibility
Generation is deterministic given the pinned `source_commit`: same input → byte-identical
fixture (stable row order: sort by `donor`, `perturbagen`, `sample_id`, `protein`). The extraction
script (ingestion lands in IMPL-007 #22, not here) records `source_file_sha256` and fails closed
if the pinned source hash changes.

## Invariants (enforced in code, not by the model)
- A `source-derived` Claim MUST reference ≥1 `EvidenceChunk`.
- An `AnalysisResult.method_id` MUST be a supported method id.
- An `AnalysisPlan` MUST exist before its `AnalysisResult`.
- All artifact bytes are reached via `ArtifactRef` + the storage adapter — never raw paths
  from a tool argument.
- A `source="selected_public"` Dataset MUST ship a `provenance.json` recording at least
  `source_repo`, `source_commit`, and `source_file_sha256` (SPEC-006).
- The demo fixture MUST be a direct subset: only the allowed transforms (row filter, melt,
  rename, donor relabel) — no value recomputation, imputation, or synthetic rows (SPEC-006).
