"""MVP tool definitions registered by the shared registry skeleton."""

from __future__ import annotations

import csv
import hashlib
import importlib
import json
import os
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
_ATTACHMENTS: dict[str, dict[str, Any]] = {}
_REPORTS: dict[str, dict[str, Any]] = {}


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


class RunEvalSuiteInput(ToolModel):
    suite: str | None = None


class EvalRunOutput(ToolModel):
    id: str
    suite: str
    mode: Literal["smoke", "full"]
    status: Literal["passed", "failed"]
    score: float
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
    project_id = new_id(EntityPrefix.PROJECT)
    created_at = _utc_now()
    _shared_projects(context)[project_id] = {
        "project": {
            "id": project_id,
            "schema_version": SCHEMA_VERSION,
            "title": typed_input.title,
            "status": "dataset_pending",
            "context_md": (
                "Agent-created v0.1 project prepared for the approved selected_public "
                "Perturb-PBMC IL-10/LPS dataset handoff."
            ),
            "created_at": created_at,
            "updated_at": created_at,
        },
        "datasets": [
            {
                "id": DEMO_DATASET_ID,
                "source": "selected_public",
                "status": "pending",
                "rows": None,
            }
        ],
    }
    return CreateProjectOutput(
        project_id=project_id,
        status="created",
        upload_url=f"/datasets?project_id={project_id}&source=selected_public",
        dashboard_url=f"/?project_id={project_id}",
        next_actions=["validate_dataset", "inspect_dataset_schema"],
    )


def _create_upload_url_handler(
    tool_input: BaseModel,
    _context: ToolContext,
) -> CreateUploadUrlOutput:
    typed_input = ProjectInput.model_validate(tool_input)
    return CreateUploadUrlOutput(
        upload_url=f"/datasets?project_id={typed_input.project_id}&source=selected_public",
        expires_at="2026-06-24T00:15:00Z",
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


def _shared_projects(context: ToolContext) -> dict[str, dict[str, Any]]:
    raw_projects = context.state.get("projects", {})
    if not isinstance(raw_projects, dict):
        raise ToolExecutionError("internal_error", "shared project state must be a mapping.")
    return raw_projects


def _require_project(context: ToolContext, project_id: str) -> dict[str, Any]:
    projects = _shared_projects(context)
    project = projects.get(project_id)
    if project is None and project_id == DEMO_PROJECT_ID:
        project = _demo_project_state()
        projects[project_id] = project
    if project is None:
        raise ToolExecutionError("not_found", f"project not found: {project_id}")
    return project


def _demo_project_state() -> dict[str, Any]:
    created_at = "2026-06-24T00:00:00Z"
    return {
        "project": {
            "id": DEMO_PROJECT_ID,
            "schema_version": SCHEMA_VERSION,
            "title": "v0.1 Perturb-PBMC IL-10/LPS demo",
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
            }
        ],
    }


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


def _validate_dataset_handler(
    tool_input: BaseModel,
    context: ToolContext,
) -> DatasetValidationOutput:
    typed_input = ValidateDatasetInput.model_validate(tool_input)
    project = _require_project(context, typed_input.project_id)
    dataset = _require_demo_dataset(project, typed_input.dataset_id)
    row_count = _fixture_row_count(_fixture_path(context))
    dataset["status"] = "validated"
    dataset["rows"] = row_count
    project_contract = project.get("project")
    if isinstance(project_contract, dict):
        project_contract["status"] = "validated"
        project_contract["updated_at"] = _utc_now()
    return DatasetValidationOutput(status="passed", row_count=row_count, issues=[])


def _inspect_dataset_schema_handler(
    tool_input: BaseModel,
    context: ToolContext,
) -> DatasetSchemaOutput:
    typed_input = ValidateDatasetInput.model_validate(tool_input)
    _require_demo_dataset(_require_project(context, typed_input.project_id), typed_input.dataset_id)
    return DatasetSchemaOutput(
        id=new_id(EntityPrefix.DATASET_SCHEMA_PROFILE),
        schema_version=SCHEMA_VERSION,
        dataset_id=typed_input.dataset_id,
        layout="long",
        columns=[
            {"name": "sample_id", "dtype": "string", "role": "metadata", "n_unique": None},
            {"name": "donor", "dtype": "string", "role": "donor", "n_unique": 6},
            {"name": "stimulation", "dtype": "categorical", "role": "stimulation", "n_unique": 1},
            {
                "name": "stimulus_concentration_ng_ml",
                "dtype": "float",
                "role": "metadata",
                "n_unique": 1,
                "examples": ["2000"],
            },
            {"name": "perturbagen", "dtype": "categorical", "role": "perturbagen"},
            {
                "name": "cytokine_concentration_ng_ml",
                "dtype": "float",
                "role": "metadata",
                "examples": ["0", "50"],
            },
            {"name": "protein", "dtype": "categorical", "role": "protein", "n_unique": 21},
            {"name": "response_value", "dtype": "float", "role": "value"},
        ],
        detected_axes={
            "donor": "donor",
            "stimulation": "stimulation",
            "perturbagen": "perturbagen",
            "protein": "protein",
            "value": "response_value",
        },
    )


