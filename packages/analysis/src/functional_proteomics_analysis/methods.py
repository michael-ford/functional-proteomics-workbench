"""Approved v0.1 analysis path for the demo comparison.

The package is intentionally narrow. It implements only the STAT-001 approved
method path: donor-aware paired differences over the selected Perturb-PBMC
fixture, with donor/protein control rows collapsed by median before pairing.
"""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from itertools import product
from statistics import mean, median
from typing import Any

DEFAULT_METHOD_ID = "donor_aware_paired_difference"
VALUE_COLUMN = "response_value"
DONOR_COLUMN = "donor"
PROTEIN_COLUMN = "protein"
PERTURBAGEN_COLUMN = "perturbagen"
STIMULATION_COLUMN = "stimulation"

REQUIRED_COLUMNS = frozenset(
    {
        "sample_id",
        DONOR_COLUMN,
        STIMULATION_COLUMN,
        "stimulus_concentration_ng_ml",
        PERTURBAGEN_COLUMN,
        "cytokine_concentration_ng_ml",
        PROTEIN_COLUMN,
        VALUE_COLUMN,
    }
)

DONOR_HANDLING = (
    "Matched donors are the biological replicate unit. For each donor/protein, "
    "matched control rows are collapsed with the median before computing the "
    "IL-10 minus control paired difference."
)
REPLICATE_HANDLING = (
    "Multiple control samples per donor/protein are technical or matched-condition "
    "rows for v0.1 and are collapsed by median; they are not treated as independent "
    "biological replicates."
)
MULTIPLE_TESTING = (
    "Exact paired sign-flip p-values are reported as exploratory outputs and "
    "Benjamini-Hochberg q-values are computed across the tested proteins."
)
LIMITATIONS = [
    "Small paired donor count limits inferential power; p-values and q-values are exploratory.",
    "The method summarizes donor-matched response_value differences and does not make "
    "mechanistic claims.",
    "The fixture carries the public H5AD normalized_response values verbatim; v0.1 does "
    "not renormalize.",
    "Only the approved IL-10 versus matched no-cytokine control comparison under LPS is supported.",
]
ASSUMPTIONS = [
    "Rows are the frozen long-format Perturb-PBMC fixture with finite response_value values.",
    "Each included donor has at least one treatment and one matched control row per protein.",
    "Donor-paired differences, not row-level observations, are the units used for "
    "exploratory inference.",
]


class AnalysisValidationError(ValueError):
    """Raised when a requested analysis falls outside the approved v0.1 path."""


@dataclass(frozen=True)
class ComparisonRequest:
    group_a: dict[str, str]
    group_b: dict[str, str]
    stimulation_context: str | None = None
    paired_by: str | None = DONOR_COLUMN
    proteins: list[str] | None = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> ComparisonRequest:
        return cls(
            group_a=_string_dict(payload.get("group_a"), field="group_a"),
            group_b=_string_dict(payload.get("group_b"), field="group_b"),
            stimulation_context=_optional_string(payload.get("stimulation_context")),
            paired_by=_optional_string(payload.get("paired_by")) or DONOR_COLUMN,
            proteins=_optional_string_list(payload.get("proteins"), field="proteins"),
        )


@dataclass(frozen=True)
class ProteinResult:
    protein: str
    effect_size: float
    direction: str
    p_value: float
    q_value: float
    donor_consistency: float
    donor_count: int
    donor_differences: dict[str, float]


@dataclass(frozen=True)
class AnalysisOutput:
    method_id: str
    rows: list[ProteinResult]
    donor_consistency: list[dict[str, Any]]
    donor_handling: str
    replicate_handling: str
    multiple_testing: str
    limitations: list[str]


