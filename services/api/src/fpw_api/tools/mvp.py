"""MVP tool definitions registered by the shared registry skeleton."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import importlib
import json
import math
import os
import sys
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
from functional_proteomics_corpus import (
    DEFAULT_INDEX_RELATIVE,
    CorpusUnindexedError,
    load_corpus_index,
    search_corpus_index,
)
from pydantic import BaseModel, ConfigDict, Field
from shared_schemas import EntityPrefix, EvidenceChunk, new_id

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
DEMO_SCHEMA_PROFILE_ID = "sp_01KCYAG0000000000000000000"
DEMO_FIXTURE_RELATIVE = Path("demo_data/raw/nelisa_pbmc_il10_lps_subset.csv")
DEMO_PROVENANCE_RELATIVE = Path("demo_data/raw/provenance.json")
DEMO_NORMALIZED_RELATIVE = Path("demo_data/processed/nelisa_pbmc_il10_lps_long.parquet")
DEMO_RAW_NAME = "nelisa_pbmc_il10_lps_subset.csv"
DEMO_PROVENANCE_NAME = "provenance.json"
DEMO_NORMALIZED_NAME = "nelisa_pbmc_il10_lps_long.parquet"
DEMO_SELECTION_URL = "/datasets?source=selected_public&dataset=perturb-pbmc-il10-lps"
DEMO_DASHBOARD_URL = "/?project_id=proj_demo"
DEMO_UPLOAD_EXPIRES_AT = "2026-06-24T00:00:00Z"

REQUIRED_DEMO_COLUMNS = (
    "sample_id",
    "donor",
    "stimulation",
    "stimulus_concentration_ng_ml",
    "perturbagen",
    "cytokine_concentration_ng_ml",
    "protein",
    "response_value",
)
EXPECTED_DONORS = {f"donor_{index}" for index in range(1, 7)}
EXPECTED_PERTURBAGENS = {"IL-10", "control"}
PROTEIN_PANEL = (
    "TNF alpha",
    "IL-1 beta",
    "IL-1 alpha",
    "IL-6",
    "IL-12 p40",
    "IFN gamma",
    "CCL1",
    "CCL2",
    "CCL22",
    "CCL24",
    "CCL5",
    "CCL7",
    "CCL8",
    "CXCL1",
    "CXCL10",
    "CXCL16",
    "G-CSF",
    "GM-CSF",
    "IL-1 RA RN",
    "TNF RII",
    "MMP-1",
)
SUPPORTED_PLOT_TYPES = {"ranked_effect_bar", "volcano", "donor_consistency"}

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
    status: Literal["created", "opened"]
    upload_url: str
    dashboard_url: str
    next_actions: list[str] = Field(default_factory=list)


class ProjectStatusOutput(ToolModel):
    project: dict[str, Any]
    summary_counts: dict[str, int] = Field(default_factory=dict)


class CreateUploadUrlOutput(ToolModel):
    upload_url: str
    expires_at: str
    source: Literal["selected_public"] = "selected_public"
    note: str


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
    plot_id: str | None = None
    table_ref: dict[str, Any]
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
_PLOTS: dict[str, dict[str, Any]] = {}
_EVIDENCE_CHUNKS: dict[str, dict[str, Any]] = {}
_ATTACHMENTS: dict[str, dict[str, Any]] = {}
_REPORTS: dict[str, dict[str, Any]] = {}


class CreatePlotInput(ProjectInput):
    result_id: str
    plot_type: str


class PlotArtifactOutput(ToolModel):
    id: str
    schema_version: str
    project_id: str
    result_id: str
    plot_type: Literal["ranked_effect_bar", "volcano", "donor_consistency"]
    spec_ref: dict[str, Any]
    image_ref: dict[str, Any] | None = None
    created_at: str


class SearchCorpusInput(ToolModel):
    query: str = Field(min_length=1)
    entities: list[str] | None = None
    k: int | None = Field(default=None, ge=1)


class CorpusChunkMetadataOutput(ToolModel):
    source_id: str
    contract_source_id: str
    source_type: Literal["paper", "docs", "github", "webpage", "supplement"]
    title: str
    topic_buckets: list[str]
    approved_for_claims: bool
    retrieval_priority: int
    source_locator: str
    access_route: str
    license_note: str | None = None
    content_sha256: str
    candidate_rank: int | None = None
    citation_count: int | None = None
    candidate_score: float | None = None
    venue: str | None = None


class ScoredEvidenceChunkOutput(ToolModel):
    chunk: EvidenceChunk
    score: float
    matched_entities: list[str] = Field(default_factory=list)
    metadata: CorpusChunkMetadataOutput


class EvidenceChunkListOutput(ToolModel):
    chunks: list[ScoredEvidenceChunkOutput]


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
    created_at: str


class RunEvalSuiteInput(ToolModel):
    suite: str | None = None


class EvalRunOutput(ToolModel):
    id: str
    suite: str
    mode: Literal["smoke", "full"]
    status: Literal["passed", "failed"]
    score: float = Field(ge=0, le=1)
    results: list[dict[str, Any]]
    trace_step_ids: list[str] = Field(default_factory=list)
    created_at: str


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
            handler=_create_project_handler,
        ),
        _tool(
            "get_project_status",
            "Return project status and summary counts.",
            ProjectInput,
            ProjectStatusOutput,
            scope="project",
            mutates_state=False,
            handler=_get_project_status_handler,
        ),
        _tool(
            "create_upload_url",
            "Create an upload URL for a project dataset.",
            ProjectInput,
            CreateUploadUrlOutput,
            scope="project",
            mutates_state=True,
            handler=_create_upload_url_handler,
        ),
        _tool(
            "validate_dataset",
            "Validate a project dataset.",
            ValidateDatasetInput,
            DatasetValidationOutput,
            scope="project",
            mutates_state=True,
            handler=_validate_dataset_handler,
        ),
        _tool(
            "inspect_dataset_schema",
            "Inspect dataset shape and detected experiment axes.",
            ValidateDatasetInput,
            DatasetSchemaOutput,
            scope="project",
            mutates_state=False,
            handler=_inspect_dataset_schema_handler,
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
            handler=_create_plot_handler,
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
            handler=_search_corpus_handler,
        ),
        _tool(
            "attach_evidence",
            "Attach evidence chunks to project work.",
            AttachEvidenceInput,
            EvidenceAttachmentOutput,
            scope="project",
            mutates_state=True,
            handler=_attach_evidence_handler,
        ),
        _tool(
            "export_report",
            "Export a claim-typed report artifact.",
            ExportReportInput,
            ReportArtifactOutput,
            scope="project",
            mutates_state=True,
            handler=_export_report_handler,
        ),
        _tool(
            "run_eval_suite",
            "Run a deterministic eval suite.",
            RunEvalSuiteInput,
            EvalRunOutput,
            scope="global",
            mutates_state=False,
            eval_tags=["eval"],
            handler=_run_eval_suite_handler,
        ),
        _tool(
            "get_trace",
            "Return project-scoped tool traces.",
            GetTraceInput,
            GetTraceOutput,
            scope="project",
            mutates_state=False,
            handler=_get_trace_handler,
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


def _create_project_handler(tool_input: BaseModel, context: ToolContext) -> CreateProjectOutput:
    typed_input = CreateProjectInput.model_validate(tool_input)
    projects = _shared_projects_for_write(context)
    opened = DEMO_PROJECT_ID in projects
    project_state = projects.get(DEMO_PROJECT_ID) or _demo_project_state(title=typed_input.title)
    projects[DEMO_PROJECT_ID] = project_state
    _write_seeded_project_files(context, project_state)
    return CreateProjectOutput(
        project_id=DEMO_PROJECT_ID,
        status="opened" if opened else "created",
        upload_url=DEMO_SELECTION_URL,
        dashboard_url=DEMO_DASHBOARD_URL,
        next_actions=[
            "create_upload_url",
            "validate_dataset",
            "inspect_dataset_schema",
            "define_comparison",
        ],
    )


def _get_project_status_handler(tool_input: BaseModel, context: ToolContext) -> ProjectStatusOutput:
    typed_input = ProjectInput.model_validate(tool_input)
    projects = _shared_projects(context)
    project = projects.get(typed_input.project_id)
    if project is None and typed_input.project_id == DEMO_PROJECT_ID:
        project = _demo_project_state()
    if project is None:
        raise ToolExecutionError("not_found", f"project not found: {typed_input.project_id}")

    project_contract = project.get("project")
    if not isinstance(project_contract, dict):
        raise ToolExecutionError("internal_error", "project state is missing contract fields.")

    summary_counts = _project_summary_counts(
        project_id=typed_input.project_id,
        project=project,
        trace_count=_trace_count_for_project(context, typed_input.project_id),
    )
    return ProjectStatusOutput(project=project_contract, summary_counts=summary_counts)


def _create_upload_url_handler(
    tool_input: BaseModel,
    context: ToolContext,
) -> CreateUploadUrlOutput:
    typed_input = ProjectInput.model_validate(tool_input)
    _require_demo_project(typed_input.project_id)
    _ensure_project_state(context, typed_input.project_id)
    return CreateUploadUrlOutput(
        upload_url=DEMO_SELECTION_URL,
        expires_at=DEMO_UPLOAD_EXPIRES_AT,
        note=(
            "v0.1 supports only the selected public Perturb-PBMC IL-10/LPS fixture; "
            "arbitrary uploads are intentionally disabled."
        ),
    )


def _validate_dataset_handler(
    tool_input: BaseModel,
    context: ToolContext,
) -> DatasetValidationOutput:
    typed_input = ValidateDatasetInput.model_validate(tool_input)
    _require_demo_dataset(typed_input)
    validation = _validate_demo_fixture(_fixture_path(context), _provenance_path(context))
    project = _ensure_project_state(context, typed_input.project_id)
    for dataset in project.get("datasets", []):
        if isinstance(dataset, dict) and dataset.get("id") == DEMO_DATASET_ID:
            dataset["status"] = "validated" if validation["status"] == "passed" else "failed"
            dataset["rows"] = validation["row_count"]
            dataset["validation"] = validation
    _write_json_project_artifact(
        context,
        typed_input.project_id,
        Path("datasets/validation.json"),
        validation,
    )
    return DatasetValidationOutput.model_validate(validation)


def _inspect_dataset_schema_handler(
    tool_input: BaseModel,
    context: ToolContext,
) -> DatasetSchemaOutput:
    typed_input = ValidateDatasetInput.model_validate(tool_input)
    _require_demo_dataset(typed_input)
    _ensure_project_state(context, typed_input.project_id)
    profile = _schema_profile_for_fixture()
    _write_json_project_artifact(
        context,
        typed_input.project_id,
        Path("datasets/schema_profile.json"),
        profile,
    )
    return DatasetSchemaOutput.model_validate(profile)


def _shared_projects(context: ToolContext) -> dict[str, dict[str, Any]]:
    raw_projects = context.state.get("projects", {})
    if not isinstance(raw_projects, dict):
        raise ToolExecutionError("internal_error", "shared project state must be a mapping.")
    return raw_projects


def _shared_projects_for_write(context: ToolContext) -> dict[str, dict[str, Any]]:
    raw_projects = context.state.setdefault("projects", {})
    if not isinstance(raw_projects, dict):
        raise ToolExecutionError("internal_error", "shared project state must be a mapping.")
    return raw_projects


def _demo_project_state(title: str | None = None) -> dict[str, Any]:
    created_at = "2026-06-24T00:00:00Z"
    return {
        "project": {
            "id": DEMO_PROJECT_ID,
            "schema_version": SCHEMA_VERSION,
            "title": title or "v0.1 Perturb-PBMC IL-10/LPS demo",
            "status": "validated",
            "context_md": (
                "Seeded v0.1 demo project for IL-10 vs matched no-cytokine control "
                "under LPS 2000 ng/mL using the approved public Perturb-PBMC subset."
            ),
            "created_at": created_at,
            "updated_at": created_at,
        },
        "datasets": [
            {
                "id": DEMO_DATASET_ID,
                "source": "selected_public",
                "status": "validated",
                "rows": 2394,
                "validation": {"status": "passed", "row_count": 2394, "issues": []},
            }
        ],
    }


def _require_demo_project(project_id: str) -> None:
    if project_id != DEMO_PROJECT_ID:
        raise ToolExecutionError(
            "out_of_scope",
            f"v0.1 supports only the deterministic demo project {DEMO_PROJECT_ID}.",
        )


def _require_demo_dataset(tool_input: ValidateDatasetInput) -> None:
    _require_demo_project(tool_input.project_id)
    if tool_input.dataset_id != DEMO_DATASET_ID:
        raise ToolExecutionError(
            "out_of_scope",
            f"v0.1 supports only the selected public dataset {DEMO_DATASET_ID}.",
        )


def _ensure_project_state(context: ToolContext, project_id: str) -> dict[str, Any]:
    _require_demo_project(project_id)
    projects = _shared_projects_for_write(context)
    project = projects.get(project_id)
    if project is None:
        project = _demo_project_state()
        projects[project_id] = project
    _write_seeded_project_files(context, project)
    return project


def _project_summary_counts(
    *,
    project_id: str,
    project: dict[str, Any],
    trace_count: int,
) -> dict[str, int]:
    datasets = project.get("datasets", [])
    dataset_count = len(datasets) if isinstance(datasets, list) else 0
    return {
        "datasets": dataset_count,
        "analysis_plans": sum(
            1 for plan in _PLANS.values() if plan.get("project_id") == project_id
        ),
        "analysis_results": sum(
            1 for result in _RESULTS.values() if result.get("project_id") == project_id
        ),
        "tool_calls": trace_count,
    }


def _trace_count_for_project(context: ToolContext, project_id: str) -> int:
    traces = getattr(context.trace_sink, "traces", None)
    if not isinstance(traces, list):
        return 0
    return sum(
        1
        for trace in traces
        if getattr(trace, "project_id", None) == project_id
    )


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
        "plot_id": None,
        "table_ref": table_ref,
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


def _create_plot_handler(tool_input: BaseModel, context: ToolContext) -> PlotArtifactOutput:
    typed_input = CreatePlotInput.model_validate(tool_input)
    if typed_input.plot_type not in SUPPORTED_PLOT_TYPES:
        raise ToolExecutionError(
            "unsupported_plot",
            (
                "v0.1 create_plot supports only ranked_effect_bar, volcano, "
                "or donor_consistency."
            ),
        )
    result = _RESULTS.get(typed_input.result_id)
    if result is None:
        raise ToolExecutionError("not_found", f"analysis result not found: {typed_input.result_id}")
    if result["project_id"] != typed_input.project_id:
        raise ToolExecutionError(
            "invalid_input",
            "result_id does not belong to the requested project_id.",
        )

    plot_id = new_id(EntityPrefix.PLOT_ARTIFACT)
    spec = _plot_spec(typed_input.plot_type, result)
    spec_ref = _write_json_project_artifact(
        context,
        typed_input.project_id,
        Path("analysis/plots") / f"{plot_id}.json",
        spec,
    )
    plot = {
        "id": plot_id,
        "schema_version": SCHEMA_VERSION,
        "project_id": typed_input.project_id,
        "result_id": typed_input.result_id,
        "plot_type": typed_input.plot_type,
        "spec_ref": spec_ref,
        "image_ref": None,
        "created_at": _utc_now(),
    }
    _PLOTS[plot_id] = plot
    result["plot_id"] = plot_id
    return PlotArtifactOutput.model_validate(plot)


def _search_corpus_handler(tool_input: BaseModel, context: ToolContext) -> EvidenceChunkListOutput:
    typed_input = SearchCorpusInput.model_validate(tool_input)
    try:
        index = load_corpus_index(_corpus_index_path(context))
    except CorpusUnindexedError as exc:
        raise ToolExecutionError("corpus_unindexed", str(exc)) from exc

    chunks = search_corpus_index(
        index,
        typed_input.query,
        entities=typed_input.entities,
        k=typed_input.k or 5,
    )
    output_chunks = [_scored_evidence_chunk_output(chunk) for chunk in chunks]
    for output_chunk in output_chunks:
        dumped = output_chunk.model_dump(mode="json")
        _EVIDENCE_CHUNKS[dumped["chunk"]["id"]] = dumped
    return EvidenceChunkListOutput(chunks=output_chunks)


def _attach_evidence_handler(
    tool_input: BaseModel,
    context: ToolContext,
) -> EvidenceAttachmentOutput:
    typed_input = AttachEvidenceInput.model_validate(tool_input)
    _ensure_project_state(context, typed_input.project_id)
    if not typed_input.chunk_ids:
        raise ToolExecutionError("invalid_input", "chunk_ids must include at least one chunk.")
    missing = [
        chunk_id for chunk_id in typed_input.chunk_ids if chunk_id not in _EVIDENCE_CHUNKS
    ]
    if missing:
        raise ToolExecutionError(
            "not_found",
            "evidence chunks must come from prior deterministic corpus retrieval: "
            + ", ".join(missing),
        )
    attachment = {
        "id": new_id(EntityPrefix.EVIDENCE_ATTACHMENT),
        "schema_version": SCHEMA_VERSION,
        "project_id": typed_input.project_id,
        "chunk_ids": typed_input.chunk_ids,
        "supports_report_id": typed_input.supports_report_id,
        "note": "Approved deterministic corpus chunks attached for v0.1 report support.",
    }
    _ATTACHMENTS[attachment["id"]] = attachment
    _write_json_project_artifact(
        context,
        typed_input.project_id,
        Path("evidence/attachments") / f"{attachment['id']}.json",
        attachment,
    )
    return EvidenceAttachmentOutput.model_validate(attachment)


def _export_report_handler(tool_input: BaseModel, context: ToolContext) -> ReportArtifactOutput:
    typed_input = ExportReportInput.model_validate(tool_input)
    result = _RESULTS.get(typed_input.result_id)
    if result is None:
        raise ToolExecutionError("not_found", f"analysis result not found: {typed_input.result_id}")
    if result["project_id"] != typed_input.project_id:
        raise ToolExecutionError(
            "invalid_input",
            "result_id does not belong to the requested project_id.",
        )
    attachments = _report_attachments(typed_input)
    chunk_ids = [chunk_id for attachment in attachments for chunk_id in attachment["chunk_ids"]]
    if not chunk_ids:
        raise ToolExecutionError(
            "invalid_input",
            (
                "export_report requires at least one attached evidence chunk "
                "for source-derived claims."
            ),
        )

    report_id = new_id(EntityPrefix.REPORT_ARTIFACT)
    claims = _report_claims(result, chunk_ids)
    markdown = _report_markdown(result, claims, chunk_ids)
    markdown_ref = _write_text_project_artifact(
        context,
        typed_input.project_id,
        Path("reports") / f"{report_id}.md",
        markdown,
    )
    report = {
        "id": report_id,
        "schema_version": SCHEMA_VERSION,
        "project_id": typed_input.project_id,
        "markdown_ref": markdown_ref,
        "claims": claims,
        "created_at": _utc_now(),
    }
    _REPORTS[report_id] = report
    for attachment in attachments:
        attachment["supports_report_id"] = report_id
    return ReportArtifactOutput.model_validate(report)


async def _run_eval_suite_handler(tool_input: BaseModel, _context: ToolContext) -> EvalRunOutput:
    typed_input = RunEvalSuiteInput.model_validate(tool_input)
    suite = typed_input.suite or "smoke"
    if suite not in {"smoke", "full", "deterministic-smoke", "offline-skeleton"}:
        raise ToolExecutionError(
            "invalid_input",
            "v0.1 run_eval_suite supports suite='smoke' or suite='full'.",
        )
    mode: Literal["smoke", "full"] = "full" if suite in {"full", "offline-skeleton"} else "smoke"
    repo_root = _repo_root()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    run_eval_suite = importlib.import_module("evals.runners.runner").run_eval_suite

    report = await asyncio.to_thread(run_eval_suite, mode)
    trace_step_ids = [
        trace_step_id
        for result in report["results"]
        for trace_step_id in result["trace_step_ids"]
    ]
    return EvalRunOutput(
        id=report["id"],
        suite=report["suite"],
        mode=report["mode"],
        status="passed" if report["score"] == 1 else "failed",
        score=report["score"],
        results=report["results"],
        trace_step_ids=trace_step_ids,
        created_at=report["created_at"],
    )


def _get_trace_handler(tool_input: BaseModel, context: ToolContext) -> GetTraceOutput:
    typed_input = GetTraceInput.model_validate(tool_input)
    traces = getattr(context.trace_sink, "traces", None)
    if not isinstance(traces, list):
        return GetTraceOutput(traces=[])
    project_traces = [
        trace.model_dump(mode="json")
        for trace in traces
        if getattr(trace, "project_id", None) == typed_input.project_id
    ]
    if typed_input.kind:
        project_traces = [
            trace
            for trace in project_traces
            if trace["tool_name"] == typed_input.kind
            or trace.get("origin", {}).get("surface") == typed_input.kind
            or trace["status"] == typed_input.kind
        ]
    return GetTraceOutput(traces=project_traces)


def _scored_evidence_chunk_output(chunk: dict[str, Any]) -> ScoredEvidenceChunkOutput:
    manifest_source_id = str(chunk["source_id"])
    contract_source_id = _deterministic_contract_id(
        EntityPrefix.EVIDENCE_SOURCE,
        manifest_source_id,
    )
    evidence_chunk = {
        "id": _deterministic_contract_id(EntityPrefix.EVIDENCE_CHUNK, str(chunk["id"])),
        "schema_version": SCHEMA_VERSION,
        "source_id": contract_source_id,
        "text": chunk["text"],
        "section": chunk.get("section"),
        "entities": chunk.get("entities", []),
        "assay_context": chunk.get("assay_context", []),
        "citation": chunk["citation"],
        "embedding_status": chunk.get("embedding_status", "pending"),
    }
    metadata = dict(chunk["metadata"])
    metadata["contract_source_id"] = contract_source_id
    return ScoredEvidenceChunkOutput.model_validate(
        {
            "chunk": evidence_chunk,
            "score": chunk["score"],
            "matched_entities": chunk.get("matched_entities", []),
            "metadata": metadata,
        }
    )


def _plot_spec(plot_type: str, result: dict[str, Any]) -> dict[str, Any]:
    ranking_rows = result["ranking"]["rows"]
    if plot_type == "ranked_effect_bar":
        rows = ranking_rows[:12]
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": "plotly",
            "plot_type": plot_type,
            "data": [
                {
                    "type": "bar",
                    "orientation": "h",
                    "x": [row["effect_size"] for row in rows],
                    "y": [row["protein"] for row in rows],
                    "marker": {
                        "color": [
                            "#2f6f9f" if row["direction"] == "up" else "#b34d4d"
                            for row in rows
                        ]
                    },
                }
            ],
            "layout": {
                "title": "Ranked IL-10 vs control response-value differences",
                "xaxis": {"title": "Donor-aware paired effect size"},
                "yaxis": {"title": "Protein", "autorange": "reversed"},
            },
        }
    if plot_type == "volcano":
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": "plotly",
            "plot_type": plot_type,
            "data": [
                {
                    "type": "scatter",
                    "mode": "markers",
                    "x": [row["effect_size"] for row in ranking_rows],
                    "y": [
                        -math.log10(max(float(row["q_value"] or 1.0), 1e-12))
                        for row in ranking_rows
                    ],
                    "text": [row["protein"] for row in ranking_rows],
                }
            ],
            "layout": {
                "title": "Exploratory effect size vs q-value",
                "xaxis": {"title": "Effect size"},
                "yaxis": {"title": "-log10(q-value)"},
            },
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "plotly",
        "plot_type": plot_type,
        "data": [
            {
                "type": "bar",
                "x": [row["donor"] for row in result["donor_consistency"]],
                "y": [
                    1 if row["agrees_with_consensus"] else 0
                    for row in result["donor_consistency"]
                ],
                "text": [row.get("note") for row in result["donor_consistency"]],
            }
        ],
        "layout": {
            "title": "Donor consistency with consensus direction",
            "xaxis": {"title": "Donor"},
            "yaxis": {"title": "Agrees with consensus", "range": [0, 1]},
        },
    }


def _report_attachments(typed_input: ExportReportInput) -> list[dict[str, Any]]:
    if typed_input.attachment_ids is None:
        return [
            attachment
            for attachment in _ATTACHMENTS.values()
            if attachment["project_id"] == typed_input.project_id
        ]
    attachments: list[dict[str, Any]] = []
    for attachment_id in typed_input.attachment_ids:
        attachment = _ATTACHMENTS.get(attachment_id)
        if attachment is None:
            raise ToolExecutionError("not_found", f"evidence attachment not found: {attachment_id}")
        if attachment["project_id"] != typed_input.project_id:
            raise ToolExecutionError(
                "invalid_input",
                "attachment_ids must belong to the requested project_id.",
            )
        attachments.append(attachment)
    return attachments


def _report_claims(result: dict[str, Any], chunk_ids: list[str]) -> list[dict[str, Any]]:
    top_row = result["ranking"]["rows"][0]
    return [
        {
            "text": (
                f"{top_row['protein']} has the largest absolute donor-aware paired "
                f"effect size in the seeded IL-10/LPS comparison."
            ),
            "kind": "data-derived",
            "evidence_chunk_ids": [],
        },
        {
            "text": (
                "The selected public fixture and IL-10/LPS interpretation are grounded "
                "only in approved retrieved corpus chunks."
            ),
            "kind": "source-derived",
            "evidence_chunk_ids": chunk_ids,
        },
        {
            "text": (
                "The report is a descriptive fixture-bounded readout, not a mechanistic "
                "or generalized biological conclusion."
            ),
            "kind": "interpretive",
            "evidence_chunk_ids": chunk_ids,
        },
        {
            "text": (
                "The donor count is small and q-values are exploratory for demo review."
            ),
            "kind": "limitation",
            "evidence_chunk_ids": [],
        },
    ]


def _report_markdown(
    result: dict[str, Any],
    claims: list[dict[str, Any]],
    chunk_ids: list[str],
) -> str:
    top_rows = result["ranking"]["rows"][:6]
    lines = [
        "# IL-10 vs matched no-cytokine control under LPS 2000 ng/mL",
        "",
        "Generated from the seeded public Perturb-PBMC/nELISA fixture.",
        "",
        "## Top ranked proteins",
        "",
        "| Protein | Effect size | Direction | q-value | Donor consistency |",
        "|---|---:|---|---:|---:|",
    ]
    for row in top_rows:
        q_value = "" if row["q_value"] is None else f"{row['q_value']:.4g}"
        consistency = (
            "" if row["donor_consistency"] is None else f"{row['donor_consistency']:.3g}"
        )
        lines.append(
            f"| {row['protein']} | {row['effect_size']:.4g} | {row['direction']} | "
            f"{q_value} | {consistency} |"
        )
    lines.extend(["", "## Claims", ""])
    for claim in claims:
        support = ", ".join(claim["evidence_chunk_ids"]) or "analysis result"
        lines.append(f"- **{claim['kind']}**: {claim['text']} Support: {support}.")
    lines.extend(["", "## Evidence chunks", ""])
    for chunk_id in chunk_ids:
        chunk = _EVIDENCE_CHUNKS[chunk_id]["chunk"]
        citation = chunk.get("citation", {})
        locator = citation.get("doi") or citation.get("url") or chunk["source_id"]
        lines.append(f"- `{chunk_id}`: {locator}")
    return "\n".join(lines) + "\n"


def _write_seeded_project_files(context: ToolContext, project_state: dict[str, Any]) -> None:
    project = project_state.get("project", {})
    if not isinstance(project, dict) or project.get("id") != DEMO_PROJECT_ID:
        return
    dataset = _dataset_contract(context)
    _write_json_project_artifact(context, DEMO_PROJECT_ID, Path("project.json"), project)
    _write_text_project_artifact(
        context,
        DEMO_PROJECT_ID,
        Path("context.md"),
        str(project.get("context_md") or ""),
    )
    _write_json_project_artifact(context, DEMO_PROJECT_ID, Path("datasets/dataset.json"), dataset)
    _write_json_project_artifact(
        context,
        DEMO_PROJECT_ID,
        Path("datasets/schema_profile.json"),
        _schema_profile_for_fixture(),
    )


def _dataset_contract(context: ToolContext) -> dict[str, Any]:
    raw_path = _fixture_path(context)
    normalized_path = _normalized_path(context)
    validation = _validate_demo_fixture(raw_path, _provenance_path(context))
    return {
        "id": DEMO_DATASET_ID,
        "project_id": DEMO_PROJECT_ID,
        "schema_version": SCHEMA_VERSION,
        "name": "Perturb-PBMC IL-10/LPS direct subset",
        "source": "selected_public",
        "raw_ref": _artifact_ref(
            DEMO_PROJECT_ID,
            Path("datasets/raw") / DEMO_RAW_NAME,
            "text/csv",
            raw_path if raw_path.exists() else None,
        ),
        "normalized_ref": _artifact_ref(
            DEMO_PROJECT_ID,
            Path("datasets/normalized") / DEMO_NORMALIZED_NAME,
            "application/parquet",
            normalized_path if normalized_path.exists() else None,
        ),
        "validation": validation,
        "created_at": "2026-06-24T00:00:00Z",
    }


def _validate_demo_fixture(raw_path: Path, provenance_path: Path) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    rows = _read_demo_rows(raw_path, issues)
    if rows:
        _validate_demo_rows(rows, issues)
    _validate_demo_provenance(provenance_path, len(rows), issues)
    return {
        "status": "failed" if issues else "passed",
        "row_count": len(rows),
        "issues": issues,
    }


def _read_demo_rows(path: Path, issues: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not path.exists():
        _append_issue(issues, "SCHEMA_MISSING_COLUMN", f"fixture file does not exist: {path}")
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in REQUIRED_DEMO_COLUMNS if column not in fieldnames]
        for column in missing:
            _append_issue(
                issues,
                "SCHEMA_MISSING_COLUMN",
                f"required column {column!r} is missing",
                column,
            )
        if missing:
            return []
        return list(reader)


def _validate_demo_rows(rows: list[dict[str, str]], issues: list[dict[str, Any]]) -> None:
    donors: set[str] = set()
    perturbagens: set[str] = set()
    proteins: set[str] = set()
    samples_by_donor_group: dict[tuple[str, str], set[str]] = {}
    sample_ids: set[str] = set()
    sample_protein_pairs: set[tuple[str, str]] = set()
    for row_number, row in enumerate(rows, start=2):
        donor = row["donor"]
        perturbagen = row["perturbagen"]
        protein = row["protein"]
        sample_id = row["sample_id"]
        donors.add(donor)
        perturbagens.add(perturbagen)
        proteins.add(protein)
        sample_ids.add(sample_id)
        sample_protein_pairs.add((sample_id, protein))
        samples_by_donor_group.setdefault((donor, perturbagen), set()).add(sample_id)

        if donor not in EXPECTED_DONORS:
            _append_issue(issues, "UNEXPECTED_CATEGORY", f"unexpected donor {donor!r}", "donor")
        if row["stimulation"] != "LPS":
            _append_issue(
                issues,
                "UNEXPECTED_CATEGORY",
                f"unexpected stimulation {row['stimulation']!r} at row {row_number}",
                "stimulation",
            )
        if _parse_float(row["stimulus_concentration_ng_ml"]) != 2000.0:
            _append_issue(
                issues,
                "UNEXPECTED_CATEGORY",
                "stimulus_concentration_ng_ml must be 2000.0 for every row",
                "stimulus_concentration_ng_ml",
            )
        if perturbagen not in EXPECTED_PERTURBAGENS:
            _append_issue(
                issues,
                "UNEXPECTED_CATEGORY",
                f"unexpected perturbagen {perturbagen!r}",
                "perturbagen",
            )
        expected_cytokine = 50.0 if perturbagen == "IL-10" else 0.0
        if _parse_float(row["cytokine_concentration_ng_ml"]) != expected_cytokine:
            _append_issue(
                issues,
                "UNEXPECTED_CATEGORY",
                "cytokine concentration does not match perturbagen",
                "cytokine_concentration_ng_ml",
            )
        if protein not in PROTEIN_PANEL:
            _append_issue(
                issues,
                "PROTEIN_NOT_IN_PANEL",
                f"protein {protein!r} is not in the frozen panel",
                "protein",
            )
        response_value = _parse_float(row["response_value"])
        if response_value is None or not math.isfinite(response_value):
            _append_issue(
                issues,
                "NULL_VALUE",
                "response_value must be finite and non-null",
                "response_value",
            )

    if donors != EXPECTED_DONORS:
        _append_issue(
            issues,
            "MISSING_GROUP_FOR_DONOR",
            "fixture must contain exactly donor_1 through donor_6",
            "donor",
        )
    if not EXPECTED_PERTURBAGENS.issubset(perturbagens):
        _append_issue(
            issues,
            "MISSING_GROUP_FOR_DONOR",
            "fixture must contain both IL-10 and control perturbagens",
            "perturbagen",
        )
    missing_panel = set(PROTEIN_PANEL) - proteins
    if missing_panel:
        _append_issue(
            issues,
            "PROTEIN_NOT_IN_PANEL",
            f"fixture is missing panel proteins: {sorted(missing_panel)}",
            "protein",
        )
    for donor in sorted(EXPECTED_DONORS):
        for perturbagen in sorted(EXPECTED_PERTURBAGENS):
            if not samples_by_donor_group.get((donor, perturbagen)):
                _append_issue(
                    issues,
                    "MISSING_GROUP_FOR_DONOR",
                    f"{donor} is missing {perturbagen} samples",
                    "donor",
                )
    expected_row_count = len(sample_ids) * len(PROTEIN_PANEL)
    if len(rows) != expected_row_count or len(sample_protein_pairs) != expected_row_count:
        _append_issue(
            issues,
            "SCHEMA_MISSING_COLUMN",
            "fixture must be rectangular: one row per sample/protein pair",
        )


def _validate_demo_provenance(
    path: Path,
    row_count: int,
    issues: list[dict[str, Any]],
) -> None:
    if not path.exists():
        _append_issue(issues, "SCHEMA_MISSING_COLUMN", f"provenance file does not exist: {path}")
        return
    provenance = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "source_repo": "https://github.com/nplexbio/nELISA-PBMC",
        "source_commit": "c26223a1d29a1efbdb6577160fab2a323fb7d80d",
        "source_file": "figure 4/data_pgmc_umap.h5ad",
        "source_file_sha256": (
            "eaf448510a429797a9ca2d8f2581c13573e90868c8190edbbe4a4e209df51500"
        ),
        "value_type": "normalized_response",
    }
    for key, value in expected.items():
        if provenance.get(key) != value:
            _append_issue(
                issues,
                "UNEXPECTED_CATEGORY",
                f"provenance {key} must be {value!r}",
                key,
            )
    if provenance.get("row_count") != row_count:
        _append_issue(
            issues,
            "UNEXPECTED_CATEGORY",
            "provenance row_count must match fixture row count",
            "row_count",
        )
    selection = provenance.get("selection", {})
    if tuple(selection.get("proteins", ())) != PROTEIN_PANEL:
        _append_issue(
            issues,
            "PROTEIN_NOT_IN_PANEL",
            "provenance selection.proteins must match the frozen panel",
            "selection.proteins",
        )


def _append_issue(
    issues: list[dict[str, Any]],
    code: str,
    message: str,
    column: str | None = None,
) -> None:
    if any(issue["code"] == code and issue.get("column") == column for issue in issues):
        return
    issues.append(
        {"severity": "error", "code": code, "message": message, "column": column}
    )


def _parse_float(value: str) -> float | None:
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _schema_profile_for_fixture() -> dict[str, Any]:
    columns = [
        ("sample_id", "string", "metadata", 114, ["266", "267", "268"]),
        ("donor", "categorical", "donor", 6, ["donor_1", "donor_2", "donor_3"]),
        ("stimulation", "categorical", "stimulation", 1, ["LPS"]),
        ("stimulus_concentration_ng_ml", "float", "metadata", 1, ["2000.0"]),
        ("perturbagen", "categorical", "perturbagen", 2, ["IL-10", "control"]),
        ("cytokine_concentration_ng_ml", "float", "metadata", 2, ["50.0", "0.0"]),
        ("protein", "categorical", "protein", len(PROTEIN_PANEL), list(PROTEIN_PANEL[:3])),
        ("response_value", "float", "value", None, ["0.0"]),
    ]
    return {
        "id": DEMO_SCHEMA_PROFILE_ID,
        "schema_version": SCHEMA_VERSION,
        "dataset_id": DEMO_DATASET_ID,
        "layout": "long",
        "columns": [
            {
                "name": name,
                "dtype": dtype,
                "role": role,
                "n_unique": n_unique,
                "examples": examples,
            }
            for name, dtype, role, n_unique, examples in columns
        ],
        "detected_axes": {
            "donor": "donor",
            "stimulation": "stimulation",
            "perturbagen": "perturbagen",
            "protein": "protein",
            "value": "response_value",
        },
    }


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


def _write_json_project_artifact(
    context: ToolContext,
    project_id: str,
    relative: Path,
    payload: dict[str, Any],
) -> dict[str, Any]:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    return _write_text_project_artifact(
        context,
        project_id,
        relative,
        text,
        media_type="application/json",
    )


def _write_text_project_artifact(
    context: ToolContext,
    project_id: str,
    relative: Path,
    text: str,
    *,
    media_type: str = "text/markdown",
) -> dict[str, Any]:
    path = _project_root(context, project_id) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return _artifact_ref(project_id, relative, media_type, path)


def _artifact_ref(
    project_id: str,
    relative: Path,
    media_type: str,
    path: Path | None,
) -> dict[str, Any]:
    return {
        "uri": f"project://{project_id}/{relative.as_posix()}",
        "media_type": media_type,
        "bytes": path.stat().st_size if path is not None and path.exists() else None,
        "sha256": _sha256_file(path) if path is not None and path.exists() else None,
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


def _provenance_path(context: ToolContext) -> Path:
    project_provenance = (
        _project_root(context, DEMO_PROJECT_ID)
        / "datasets"
        / "raw"
        / DEMO_PROVENANCE_NAME
    )
    if project_provenance.exists():
        return project_provenance
    return _repo_root() / DEMO_PROVENANCE_RELATIVE


def _normalized_path(context: ToolContext) -> Path:
    project_normalized = (
        _project_root(context, DEMO_PROJECT_ID)
        / "datasets"
        / "normalized"
        / DEMO_NORMALIZED_NAME
    )
    if project_normalized.exists():
        return project_normalized
    return _repo_root() / DEMO_NORMALIZED_RELATIVE


def _project_root(context: ToolContext, project_id: str) -> Path:
    state_root = context.state.get("state_root")
    root = Path(state_root) if isinstance(state_root, str | Path) else _repo_root() / ".fpw_state"
    return root / "projects" / project_id


def _corpus_index_path(context: ToolContext) -> Path:
    explicit = context.state.get("corpus_index_path")
    if isinstance(explicit, str | Path):
        return Path(explicit)
    env_path = os.environ.get("FPW_CORPUS_INDEX_PATH")
    if env_path:
        return Path(env_path)
    return _repo_root() / DEFAULT_INDEX_RELATIVE


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


def _deterministic_contract_id(prefix: EntityPrefix, value: str) -> str:
    alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    number = int.from_bytes(digest[:16], "big")
    chars: list[str] = []
    for _ in range(26):
        chars.append(alphabet[number & 31])
        number >>= 5
    return f"{prefix.value}{''.join(reversed(chars))}"