def _require_demo_dataset(project: dict[str, Any], dataset_id: str) -> dict[str, Any]:
    datasets = project.get("datasets")
    if not isinstance(datasets, list):
        raise ToolExecutionError("internal_error", "project state is missing datasets.")
    for dataset in datasets:
        if isinstance(dataset, dict) and dataset.get("id") == dataset_id:
            if dataset.get("source") != "selected_public":
                raise ToolExecutionError("invalid_input", "v0.1 supports selected_public only.")
            return dataset
    raise ToolExecutionError("not_found", f"dataset not found: {dataset_id}")


def _fixture_row_count(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _row in csv.DictReader(handle))


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


def _attach_evidence_handler(
    tool_input: BaseModel,
    context: ToolContext,
) -> EvidenceAttachmentOutput:
    typed_input = AttachEvidenceInput.model_validate(tool_input)
    if not typed_input.chunk_ids:
        raise ToolExecutionError("invalid_input", "attach_evidence requires at least one chunk_id.")
    valid_chunk_ids = _retrieved_cited_chunk_ids(context, project_id=typed_input.project_id)
    unknown_chunk_ids = sorted(set(typed_input.chunk_ids) - valid_chunk_ids)
    if unknown_chunk_ids:
        raise ToolExecutionError(
            "invalid_input",
            "evidence chunks were not retrieved from approved cited corpus results: "
            f"{unknown_chunk_ids}",
        )
    attachment = {
        "id": new_id(EntityPrefix.EVIDENCE_ATTACHMENT),
        "schema_version": SCHEMA_VERSION,
        "project_id": typed_input.project_id,
        "chunk_ids": list(typed_input.chunk_ids),
        "supports_report_id": typed_input.supports_report_id,
        "note": "Attached deterministic corpus evidence for the IL-10/LPS demo report.",
    }
    _ATTACHMENTS[attachment["id"]] = attachment
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

    attached_chunk_ids = _attached_chunk_ids(
        context=context,
        project_id=typed_input.project_id,
        attachment_ids=typed_input.attachment_ids or [],
    )
    if not attached_chunk_ids:
        raise ToolExecutionError(
            "invalid_input",
            "export_report requires attached cited evidence for source-derived claims.",
        )

    top_row = result["ranking"]["rows"][0]
    unique_chunk_ids = sorted(set(attached_chunk_ids))
    claims = [
        {
            "text": (
                f"{top_row['protein']} is the top-ranked protein by absolute paired effect "
                f"size in the fixture-derived IL-10 versus control comparison."
            ),
            "kind": "data-derived",
            "evidence_chunk_ids": [],
        },
        {
            "text": (
                "Retrieved approved corpus sources support the report context for the public "
                "Perturb-PBMC subset, nELISA assay, LPS-stimulated PBMC response, and IL-10."
            ),
            "kind": "source-derived",
            "evidence_chunk_ids": unique_chunk_ids,
        },
        {
            "text": (
                "The result is reported as an IL-10-associated dampening pattern in this "
                "fixture, not as a demonstrated molecular mechanism."
            ),
            "kind": "interpretive",
            "evidence_chunk_ids": unique_chunk_ids,
        },
        {
            "text": "Small paired donor count and exploratory p-values/q-values limit inference.",
            "kind": "limitation",
            "evidence_chunk_ids": [],
        },
    ]
    report_id = new_id(EntityPrefix.REPORT_ARTIFACT)
    markdown_ref = _write_report_markdown(
        context=context,
        project_id=typed_input.project_id,
        report_id=report_id,
        markdown=_report_markdown(top_row=top_row, claims=claims),
    )
    report = {
        "id": report_id,
        "schema_version": SCHEMA_VERSION,
        "project_id": typed_input.project_id,
        "markdown_ref": markdown_ref,
        "claims": claims,
    }
    _REPORTS[report_id] = report
    return ReportArtifactOutput.model_validate(report)


