import pytest

from shared_schemas import (
    AnalysisPlan,
    AnalysisResult,
    ArtifactRef,
    Claim,
    ComparisonSpec,
    ContractInvariantError,
    ProteinRanking,
    ReportArtifact,
    validate_analysis_plan_invariants,
    validate_analysis_result_invariants,
    validate_claim_invariants,
    validate_report_artifact_invariants,
)


def _analysis_result(utc_now, ulid, method_id: str) -> AnalysisResult:
    return AnalysisResult(
        id=f"res_{ulid}",
        schema_version="0.1.0",
        project_id="proj_demo",
        plan_id=f"plan_{ulid}",
        method_id=method_id,
        ranking=ProteinRanking(rows=[], metric="effect_size"),
        table_ref=ArtifactRef(
            uri="project://proj_demo/results/diff.csv",
            media_type="text/csv",
        ),
        created_at=utc_now,
    )


def test_source_derived_claim_must_cite_chunk() -> None:
    claim = Claim(text="Prior work supports this.", kind="source-derived")

    with pytest.raises(ContractInvariantError, match="at least one EvidenceChunk"):
        validate_claim_invariants(claim)


def test_source_derived_claim_with_chunk_passes(ulid) -> None:
    claim = Claim(
        text="Prior work supports this.",
        kind="source-derived",
        evidence_chunk_ids=[f"chunk_{ulid}"],
    )

    assert validate_claim_invariants(claim) is claim


def test_report_artifact_checks_claim_invariants(utc_now, ulid) -> None:
    report = ReportArtifact(
        id=f"rep_{ulid}",
        schema_version="0.1.0",
        project_id="proj_demo",
        markdown_ref=ArtifactRef(
            uri="project://proj_demo/reports/report.md",
            media_type="text/markdown",
        ),
        claims=[Claim(text="Unsupported source claim.", kind="source-derived")],
        created_at=utc_now,
    )

    with pytest.raises(ContractInvariantError):
        validate_report_artifact_invariants(report)


def test_analysis_plan_method_id_must_be_supported(utc_now, ulid) -> None:
    plan = AnalysisPlan(
        id=f"plan_{ulid}",
        schema_version="0.1.0",
        project_id="proj_demo",
        dataset_id=f"ds_{ulid}",
        method_id="invented_method",
        comparison=ComparisonSpec(group_a={"perturbagen": "IFNG"}, group_b={"perturbagen": "control"}),
        rationale="A focused comparison.",
        assumptions=[],
        donor_handling="paired by donor",
        limitations=[],
        created_at=utc_now,
    )

    with pytest.raises(ContractInvariantError, match="unsupported method_id"):
        validate_analysis_plan_invariants(plan)


def test_analysis_result_method_id_must_be_supported(utc_now, ulid) -> None:
    result = _analysis_result(utc_now, ulid, method_id="invented_method")

    with pytest.raises(ContractInvariantError, match="unsupported method_id"):
        validate_analysis_result_invariants(result)


def test_analysis_result_plan_must_exist(utc_now, ulid) -> None:
    result = _analysis_result(utc_now, ulid, method_id="effect_size_summary")

    with pytest.raises(ContractInvariantError, match="must exist"):
        validate_analysis_result_invariants(result, existing_plan_ids=set())

    assert (
        validate_analysis_result_invariants(
            result,
            existing_plan_ids={f"plan_{ulid}"},
        )
        is result
    )
