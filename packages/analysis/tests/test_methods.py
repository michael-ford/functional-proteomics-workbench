from __future__ import annotations

from pathlib import Path

import pytest

from functional_proteomics_analysis import (
    DEFAULT_METHOD_ID,
    AnalysisValidationError,
    ComparisonRequest,
    build_default_analysis_plan,
    load_long_csv,
    run_donor_aware_paired_difference,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "demo_data" / "raw" / "nelisa_pbmc_il10_lps_subset.csv"


def test_default_plan_documents_donor_and_limitation_handling() -> None:
    plan = build_default_analysis_plan(_hero_comparison())

    assert plan["method_id"] == DEFAULT_METHOD_ID
    assert "Matched donors" in plan["donor_handling"]
    assert "collapsed by median" in plan["replicate_handling"]
    assert "Benjamini-Hochberg" in plan["multiple_testing"]
    assert any("Small paired donor count" in limitation for limitation in plan["limitations"])


def test_donor_aware_paired_difference_is_deterministic_on_fixture() -> None:
    rows = load_long_csv(str(FIXTURE))

    first = run_donor_aware_paired_difference(rows, _hero_comparison())
    second = run_donor_aware_paired_difference(rows, _hero_comparison())

    assert first == second
    assert first.method_id == DEFAULT_METHOD_ID
    assert len(first.rows) == 21
    assert len(first.donor_consistency) == 6
    assert first.rows[0].protein == "TNF alpha"
    assert first.rows[0].effect_size == pytest.approx(-0.8155901585)
    assert first.rows[0].p_value == pytest.approx(0.03125)
    assert first.rows[0].q_value == pytest.approx(0.036458333333333336)
    assert first.rows[0].donor_consistency == 1.0


def test_controls_are_collapsed_per_donor_not_treated_as_row_replicates() -> None:
    output = run_donor_aware_paired_difference(load_long_csv(str(FIXTURE)), _hero_comparison())
    row = next(result for result in output.rows if result.protein == "TNF alpha")

    assert row.donor_count == 6
    assert sorted(row.donor_differences) == [f"donor_{index}" for index in range(1, 7)]


def test_unsupported_unpaired_assumption_fails_closed() -> None:
    comparison = ComparisonRequest(
        group_a={"perturbagen": "IL-10"},
        group_b={"perturbagen": "control"},
        stimulation_context="LPS",
        paired_by=None,
    )
    # Dataclass default is bypassed by explicit None, matching a malformed caller.
    object.__setattr__(comparison, "paired_by", None)

    with pytest.raises(AnalysisValidationError, match="paired_by='donor'"):
        build_default_analysis_plan(comparison)


def _hero_comparison() -> ComparisonRequest:
    return ComparisonRequest(
        group_a={"perturbagen": "IL-10"},
        group_b={"perturbagen": "control"},
        stimulation_context="LPS",
        paired_by="donor",
    )
