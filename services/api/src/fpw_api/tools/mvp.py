"""MVP tool definitions registered by the shared registry skeleton."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from functional_proteomics_analysis import (
    DEFAULT_METHOD_ID,
    AnalysisValidationError,
    ComparisonRequest,
    build_default_analysis_plan,
    load_long_csv,
    run_donor_aware_paired_difference,
)
from pydantic import BaseModel, ConfigDict, Field
from shared_schemas import EntityPrefix, new_id

from fpw_api.tools.registry import (
    ToolContext,
    ToolDefinition,
    ToolExecutionError,
    ToolHandler,
    ToolPermissions,
    ToolRegistry,
    TracePolicy,
)

SCHEMA_VERSION = "0.1.0"
DEMO_PROJECT_ID = "proj_demo"
DEMO_DATASET_ID = "ds_01KCYAG0000000000000000000"
DEMO_FIXTURE_RELATIVE = Path("demo_data/raw/nelisa_pbmc_il10_lps_subset.csv")

STANDARD_ERROR_CODES = [
    "invalid_input",
    "not_found",
    "unsupported_method",
    "unsupported_plot",
    "dataset_not_validated",
    "corpus_unindexed",
    "out_of_scope",
    "internal_error",
]


class ToolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectInput(ToolModel):
    project_id: str


class CreateProjectInput(ToolModel):
    title: str = Field(min_length=1)


class CreateProjectOutput(ToolModel):
    project_id: str
    status: Literal["created"]
    upload_url: str
    dashboard_url: str
    next_actions: list[str] = Field(default_factory=list)


class ProjectStatusOutput(ToolModel):
    project: dict[str, Any]
    summary_counts: dict[str, int] = Field(default_factory=dict)


class CreateUploadUrlOutput(ToolModel):
    upload_url: str
    expires_at: str


class ValidateDatasetInput(ProjectInput):
    dataset_id: str


class DatasetValidationOutput(ToolModel):
    status: Literal["pending", "passed", "failed"]
    row_count: int | None = Field(default=None, ge=0)
    issues: list[dict[str, Any]] = Field(default_factory=list)


class DatasetSchemaOutput(ToolModel):
    id: str
    schema_version: str
    dataset_id: str
    layout: Literal["long", "wide"]
    columns: list[dict[str, Any]]
    detected_axes: dict[str, Any]


class DefineComparisonInput(ValidateDatasetInput):
    comparison: dict[str, Any]


class AnalysisPlanOutput(ToolModel):
    id: str
    schema_version: str
    project_id: str
    dataset_id: str
    method_id: str
    comparison: dict[str, Any]
    rationale: str
    assumptions: list[str]
    donor_handling: str
    replicate_handling: str | None = None
    multiple_testing: str | None = None
    limitations: list[str]
    unsupported_assumptions: list[str] = Field(default_factory=list)
    created_at: str


class RunComparisonInput(ProjectInput):
    plan_id: str


class AnalysisResultOutput(ToolModel):
    id: str
    schema_version: str
    project_id: str
    plan_id: str
    method_id: str
    ranking: dict[str, Any]
    donor_consistency: list[dict[str, Any]] = Field(default_factory=list)
    table_ref: dict[str, Any]
    donor_handling: str
    replicate_handling: str | None = None
    multiple_testing: str | None = None
    limitations: list[str]
    created_at: str


class RankProteinsInput(ProjectInput):
    result_id: str
    metric: str | None = None


class ProteinRankingOutput(ToolModel):
    rows: list[dict[str, Any]]
    metric: str
    correction: str | None = None


_PLANS: dict[str, dict[str, Any]] = {}
_RESULTS: dict[str, dict[str, Any]] = {}


class CreatePlotInput(ProjectInput):
    result_id: str
    plot_type: Literal["ranked_effect_bar", "volcano", "donor_consistency"]


class PlotArtifactOutput(ToolModel):
    id: str
    schema_version: str
    project_id: str
    result_id: str
    plot_type: Literal["ranked_effect_bar", "volcano", "donor_consistency"]
    spec_ref: dict[str, Any]
    image_ref: dict[str, Any] | None = None


class SearchCorpusInput(ToolModel):
    query: str = Field(min_length=1)
    entities: list[str] | None = None
    k: int | None = Field(default=None, ge=1)


class EvidenceChunkListOutput(ToolModel):
    chunks: list[dict[str, Any]]


class AttachEvidenceInput(ProjectInput):
    chunk_ids: list[str]
    supports_report_id: str | None = None


class EvidenceAttachmentOutput(ToolModel):
    id: str
    schema_version: str
    project_id: str
    chunk_ids: list[str]
    supports_report_id: str | None = None
    note: str | None = None


class ExportReportInput(ProjectInput):
    result_id: str
    attachment_ids: list[str] | None = None


class ReportArtifactOutput(ToolModel):
    id: str
    schema_version: str
    project_id: str
    markdown_ref: dict[str, Any]
    claims: list[dict[str, Any]]


class RunEvalSuiteInput(ToolModel):
    suite: str | None = None


class EvalRunOutput(ToolModel):
    suite: str | None = None
    status: Literal["stubbed"]
    trace_step_ids: list[str] = Field(default_factory=list)


class GetTraceInput(ProjectInput):
    kind: str | None = None


class GetTraceOutput(ToolModel):
    traces: list[dict[str, Any]]


def create_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for definition in mvp_tool_definitions():
        registry.register(definition)
    return registry


def mvp_tool_definitions() -> list[ToolDefinition]:
    return [
        _tool(
            "create_project",
            "Create a project workspace.",
            CreateProjectInput,
            CreateProjectOutput,
            scope="project",
            mutates_state=True,
            eval_tags=["project"],
        ),
        _tool(
            "get_project_status",
            "Return project status and summary counts.",
            ProjectInput,
            ProjectStatusOutput,
            scope="project",
            mutates_state=False,
        ),
        _tool(
            "create_upload_url",
            "Create an upload URL for a project dataset.",
            ProjectInput,
            CreateUploadUrlOutput,
            scope="project",
            mutates_state=True,
        ),
        _tool(
            "validate_dataset",
            "Validate a project dataset.",
            ValidateDatasetInput,
            DatasetValidationOutput,
            scope="project",
            mutates_state=True,
        ),
        _tool(
            "inspect_dataset_schema",
            "Inspect dataset shape and detected experiment axes.",
            ValidateDatasetInput,
            DatasetSchemaOutput,
            scope="project",
            mutates_state=False,
        ),
        _tool(
            "define_comparison",
            "Create a draft analysis plan for a comparison.",
            DefineComparisonInput,
            AnalysisPlanOutput,
            scope="project",
            mutates_state=True,
            handler=_define_comparison_handler,
        ),
        _tool(
            "run_comparison",
            "Run a supported analysis plan.",
            RunComparisonInput,
            AnalysisResultOutput,
            scope="project",
            mutates_state=True,
            handler=_run_comparison_handler,
        ),
        _tool(
            "rank_proteins",
            "Rank proteins from an analysis result.",
            RankProteinsInput,
            ProteinRankingOutput,
            scope="project",
            mutates_state=False,
            handler=_rank_proteins_handler,
        ),
        _tool(
            "create_plot",
            "Create a supported plot artifact.",
            CreatePlotInput,
            PlotArtifactOutput,
            scope="project",
            mutates_state=True,
            error_codes=["invalid_input", "unsupported_plot", "out_of_scope", "internal_error"],
        ),
        _tool(
            "search_corpus",
            "Search the indexed project corpus.",
            SearchCorpusInput,
            EvidenceChunkListOutput,
            scope="project",
            mutates_state=False,
            reads_corpus=True,
            error_codes=["invalid_input", "corpus_unindexed", "out_of_scope", "internal_error"],
        ),
        _tool(
            "attach_evidence",
            "Attach evidence chunks to project work.",
            AttachEvidenceInput,
            EvidenceAttachmentOutput,
            scope="project",
            mutates_state=True,
        ),
        _tool(
            "export_report",
            "Export a claim-typed report artifact.",
            ExportReportInput,
            ReportArtifactOutput,
            scope="project",
            mutates_state=True,
        ),
        _tool(
            "run_eval_suite",
            "Run a deterministic eval suite.",
            RunEvalSuiteInput,
            EvalRunOutput,
            scope="global",
            mutates_state=False,
            eval_tags=["eval"],
        ),
        _tool(
            "get_trace",
            "Return project-scoped tool traces.",
            GetTraceInput,
            GetTraceOutput,
            scope="project",
            mutates_state=False,
        ),
    ]


def _tool(
    name: str,
    description: str,
    input_model: type[BaseModel],
    output_model: type[BaseModel],
    *,
    scope: Literal["project", "global"],
    mutates_state: bool,
    reads_corpus: bool = False,
    external_model_call: bool = False,
    error_codes: list[str] | None = None,
    eval_tags: list[str] | None = None,
    handler: ToolHandler | None = None,
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=description,
        input_model=input_model,
        output_model=output_model,
        error_codes=error_codes or STANDARD_ERROR_CODES,
        permissions=ToolPermissions(
            scope=scope,
            mutates_state=mutates_state,
            reads_corpus=reads_corpus,
            external_model_call=external_model_call,
        ),
        trace=TracePolicy(),
        eval_tags=eval_tags or [],
        handler=handler or _stub_handler(name),
    )


def _stub_handler(name: str) -> ToolHandler:
    def handler(_tool_input: BaseModel, _context: ToolContext) -> BaseModel:
        raise ToolExecutionError(
            "out_of_scope",
            f"{name} is registered but not implemented in the ToolRegistry skeleton.",
        )

    return handler


def _define_comparison_handler(tool_input: BaseModel, _context: ToolContext) -> AnalysisPlanOutput:
    typed_input = DefineComparisonInput.model_validate(tool_input)
    if typed_input.dataset_id != DEMO_DATASET_ID:
        raise ToolExecutionError(
            "not_found",
            f"v0.1 analysis is available only for the seeded dataset {DEMO_DATASET_ID}.",
        )

    try:
        comparison = ComparisonRequest.from_mapping(typed_input.comparison)
        plan_fields = build_default_analysis_plan(comparison)
    except AnalysisValidationError as exc:
        raise ToolExecutionError("invalid_input", str(exc)) from exc

    created_at = _utc_now()
    plan = {
        "id": new_id(EntityPrefix.ANALYSIS_PLAN),
        "schema_version": SCHEMA_VERSION,
        "project_id": typed_input.project_id,
        "dataset_id": typed_input.dataset_id,
        "method_id": plan_fields["method_id"],
        "comparison": {
            "group_a": comparison.group_a,
            "group_b": comparison.group_b,
            "stimulation_context": comparison.stimulation_context,
            "paired_by": comparison.paired_by,
            "proteins": comparison.proteins,
        },
        "rationale": plan_fields["rationale"],
        "assumptions": plan_fields["assumptions"],
        "donor_handling": plan_fields["donor_handling"],
        "replicate_handling": plan_fields["replicate_handling"],
        "multiple_testing": plan_fields["multiple_testing"],
        "limitations": plan_fields["limitations"],
        "unsupported_assumptions": plan_fields["unsupported_assumptions"],
        "created_at": created_at,
    }
    _PLANS[plan["id"]] = plan
    return AnalysisPlanOutput.model_validate(plan)


def _run_comparison_handler(tool_input: BaseModel, context: ToolContext) -> AnalysisResultOutput:
    typed_input = RunComparisonInput.model_validate(tool_input)
    plan = _PLANS.get(typed_input.plan_id)
    if plan is None:
        raise ToolExecutionError("not_found", f"analysis plan not found: {typed_input.plan_id}")
    if plan["project_id"] != typed_input.project_id:
        raise ToolExecutionError(
            "invalid_input",
            "plan_id does not belong to the requested project_id.",
        )
    if plan["method_id"] != DEFAULT_METHOD_ID:
        raise ToolExecutionError(
            "unsupported_method",
            f"unsupported analysis method: {plan['method_id']}",
        )

    fixture_path = _fixture_path(context)
    try:
        output = run_donor_aware_paired_difference(
            load_long_csv(str(fixture_path)),
            ComparisonRequest.from_mapping(plan["comparison"]),
        )
    except AnalysisValidationError as exc:
        raise ToolExecutionError("invalid_input", str(exc)) from exc

    result_id = new_id(EntityPrefix.ANALYSIS_RESULT)
    table_ref = _write_result_table(
        context=context,
        project_id=typed_input.project_id,
        result_id=result_id,
        output=output,
    )
    ranking = {
        "rows": [
            {
                "protein": row.protein,
                "effect_size": row.effect_size,
                "direction": row.direction,
                "p_value": row.p_value,
                "q_value": row.q_value,
                "donor_consistency": row.donor_consistency,
            }
            for row in output.rows
        ],
        "metric": "effect_size",
        "correction": "Benjamini-Hochberg q_value from exact paired sign-flip p-values",
    }
    result = {
        "id": result_id,
        "schema_version": SCHEMA_VERSION,
        "project_id": typed_input.project_id,
        "plan_id": typed_input.plan_id,
        "method_id": output.method_id,
        "ranking": ranking,
        "donor_consistency": output.donor_consistency,
        "table_ref": table_ref,
        "donor_handling": output.donor_handling,
        "replicate_handling": output.replicate_handling,
        "multiple_testing": output.multiple_testing,
        "limitations": output.limitations,
        "created_at": _utc_now(),
    }
    _RESULTS[result_id] = result
    return AnalysisResultOutput.model_validate(result)


def _rank_proteins_handler(tool_input: BaseModel, _context: ToolContext) -> ProteinRankingOutput:
    typed_input = RankProteinsInput.model_validate(tool_input)
    result = _RESULTS.get(typed_input.result_id)
    if result is None:
        raise ToolExecutionError("not_found", f"analysis result not found: {typed_input.result_id}")
    if result["project_id"] != typed_input.project_id:
        raise ToolExecutionError(
            "invalid_input",
            "result_id does not belong to the requested project_id.",
        )
    metric = typed_input.metric or "effect_size"
    if metric != "effect_size":
        raise ToolExecutionError(
            "invalid_input",
            "v0.1 rank_proteins supports only metric='effect_size'.",
        )
    return ProteinRankingOutput.model_validate(result["ranking"])


def _write_result_table(
    *,
    context: ToolContext,
    project_id: str,
    result_id: str,
    output: Any,
) -> dict[str, Any]:
    relative = Path("analysis/results") / f"{result_id}.csv"
    path = _project_root(context, project_id) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "protein",
                "effect_size",
                "direction",
                "p_value",
                "q_value",
                "donor_consistency",
                "donor_count",
                "donor_differences",
            ],
        )
        writer.writeheader()
        for row in output.rows:
            writer.writerow(
                {
                    "protein": row.protein,
                    "effect_size": f"{row.effect_size:.12g}",
                    "direction": row.direction,
                    "p_value": f"{row.p_value:.12g}",
                    "q_value": f"{row.q_value:.12g}",
                    "donor_consistency": f"{row.donor_consistency:.12g}",
                    "donor_count": row.donor_count,
                    "donor_differences": json.dumps(row.donor_differences, sort_keys=True),
                }
            )
    return {
        "uri": f"project://{project_id}/{relative.as_posix()}",
        "media_type": "text/csv",
        "bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
    }


def _fixture_path(context: ToolContext) -> Path:
    project_fixture = (
        _project_root(context, DEMO_PROJECT_ID)
        / "datasets"
        / "raw"
        / "nelisa_pbmc_il10_lps_subset.csv"
    )
    if project_fixture.exists():
        return project_fixture
    return _repo_root() / DEMO_FIXTURE_RELATIVE


def _project_root(context: ToolContext, project_id: str) -> Path:
    state_root = context.state.get("state_root")
    root = Path(state_root) if isinstance(state_root, str | Path) else _repo_root() / ".fpw_state"
    return root / "projects" / project_id


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
