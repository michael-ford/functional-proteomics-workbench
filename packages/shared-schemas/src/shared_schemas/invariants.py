"""Cross-field and cross-record contract invariant checks."""

from __future__ import annotations

from collections.abc import Container

from shared_schemas.models import AnalysisPlan, AnalysisResult, Claim, ReportArtifact


SUPPORTED_METHOD_IDS = frozenset(
    {
        "effect_size_summary",
        "donor_aware_paired_difference",
        "simple_group_test",
        "multiple_testing_correction",
        "donor_consistency_score",
    }
)


class ContractInvariantError(ValueError):
    """Raised when an entity is valid JSON shape but violates contract invariants."""


def ensure_supported_method_id(method_id: str) -> str:
    if method_id not in SUPPORTED_METHOD_IDS:
        supported = ", ".join(sorted(SUPPORTED_METHOD_IDS))
        raise ContractInvariantError(
            f"unsupported method_id {method_id!r}; supported values: {supported}"
        )
    return method_id


def validate_claim_invariants(claim: Claim) -> Claim:
    if claim.kind == "source-derived" and len(claim.evidence_chunk_ids) == 0:
        raise ContractInvariantError(
            "source-derived Claim must reference at least one EvidenceChunk"
        )
    return claim


def validate_report_artifact_invariants(report: ReportArtifact) -> ReportArtifact:
    for claim in report.claims:
        validate_claim_invariants(claim)
    return report


def validate_analysis_plan_invariants(plan: AnalysisPlan) -> AnalysisPlan:
    ensure_supported_method_id(plan.method_id)
    return plan


def validate_analysis_result_invariants(
    result: AnalysisResult,
    *,
    existing_plan_ids: Container[str] | None = None,
) -> AnalysisResult:
    ensure_supported_method_id(result.method_id)
    if existing_plan_ids is not None and result.plan_id not in existing_plan_ids:
        raise ContractInvariantError(
            f"AnalysisPlan {result.plan_id!r} must exist before its AnalysisResult"
        )
    return result
