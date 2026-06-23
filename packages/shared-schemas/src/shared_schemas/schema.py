"""JSON Schema export for TypeScript type generation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic.json_schema import models_json_schema

from shared_schemas.models import (
    AnalysisPlan,
    AnalysisResult,
    ArtifactRef,
    Citation,
    Claim,
    ColumnProfile,
    ComparisonSpec,
    Dataset,
    DatasetSchemaProfile,
    DatasetValidation,
    DonorConsistencyRow,
    EvidenceAttachment,
    EvidenceChunk,
    EvidenceSource,
    ExperimentAxes,
    PlotArtifact,
    Project,
    ProteinRanking,
    RankedProtein,
    ReportArtifact,
    ValidationIssue,
)

SCHEMA_MODELS = [
    ArtifactRef,
    Project,
    Dataset,
    DatasetValidation,
    ValidationIssue,
    DatasetSchemaProfile,
    ColumnProfile,
    ExperimentAxes,
    AnalysisPlan,
    ComparisonSpec,
    AnalysisResult,
    ProteinRanking,
    RankedProtein,
    DonorConsistencyRow,
    PlotArtifact,
    EvidenceSource,
    EvidenceChunk,
    Citation,
    EvidenceAttachment,
    ReportArtifact,
    Claim,
]


def combined_json_schema(
    models: Sequence[type] = SCHEMA_MODELS,
) -> dict[str, Any]:
    """Return one schema document containing all exported contract models."""

    _, schema = models_json_schema(
        [(model, "validation") for model in models],
        ref_template="#/$defs/{model}",
        title="SharedSchemas",
        description="Generated JSON Schema for functional proteomics shared contracts.",
    )
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["type"] = "object"
    schema["additionalProperties"] = False
    schema["properties"] = {
        model.__name__: {"$ref": f"#/$defs/{model.__name__}"} for model in models
    }
    return schema
