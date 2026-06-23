"""ULID-backed ID helpers for contract entities."""

from __future__ import annotations

import re
from enum import StrEnum

from ulid import ULID


class EntityPrefix(StrEnum):
    PROJECT = "proj_"
    DATASET = "ds_"
    DATASET_SCHEMA_PROFILE = "sp_"
    ANALYSIS_PLAN = "plan_"
    ANALYSIS_RESULT = "res_"
    PLOT_ARTIFACT = "plot_"
    EVIDENCE_SOURCE = "src_"
    EVIDENCE_CHUNK = "chunk_"
    EVIDENCE_ATTACHMENT = "evd_"
    REPORT_ARTIFACT = "rep_"
    TOOL_CALL_TRACE = "tc_"


ID_PREFIXES: dict[str, EntityPrefix] = {
    "Project": EntityPrefix.PROJECT,
    "Dataset": EntityPrefix.DATASET,
    "DatasetSchemaProfile": EntityPrefix.DATASET_SCHEMA_PROFILE,
    "AnalysisPlan": EntityPrefix.ANALYSIS_PLAN,
    "AnalysisResult": EntityPrefix.ANALYSIS_RESULT,
    "PlotArtifact": EntityPrefix.PLOT_ARTIFACT,
    "EvidenceSource": EntityPrefix.EVIDENCE_SOURCE,
    "EvidenceChunk": EntityPrefix.EVIDENCE_CHUNK,
    "EvidenceAttachment": EntityPrefix.EVIDENCE_ATTACHMENT,
    "ReportArtifact": EntityPrefix.REPORT_ARTIFACT,
    "ToolCallTrace": EntityPrefix.TOOL_CALL_TRACE,
}

_ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")


def _prefix_value(prefix: EntityPrefix | str) -> str:
    return prefix.value if isinstance(prefix, EntityPrefix) else prefix


def new_id(prefix: EntityPrefix | str) -> str:
    """Create a new contract ID using the ``prefix_ULID`` convention."""

    return f"{_prefix_value(prefix)}{ULID()}"


def is_prefixed_ulid(value: str, prefix: EntityPrefix | str) -> bool:
    """Return whether ``value`` matches the requested ``prefix_ULID`` shape."""

    prefix_value = _prefix_value(prefix)
    if not value.startswith(prefix_value):
        return False
    return bool(_ULID_RE.fullmatch(value[len(prefix_value) :]))


def validate_prefixed_ulid(
    value: str,
    prefix: EntityPrefix | str,
    *,
    allow_demo_project: bool = False,
) -> str:
    """Validate a contract ID and return it unchanged."""

    if allow_demo_project and value == "proj_demo":
        return value
    if not is_prefixed_ulid(value, prefix):
        prefix_value = _prefix_value(prefix)
        raise ValueError(f"expected ID matching {prefix_value}<ULID>")
    return value
