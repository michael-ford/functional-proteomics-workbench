"""Pydantic contracts from docs/DATA_CONTRACTS.md."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from shared_schemas.ids import EntityPrefix, validate_prefixed_ulid


PROJECT_ARTIFACT_URI_PATTERN = r"^project://\S+$"


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("created_at", "updated_at", check_fields=False)
    @classmethod
    def _require_utc_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware UTC datetimes")
        return value.astimezone(UTC)


class ArtifactRef(ContractModel):
    uri: str = Field(pattern=PROJECT_ARTIFACT_URI_PATTERN)
    media_type: str
    bytes: int | None = Field(default=None, ge=0)
    sha256: str | None = None

    @field_validator("uri")
    @classmethod
    def _validate_uri(cls, value: str) -> str:
        if not value.startswith("project://") or value == "project://":
            raise ValueError("artifact URI must be project:// storage-adapter URI")
        if any(char.isspace() for char in value):
            raise ValueError("artifact URI must not contain whitespace")
        return value


class Project(ContractModel):
    id: str
    schema_version: str
    title: str
    status: Literal["created", "dataset_pending", "validated", "analyzed", "reported"]
    context_md: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.PROJECT, allow_demo_project=True)


class ValidationIssue(ContractModel):
    severity: Literal["error", "warning"]
    code: str
    message: str
    column: str | None = None


class DatasetValidation(ContractModel):
    status: Literal["pending", "passed", "failed"]
    row_count: int | None = Field(default=None, ge=0)
    issues: list[ValidationIssue] = Field(default_factory=list)


class Dataset(ContractModel):
    id: str
    project_id: str
    schema_version: str
    name: str
    source: Literal["uploaded", "selected_public"]
    raw_ref: ArtifactRef
    normalized_ref: ArtifactRef | None = None
    validation: DatasetValidation
    created_at: datetime

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.DATASET)

    @field_validator("project_id")
    @classmethod
    def _validate_project_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.PROJECT, allow_demo_project=True)


class ColumnProfile(ContractModel):
    name: str
    dtype: Literal["string", "float", "int", "categorical"]
    role: Literal[
        "donor",
        "stimulation",
        "perturbagen",
        "protein",
        "value",
        "metadata",
        "unknown",
    ]
    n_unique: int | None = Field(default=None, ge=0)
    examples: list[str] = Field(default_factory=list)


class ExperimentAxes(ContractModel):
    donor: str | None
    stimulation: str | None
    perturbagen: str | None
    protein: str | None
    value: str | None


class DatasetSchemaProfile(ContractModel):
    id: str
    schema_version: str
    dataset_id: str
    layout: Literal["long", "wide"]
    columns: list[ColumnProfile]
    detected_axes: ExperimentAxes

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.DATASET_SCHEMA_PROFILE)

    @field_validator("dataset_id")
    @classmethod
    def _validate_dataset_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.DATASET)


class ComparisonSpec(ContractModel):
    group_a: dict[str, str]
    group_b: dict[str, str]
    stimulation_context: str | None = None
    paired_by: str | None = None
    proteins: list[str] | None = None


class AnalysisPlan(ContractModel):
    id: str
    schema_version: str
    project_id: str
    dataset_id: str
    method_id: str
    comparison: ComparisonSpec
    rationale: str
    assumptions: list[str]
    donor_handling: str
    replicate_handling: str | None = None
    multiple_testing: str | None = None
    limitations: list[str]
    unsupported_assumptions: list[str] = Field(default_factory=list)
    created_at: datetime

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.ANALYSIS_PLAN)

    @field_validator("project_id")
    @classmethod
    def _validate_project_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.PROJECT, allow_demo_project=True)

    @field_validator("dataset_id")
    @classmethod
    def _validate_dataset_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.DATASET)


class RankedProtein(ContractModel):
    protein: str
    effect_size: float
    direction: Literal["up", "down"]
    p_value: float | None = Field(default=None, ge=0, le=1)
    q_value: float | None = Field(default=None, ge=0, le=1)
    donor_consistency: float | None = Field(default=None, ge=0, le=1)


class ProteinRanking(ContractModel):
    rows: list[RankedProtein]
    metric: str
    correction: str | None = None


class DonorConsistencyRow(ContractModel):
    donor: str
    agrees_with_consensus: bool
    note: str | None = None


class AnalysisResult(ContractModel):
    id: str
    schema_version: str
    project_id: str
    plan_id: str
    method_id: str
    ranking: ProteinRanking
    donor_consistency: list[DonorConsistencyRow] = Field(default_factory=list)
    plot_id: str | None = None
    table_ref: ArtifactRef
    created_at: datetime

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.ANALYSIS_RESULT)

    @field_validator("project_id")
    @classmethod
    def _validate_project_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.PROJECT, allow_demo_project=True)

    @field_validator("plan_id")
    @classmethod
    def _validate_plan_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.ANALYSIS_PLAN)

    @field_validator("plot_id")
    @classmethod
    def _validate_plot_id(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_prefixed_ulid(value, EntityPrefix.PLOT_ARTIFACT)


class PlotArtifact(ContractModel):
    id: str
    schema_version: str
    project_id: str
    result_id: str
    plot_type: Literal["ranked_effect_bar", "volcano", "donor_consistency"]
    spec_ref: ArtifactRef
    image_ref: ArtifactRef | None = None
    created_at: datetime

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.PLOT_ARTIFACT)

    @field_validator("project_id")
    @classmethod
    def _validate_project_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.PROJECT, allow_demo_project=True)

    @field_validator("result_id")
    @classmethod
    def _validate_result_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.ANALYSIS_RESULT)


class EvidenceSource(ContractModel):
    id: str
    schema_version: str
    title: str
    source_type: Literal["paper", "docs", "github", "webpage", "supplement"]
    url: str | None = None
    doi: str | None = None
    license_note: str | None = None

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.EVIDENCE_SOURCE)


class Citation(ContractModel):
    url: str | None = None
    doi: str | None = None
    paper_title: str | None = None
    authors: str | None = None
    year: str | None = None


class EvidenceChunk(ContractModel):
    id: str
    schema_version: str
    source_id: str
    text: str
    section: str | None = None
    entities: list[str] = Field(default_factory=list)
    assay_context: list[str] = Field(default_factory=list)
    citation: Citation
    embedding_status: Literal["pending", "embedded"] = "pending"

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.EVIDENCE_CHUNK)

    @field_validator("source_id")
    @classmethod
    def _validate_source_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.EVIDENCE_SOURCE)


class EvidenceAttachment(ContractModel):
    id: str
    schema_version: str
    project_id: str
    chunk_ids: list[str]
    supports_report_id: str | None = None
    note: str | None = None

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.EVIDENCE_ATTACHMENT)

    @field_validator("project_id")
    @classmethod
    def _validate_project_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.PROJECT, allow_demo_project=True)

    @field_validator("chunk_ids")
    @classmethod
    def _validate_chunk_ids(cls, value: list[str]) -> list[str]:
        for chunk_id in value:
            validate_prefixed_ulid(chunk_id, EntityPrefix.EVIDENCE_CHUNK)
        return value

    @field_validator("supports_report_id")
    @classmethod
    def _validate_supports_report_id(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_prefixed_ulid(value, EntityPrefix.REPORT_ARTIFACT)


class Claim(ContractModel):
    text: str
    kind: Literal["data-derived", "source-derived", "interpretive", "limitation"]
    evidence_chunk_ids: list[str] = Field(default_factory=list)

    @field_validator("evidence_chunk_ids")
    @classmethod
    def _validate_evidence_chunk_ids(cls, value: list[str]) -> list[str]:
        for chunk_id in value:
            validate_prefixed_ulid(chunk_id, EntityPrefix.EVIDENCE_CHUNK)
        return value


class ReportArtifact(ContractModel):
    id: str
    schema_version: str
    project_id: str
    markdown_ref: ArtifactRef
    claims: list[Claim]
    created_at: datetime

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.REPORT_ARTIFACT)

    @field_validator("project_id")
    @classmethod
    def _validate_project_id(cls, value: str) -> str:
        return validate_prefixed_ulid(value, EntityPrefix.PROJECT, allow_demo_project=True)