def _attached_chunk_ids(
    *,
    context: ToolContext,
    project_id: str,
    attachment_ids: list[str],
) -> list[str]:
    valid_chunk_ids = _retrieved_cited_chunk_ids(context, project_id=project_id)
    chunk_ids: list[str] = []
    for attachment_id in attachment_ids:
        attachment = _ATTACHMENTS.get(attachment_id)
        if attachment is None:
            raise ToolExecutionError("not_found", f"evidence attachment not found: {attachment_id}")
        if attachment["project_id"] != project_id:
            raise ToolExecutionError(
                "invalid_input",
                "attachment_id does not belong to the requested project_id.",
            )
        unknown_chunk_ids = sorted(set(attachment["chunk_ids"]) - valid_chunk_ids)
        if unknown_chunk_ids:
            raise ToolExecutionError(
                "invalid_input",
                "evidence attachment contains chunks that were not retrieved from approved "
                f"cited corpus results: {unknown_chunk_ids}",
            )
        chunk_ids.extend(attachment["chunk_ids"])
    return chunk_ids


def _retrieved_cited_chunk_ids(context: ToolContext, *, project_id: str) -> set[str]:
    traces = getattr(context.trace_sink, "traces", None)
    if not isinstance(traces, list):
        return set()
    chunk_ids: set[str] = set()
    for trace in traces:
        if trace.project_id != project_id or trace.tool_name != "search_corpus":
            continue
        if trace.status != "ok" or not isinstance(trace.output, dict):
            continue
        chunks = trace.output.get("chunks")
        if not isinstance(chunks, list):
            continue
        for chunk in chunks:
            if not isinstance(chunk, dict):
                continue
            metadata = chunk.get("metadata")
            evidence_chunk = chunk.get("chunk")
            if not isinstance(metadata, dict) or not isinstance(evidence_chunk, dict):
                continue
            citation = evidence_chunk.get("citation")
            chunk_id = evidence_chunk.get("id")
            if (
                isinstance(chunk_id, str)
                and metadata.get("approved_for_claims") is True
                and isinstance(citation, dict)
                and (citation.get("url") or citation.get("doi"))
            ):
                chunk_ids.add(chunk_id)
    return chunk_ids


def _run_eval_suite_handler(tool_input: BaseModel, _context: ToolContext) -> EvalRunOutput:
    typed_input = RunEvalSuiteInput.model_validate(tool_input)
    mode: Literal["smoke", "full"] = "full" if typed_input.suite == "full" else "smoke"
    runner = importlib.import_module("evals.runners.runner")
    report = runner.run_eval_suite(mode)
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
        trace_step_ids=trace_step_ids,
    )


def _get_trace_handler(tool_input: BaseModel, context: ToolContext) -> GetTraceOutput:
    typed_input = GetTraceInput.model_validate(tool_input)
    traces = getattr(context.trace_sink, "traces", None)
    if not isinstance(traces, list):
        return GetTraceOutput(traces=[])
    return GetTraceOutput(
        traces=[
            trace.model_dump(mode="json")
            for trace in traces
            if trace.project_id == typed_input.project_id
            and (typed_input.kind is None or trace.tool_name == typed_input.kind)
        ]
    )


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
    return EvidenceChunkListOutput(
        chunks=[_scored_evidence_chunk_output(chunk) for chunk in chunks]
    )


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


def _report_markdown(*, top_row: dict[str, Any], claims: list[dict[str, Any]]) -> str:
    claim_lines = "\n".join(f"- {claim['kind']}: {claim['text']}" for claim in claims)
    return (
        "# IL-10/LPS fixture report\n\n"
        f"Top ranked protein: {top_row['protein']} "
        f"({top_row['effect_size']:.6g}, {top_row['direction']}).\n\n"
        "## Claims\n"
        f"{claim_lines}\n"
    )


def _write_report_markdown(
    *,
    context: ToolContext,
    project_id: str,
    report_id: str,
    markdown: str,
) -> dict[str, Any]:
    relative = Path("reports") / f"{report_id}.md"
    path = _project_root(context, project_id) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return {
        "uri": f"project://{project_id}/{relative.as_posix()}",
        "media_type": "text/markdown",
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
