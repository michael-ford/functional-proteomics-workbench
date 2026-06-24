from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from scripts.seed_demo_project import (
    PROJECT_ID,
    RAW_FIXTURE_NAME,
    REQUIRED_COLUMNS,
    seed_demo_project,
    validate_demo_fixture,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "demo_data"


def test_seed_demo_project_is_idempotent(tmp_path: Path) -> None:
    state_root = tmp_path / "state"

    first = seed_demo_project(state_root=state_root, fixture_root=FIXTURE_ROOT)
    first_hashes = _tree_hashes(first.project_dir)
    second = seed_demo_project(state_root=state_root, fixture_root=FIXTURE_ROOT)
    second_hashes = _tree_hashes(second.project_dir)

    assert first.project_id == PROJECT_ID
    assert first.row_count == 2394
    assert first.as_dict() == second.as_dict()
    assert first_hashes == second_hashes

    project = json.loads((first.project_dir / "project.json").read_text(encoding="utf-8"))
    dataset = json.loads(
        (first.project_dir / "datasets" / "dataset.json").read_text(encoding="utf-8")
    )
    assert project["id"] == PROJECT_ID
    assert project["status"] == "validated"
    assert dataset["source"] == "selected_public"
    assert dataset["validation"]["status"] == "passed"
    assert dataset["raw_ref"]["uri"] == (
        f"project://{PROJECT_ID}/datasets/raw/{RAW_FIXTURE_NAME}"
    )


def test_demo_fixture_validation_passes_for_committed_fixture() -> None:
    validation = validate_demo_fixture(
        FIXTURE_ROOT / "raw" / RAW_FIXTURE_NAME,
        FIXTURE_ROOT / "raw" / "provenance.json",
    )

    assert validation.status == "passed"
    assert validation.row_count == 2394
    assert validation.issues == []


@pytest.mark.parametrize(
    ("variant", "expected_code"),
    [
        ("missing_column", "SCHEMA_MISSING_COLUMN"),
        ("unknown_protein", "PROTEIN_NOT_IN_PANEL"),
        ("nan_value", "NULL_VALUE"),
        ("wrong_stimulation", "UNEXPECTED_CATEGORY"),
        ("unbalanced_design", "MISSING_GROUP_FOR_DONOR"),
    ],
)
def test_demo_fixture_validation_reports_contract_failure_codes(
    tmp_path: Path,
    variant: str,
    expected_code: str,
) -> None:
    raw_variant = tmp_path / f"{variant}.csv"
    provenance_variant = tmp_path / "provenance.json"
    _write_variant_csv(variant, raw_variant)
    provenance = json.loads((FIXTURE_ROOT / "raw" / "provenance.json").read_text(encoding="utf-8"))
    if variant == "unbalanced_design":
        provenance["row_count"] = _count_data_rows(raw_variant)
    provenance_variant.write_text(json.dumps(provenance, sort_keys=True), encoding="utf-8")

    validation = validate_demo_fixture(raw_variant, provenance_variant)

    assert validation.status == "failed"
    assert expected_code in {issue.code for issue in validation.issues}


def _tree_hashes(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        hashes[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _write_variant_csv(variant: str, output: Path) -> None:
    rows = _fixture_rows()
    fieldnames = list(REQUIRED_COLUMNS)
    if variant == "missing_column":
        fieldnames.remove("perturbagen")
    elif variant == "unknown_protein":
        rows[0]["protein"] = "not-a-panel-protein"
    elif variant == "nan_value":
        rows[0]["response_value"] = "NaN"
    elif variant == "wrong_stimulation":
        rows[0]["stimulation"] = "PolyIC"
    elif variant == "unbalanced_design":
        rows = [
            row
            for row in rows
            if not (row["donor"] == "donor_1" and row["perturbagen"] == "IL-10")
        ]
    else:
        raise AssertionError(f"unknown variant {variant}")

    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row[column] for column in fieldnames})


def _fixture_rows() -> list[dict[str, str]]:
    with (FIXTURE_ROOT / "raw" / RAW_FIXTURE_NAME).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _count_data_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))