def load_long_csv(path: str) -> list[dict[str, str]]:
    """Load a contract long-format fixture CSV."""

    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def build_default_analysis_plan(comparison: ComparisonRequest) -> dict[str, Any]:
    """Return the auditable plan text for the only approved v0.1 method."""

    validate_supported_comparison(comparison)
    return {
        "method_id": DEFAULT_METHOD_ID,
        "rationale": (
            "The fixture is a matched donor design with repeated controls. "
            "The approved v0.1 path compares donor-paired IL-10 and control "
            "responses after collapsing controls per donor/protein."
        ),
        "assumptions": list(ASSUMPTIONS),
        "donor_handling": DONOR_HANDLING,
        "replicate_handling": REPLICATE_HANDLING,
        "multiple_testing": MULTIPLE_TESTING,
        "limitations": list(LIMITATIONS),
        "unsupported_assumptions": [],
    }


def validate_supported_comparison(comparison: ComparisonRequest) -> None:
    """Fail closed for requests outside the STAT-001 approved path."""

    if comparison.paired_by != DONOR_COLUMN:
        raise AnalysisValidationError("v0.1 analysis must be paired_by='donor'.")
    if comparison.stimulation_context not in (None, "LPS"):
        raise AnalysisValidationError("v0.1 analysis supports only stimulation_context='LPS'.")
    if comparison.group_a != {PERTURBAGEN_COLUMN: "IL-10"}:
        raise AnalysisValidationError("group_a must be {'perturbagen': 'IL-10'}.")
    if comparison.group_b != {PERTURBAGEN_COLUMN: "control"}:
        raise AnalysisValidationError("group_b must be {'perturbagen': 'control'}.")


def run_donor_aware_paired_difference(
    rows: Iterable[Mapping[str, Any]],
    comparison: ComparisonRequest,
) -> AnalysisOutput:
    """Run the approved paired-difference method over long-format rows."""

    validate_supported_comparison(comparison)
    typed_rows = [_normalize_row(row) for row in rows]
    if not typed_rows:
        raise AnalysisValidationError("analysis requires at least one data row.")

    _validate_required_columns(typed_rows[0])
    proteins = sorted({row[PROTEIN_COLUMN] for row in typed_rows})
    if comparison.proteins is not None:
        unknown = sorted(set(comparison.proteins) - set(proteins))
        if unknown:
            raise AnalysisValidationError(f"requested proteins are absent from fixture: {unknown}")
        proteins = list(comparison.proteins)

    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in typed_rows:
        if row[STIMULATION_COLUMN] != "LPS":
            continue
        perturbagen = row[PERTURBAGEN_COLUMN]
        if perturbagen not in {"IL-10", "control"}:
            continue
        protein = row[PROTEIN_COLUMN]
        if protein not in proteins:
            continue
        grouped[(row[DONOR_COLUMN], perturbagen, protein)].append(float(row[VALUE_COLUMN]))

    protein_results: list[ProteinResult] = []
    for protein in proteins:
        donors = sorted(
            donor
            for donor in {key[0] for key in grouped if key[2] == protein}
            if grouped.get((donor, "IL-10", protein)) and grouped.get((donor, "control", protein))
        )
        if not donors:
            raise AnalysisValidationError(f"protein {protein!r} has no matched donor pairs.")

        diffs: dict[str, float] = {}
        for donor in donors:
            treatment = median(grouped[(donor, "IL-10", protein)])
            control = median(grouped[(donor, "control", protein)])
            diffs[donor] = treatment - control

        effect_size = mean(diffs.values())
        direction = "up" if effect_size >= 0 else "down"
        donor_consistency = _donor_consistency(diffs.values(), direction=direction)
        protein_results.append(
            ProteinResult(
                protein=protein,
                effect_size=effect_size,
                direction=direction,
                p_value=exact_sign_flip_p_value(list(diffs.values())),
                q_value=math.nan,
                donor_consistency=donor_consistency,
                donor_count=len(diffs),
                donor_differences=diffs,
            )
        )

    q_values = benjamini_hochberg([row.p_value for row in protein_results])
    ranked_rows = [
        ProteinResult(
            protein=row.protein,
            effect_size=row.effect_size,
            direction=row.direction,
            p_value=row.p_value,
            q_value=q_value,
            donor_consistency=row.donor_consistency,
            donor_count=row.donor_count,
            donor_differences=row.donor_differences,
        )
        for row, q_value in zip(protein_results, q_values, strict=True)
    ]
    ranked_rows.sort(key=lambda row: (-abs(row.effect_size), row.protein))

    return AnalysisOutput(
        method_id=DEFAULT_METHOD_ID,
        rows=ranked_rows,
        donor_consistency=_aggregate_donor_consistency(ranked_rows),
        donor_handling=DONOR_HANDLING,
        replicate_handling=REPLICATE_HANDLING,
        multiple_testing=MULTIPLE_TESTING,
        limitations=list(LIMITATIONS),
    )


