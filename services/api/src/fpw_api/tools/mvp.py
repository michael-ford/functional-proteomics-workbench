"""MVP tool definitions registered by the shared registry skeleton."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from fpw_api.tools.registry import (
    ToolContext,
    ToolDefinition,
    ToolExecutionError,
    ToolHandler,
    ToolPermissions,
    ToolRegistry,
    TracePolicy,
)

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
    limitations: list[str]


class RunComparisonInput(ProjectInput):
    plan_id: str


class AnalysisResultOutput(ToolModel):
    id: str
    schema_version: str
    project_id: str
    plan_id: str
    method_id: str
    ranking: dict[str, Any]
    table_ref: dict[str, Any]


class RankProteinsInput(ProjectInput):
    result_id: str
    metric: str | None = None


class ProteinRankingOutput(ToolModel):
    rows: list[dict[str, Any]]
    metric: str
    correction: str | None = None


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
        ),
        _tool(
            "run_comparison",
            "Run a supported analysis plan.",
            RunComparisonInput,
            AnalysisResultOutput,
            scope="project",
            mutates_state=True,
        ),
        _tool(
            "rank_proteins",
            "Rank proteins from an analysis result.",
            RankProteinsInput,
            ProteinRankingOutput,
            scope="project",
            mutates_state=False,
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
        handler=_stub_handler(name),
    )


def _stub_handler(name: str) -> ToolHandler:
    def handler(_tool_input: BaseModel, _context: ToolContext) -> BaseModel:
        raise ToolExecutionError(
            "out_of_scope",
            f"{name} is registered but not implemented in the ToolRegistry skeleton.",
        )

    return handler