def exact_sign_flip_p_value(differences: Sequence[float]) -> float:
    """Exact two-sided paired sign-flip p-value for the mean difference."""

    if not differences:
        raise AnalysisValidationError("sign-flip test requires at least one paired difference.")
    observed = abs(mean(differences))
    magnitudes = [abs(value) for value in differences]
    total = 2 ** len(magnitudes)
    extreme = 0
    for signs in product((-1.0, 1.0), repeat=len(magnitudes)):
        candidate = abs(mean(sign * value for sign, value in zip(signs, magnitudes, strict=True)))
        if candidate >= observed - 1e-12:
            extreme += 1
    return extreme / total


def benjamini_hochberg(p_values: Sequence[float]) -> list[float]:
    """Benjamini-Hochberg adjusted q-values in original order."""

    count = len(p_values)
    if count == 0:
        return []
    order = sorted(range(count), key=lambda index: p_values[index])
    adjusted = [0.0] * count
    running_min = 1.0
    for rank_from_end, index in enumerate(reversed(order), start=1):
        rank = count - rank_from_end + 1
        value = min(1.0, p_values[index] * count / rank)
        running_min = min(running_min, value)
        adjusted[index] = running_min
    return adjusted


def _normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    try:
        normalized[VALUE_COLUMN] = float(normalized[VALUE_COLUMN])
    except (KeyError, TypeError, ValueError) as exc:
        raise AnalysisValidationError("response_value must be finite numeric data.") from exc
    if not math.isfinite(normalized[VALUE_COLUMN]):
        raise AnalysisValidationError("response_value must be finite numeric data.")
    return normalized


def _validate_required_columns(row: Mapping[str, Any]) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(row))
    if missing:
        raise AnalysisValidationError(f"analysis fixture is missing required columns: {missing}")


def _donor_consistency(differences: Iterable[float], *, direction: str) -> float:
    values = list(differences)
    if not values:
        return 0.0
    if direction == "up":
        agreeing = sum(1 for value in values if value >= 0)
    else:
        agreeing = sum(1 for value in values if value <= 0)
    return agreeing / len(values)


def _aggregate_donor_consistency(rows: Sequence[ProteinResult]) -> list[dict[str, Any]]:
    donors = sorted({donor for row in rows for donor in row.donor_differences})
    aggregate: list[dict[str, Any]] = []
    for donor in donors:
        votes = []
        for row in rows:
            diff = row.donor_differences.get(donor)
            if diff is None:
                continue
            votes.append(diff >= 0 if row.direction == "up" else diff <= 0)
        agrees = sum(1 for vote in votes if vote)
        total = len(votes)
        aggregate.append(
            {
                "donor": donor,
                "agrees_with_consensus": total > 0 and agrees / total >= 0.5,
                "note": f"Agrees on {agrees}/{total} ranked protein directions.",
            }
        )
    return aggregate


def _string_dict(value: Any, *, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise AnalysisValidationError(f"{field} must be an object.")
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise AnalysisValidationError(f"{field} must map strings to strings.")
        result[key] = item
    return result


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise AnalysisValidationError("optional string fields must be strings when provided.")
    return value


def _optional_string_list(value: Any, *, field: str) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AnalysisValidationError(f"{field} must be a list of strings when provided.")
    return value
