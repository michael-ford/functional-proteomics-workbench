"""Seed the deterministic v0.1 demo project state.

The committed fixture is the approved SPEC-006 direct Perturb-PBMC subset. This
script validates the fixture and writes an inspectable local project tree under
``.fpw_state/projects/proj_demo`` by default.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shared_schemas import (
    ArtifactRef,
    ColumnProfile,
    Dataset,
    DatasetSchemaProfile,
    DatasetValidation,
    ExperimentAxes,
    Project,
    ValidationIssue,
)


SCHEMA_VERSION = "0.1.0"
PROJECT_ID = "proj_demo"
DATASET_ID = "ds_01KCYAG0000000000000000000"
SCHEMA_PROFILE_ID = "sp_01KCYAG0000000000000000000"
SEEDED_AT = datetime(2026, 6, 24, 0, 0, 0, tzinfo=UTC)

SOURCE_REPO = "https://github.com/nplexbio/nELISA-PBMC"
SOURCE_COMMIT = "c26223a1d29a1efbdb6577160fab2a323fb7d80d"
SOURCE_FILE = "figure 4/data_pgmc_umap.h5ad"
SOURCE_FILE_SHA256 = "eaf448510a429797a9ca2d8f2581c13573e90868c8190edbbe4a4e209df51500"

RAW_FIXTURE_NAME = "nelisa_pbmc_il10_lps_subset.csv"
NORMALIZED_FIXTURE_NAME = "nelisa_pbmc_il10_lps_long.parquet"
PROVENANCE_NAME = "provenance.json"

REQUIRED_COLUMNS = (
    "sample_id",
    "donor",
    "stimulation",
    "stimulus_concentration_ng_ml",
    "perturbagen",
    "cytokine_concentration_ng_ml",
    "protein",
    "response_value",
)
EXPECTED_DONORS = {f"donor_{index}" for index in range(1, 7)}
EXPECTED_PERTURBAGENS = {"IL-10", "control"}
PROTEIN_PANEL = (
    "TNF alpha",
    "IL-1 beta",
    "IL-1 alpha",
    "IL-6",
    "IL-12 p40",
    "IFN gamma",
    "CCL1",
    "CCL2",
    "CCL22",
    "CCL24",
    "CCL5",
    "CCL7",
    "CCL8",
    "CXCL1",
    "CXCL10",
    "CXCL16",
    "G-CSF",
    "GM-CSF",
    "IL-1 RA RN",
    "TNF RII",
    "MMP-1",
)


@dataclass(frozen=True)
class SeedSummary:
    project_id: str
    project_dir: Path
    dataset_id: str
    row_count: int
    raw_sha256: str
    normalized_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_dir": str(self.project_dir),
            "dataset_id": self.dataset_id,
            "row_count": self.row_count,
            "raw_sha256": self.raw_sha256,
            "normalized_sha256": self.normalized_sha256,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed the deterministic demo project.")
    parser.add_argument(
        "--state-root",
        type=Path,
        default=Path(".fpw_state"),
        help="Root directory for local project state.",
    )
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=Path("demo_data"),
        help="Root directory containing raw/ and processed/ demo fixture files.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate the committed fixture without writing project state.",
    )
    args = parser.parse_args(argv)

    summary = seed_demo_project(
        state_root=args.state_root,
        fixture_root=args.fixture_root,
        check_only=args.check_only,
    )
    print(json.dumps(summary.as_dict(), indent=2, sort_keys=True))
    return 0


def seed_demo_project(
    *,
    state_root: Path = Path(".fpw_state"),
    fixture_root: Path = Path("demo_data"),
    check_only: bool = False,
) -> SeedSummary:
    fixture_root = fixture_root.resolve()
    state_root = state_root.resolve()
    raw_path = fixture_root / "raw" / RAW_FIXTURE_NAME
    normalized_path = fixture_root / "processed" / NORMALIZED_FIXTURE_NAME
    provenance_path = fixture_root / "raw" / PROVENANCE_NAME

    validation = validate_demo_fixture(raw_path, provenance_path)
    if validation.status != "passed":
        details = ", ".join(f"{issue.code}:{issue.column or '-'}" for issue in validation.issues)
        raise SystemExit(f"demo fixture validation failed: {details}")
    if not normalized_path.exists():
        raise SystemExit(f"missing normalized fixture: {normalized_path}")

    raw_sha256 = sha256_file(raw_path)
    normalized_sha256 = sha256_file(normalized_path)
    project_dir = state_root / "projects" / PROJECT_ID
    if not check_only:
        _write_project_tree(
            project_dir=project_dir,
            raw_path=raw_path,
            normalized_path=normalized_path,
            provenance_path=provenance_path,
            validation=validation,
            raw_sha256=raw_sha256,
            normalized_sha256=normalized_sha256,
        )

    return SeedSummary(
        project_id=PROJECT_ID,
        project_dir=project_dir,
        dataset_id=DATASET_ID,
        row_count=validation.row_count or 0,
        raw_sha256=raw_sha256,
        normalized_sha256=normalized_sha256,
    )


def validate_demo_fixture(raw_path: Path, provenance_path: Path) -> DatasetValidation:
    issues: list[ValidationIssue] = []
    rows = _read_fixture_rows(raw_path, issues)
    if rows:
        _validate_fixture_rows(rows, issues)
    _validate_provenance(provenance_path, row_count=len(rows), issues=issues)
    return DatasetValidation(
        status="failed" if issues else "passed",
        row_count=len(rows),
        issues=issues,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_project_tree(
    *,
    project_dir: Path,
    raw_path: Path,
    normalized_path: Path,
    provenance_path: Path,
    validation: DatasetValidation,
    raw_sha256: str,
    normalized_sha256: str,
) -> None:
    tmp_dir = project_dir.with_name(f".{project_dir.name}.tmp")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    raw_dir = tmp_dir / "datasets" / "raw"
    normalized_dir = tmp_dir / "datasets" / "normalized"
    raw_dir.mkdir(parents=True)
    normalized_dir.mkdir(parents=True)

    shutil.copyfile(raw_path, raw_dir / RAW_FIXTURE_NAME)
    shutil.copyfile(provenance_path, raw_dir / PROVENANCE_NAME)
    shutil.copyfile(normalized_path, normalized_dir / NORMALIZED_FIXTURE_NAME)

    project = Project(
        id=PROJECT_ID,
        schema_version=SCHEMA_VERSION,
        title="v0.1 Perturb-PBMC IL-10/LPS demo",
        status="validated",
        context_md=(
            "Seeded v0.1 demo project for IL-10 vs matched no-cytokine control "
            "under LPS 2000 ng/mL using the approved public Perturb-PBMC subset."
        ),
        created_at=SEEDED_AT,
        updated_at=SEEDED_AT,
    )
    dataset = Dataset(
        id=DATASET_ID,
        project_id=PROJECT_ID,
        schema_version=SCHEMA_VERSION,
        name="Perturb-PBMC IL-10/LPS direct subset",
        source="selected_public",
        raw_ref=ArtifactRef(
            uri=f"project://{PROJECT_ID}/datasets/raw/{RAW_FIXTURE_NAME}",
            media_type="text/csv",
            bytes=raw_path.stat().st_size,
            sha256=raw_sha256,
        ),
        normalized_ref=ArtifactRef(
            uri=f"project://{PROJECT_ID}/datasets/normalized/{NORMALIZED_FIXTURE_NAME}",
            media_type="application/parquet",
            bytes=normalized_path.stat().st_size,
            sha256=normalized_sha256,
        ),
        validation=validation,
        created_at=SEEDED_AT,
    )
    schema_profile = _schema_profile_for_fixture()

    _write_json(tmp_dir / "project.json", project.model_dump(mode="json"))
    _write_text(tmp_dir / "context.md", project.context_md or "")
    _write_json(tmp_dir / "datasets" / "dataset.json", dataset.model_dump(mode="json"))
    _write_json(
        tmp_dir / "datasets" / "schema_profile.json",
        schema_profile.model_dump(mode="json"),
    )
    _write_json(tmp_dir / "datasets" / "validation.json", validation.model_dump(mode="json"))
    _write_json(
        tmp_dir / "seed_manifest.json",
        {
            "project_id": PROJECT_ID,
            "dataset_id": DATASET_ID,
            "schema_profile_id": SCHEMA_PROFILE_ID,
            "seeded_at": SEEDED_AT.isoformat().replace("+00:00", "Z"),
            "source_repo": SOURCE_REPO,
            "source_commit": SOURCE_COMMIT,
            "source_file": SOURCE_FILE,
            "source_file_sha256": SOURCE_FILE_SHA256,
            "artifact_refs": [
                f"project://{PROJECT_ID}/datasets/raw/{RAW_FIXTURE_NAME}",
                f"project://{PROJECT_ID}/datasets/raw/{PROVENANCE_NAME}",
                f"project://{PROJECT_ID}/datasets/normalized/{NORMALIZED_FIXTURE_NAME}",
            ],
        },
    )

    project_dir.parent.mkdir(parents=True, exist_ok=True)
    if project_dir.exists():
        shutil.rmtree(project_dir)
    tmp_dir.rename(project_dir)


def _schema_profile_for_fixture() -> DatasetSchemaProfile:
    columns = [
        ColumnProfile(
            name="sample_id",
            dtype="string",
            role="metadata",
            n_unique=114,
            examples=["266", "267", "268"],
        ),
        ColumnProfile(
            name="donor",
            dtype="categorical",
            role="donor",
            n_unique=6,
            examples=["donor_1", "donor_2", "donor_3"],
        ),
        ColumnProfile(
            name="stimulation",
            dtype="categorical",
            role="stimulation",
            n_unique=1,
            examples=["LPS"],
        ),
        ColumnProfile(
            name="stimulus_concentration_ng_ml",
            dtype="float",
            role="metadata",
            n_unique=1,
            examples=["2000.0"],
        ),
        ColumnProfile(
            name="perturbagen",
            dtype="categorical",
            role="perturbagen",
            n_unique=2,
            examples=["IL-10", "control"],
        ),
        ColumnProfile(
            name="cytokine_concentration_ng_ml",
            dtype="float",
            role="metadata",
            n_unique=2,
            examples=["50.0", "0.0"],
        ),
        ColumnProfile(
            name="protein",
            dtype="categorical",
            role="protein",
            n_unique=len(PROTEIN_PANEL),
            examples=list(PROTEIN_PANEL[:3]),
        ),
        ColumnProfile(
            name="response_value",
            dtype="float",
            role="value",
            n_unique=None,
            examples=["0.0"],
        ),
    ]
    return DatasetSchemaProfile(
        id=SCHEMA_PROFILE_ID,
        schema_version=SCHEMA_VERSION,
        dataset_id=DATASET_ID,
        layout="long",
        columns=columns,
        detected_axes=ExperimentAxes(
            donor="donor",
            stimulation="stimulation",
            perturbagen="perturbagen",
            protein="protein",
            value="response_value",
        ),
    )


def _read_fixture_rows(raw_path: Path, issues: list[ValidationIssue]) -> list[dict[str, str]]:
    if not raw_path.exists():
        issues.append(
            ValidationIssue(
                severity="error",
                code="SCHEMA_MISSING_COLUMN",
                message=f"fixture file does not exist: {raw_path}",
            )
        )
        return []

    with raw_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
        for column in missing:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="SCHEMA_MISSING_COLUMN",
                    message=f"required column {column!r} is missing",
                    column=column,
                )
            )
        if missing:
            return []
        return list(reader)


def _validate_fixture_rows(rows: list[dict[str, str]], issues: list[ValidationIssue]) -> None:
    donors: set[str] = set()
    perturbagens: set[str] = set()
    proteins: set[str] = set()
    samples_by_donor_group: dict[tuple[str, str], set[str]] = {}
    sample_ids: set[str] = set()
    sample_protein_pairs: set[tuple[str, str]] = set()

    for row_number, row in enumerate(rows, start=2):
        donor = row["donor"]
        perturbagen = row["perturbagen"]
        protein = row["protein"]
        sample_id = row["sample_id"]
        donors.add(donor)
        perturbagens.add(perturbagen)
        proteins.add(protein)
        sample_ids.add(sample_id)
        sample_protein_pairs.add((sample_id, protein))
        samples_by_donor_group.setdefault((donor, perturbagen), set()).add(sample_id)

        if donor not in EXPECTED_DONORS:
            _append_once(
                issues,
                "UNEXPECTED_CATEGORY",
                f"unexpected donor {donor!r} at row {row_number}",
                "donor",
            )
        if row["stimulation"] != "LPS":
            _append_once(
                issues,
                "UNEXPECTED_CATEGORY",
                f"unexpected stimulation {row['stimulation']!r} at row {row_number}",
                "stimulation",
            )
        if _parse_float(row["stimulus_concentration_ng_ml"]) != 2000.0:
            _append_once(
                issues,
                "UNEXPECTED_CATEGORY",
                "stimulus_concentration_ng_ml must be 2000.0 for every row",
                "stimulus_concentration_ng_ml",
            )
        if perturbagen not in EXPECTED_PERTURBAGENS:
            _append_once(
                issues,
                "UNEXPECTED_CATEGORY",
                f"unexpected perturbagen {perturbagen!r} at row {row_number}",
                "perturbagen",
            )
        expected_cytokine_concentration = 50.0 if perturbagen == "IL-10" else 0.0
        if _parse_float(row["cytokine_concentration_ng_ml"]) != expected_cytokine_concentration:
            _append_once(
                issues,
                "UNEXPECTED_CATEGORY",
                "cytokine concentration does not match perturbagen",
                "cytokine_concentration_ng_ml",
            )
        if protein not in PROTEIN_PANEL:
            _append_once(
                issues,
                "PROTEIN_NOT_IN_PANEL",
                f"protein {protein!r} is not in the frozen panel",
                "protein",
            )
        response_value = _parse_float(row["response_value"])
        if response_value is None or not math.isfinite(response_value):
            _append_once(
                issues,
                "NULL_VALUE",
                "response_value must be finite and non-null",
                "response_value",
            )

    if donors != EXPECTED_DONORS:
        _append_once(
            issues,
            "MISSING_GROUP_FOR_DONOR",
            "fixture must contain exactly donor_1 through donor_6",
            "donor",
        )
    if not EXPECTED_PERTURBAGENS.issubset(perturbagens):
        _append_once(
            issues,
            "MISSING_GROUP_FOR_DONOR",
            "fixture must contain both IL-10 and control perturbagens",
            "perturbagen",
        )
    missing_panel = set(PROTEIN_PANEL) - proteins
    if missing_panel:
        _append_once(
            issues,
            "PROTEIN_NOT_IN_PANEL",
            f"fixture is missing panel proteins: {sorted(missing_panel)}",
            "protein",
        )

    for donor in sorted(EXPECTED_DONORS):
        for perturbagen in sorted(EXPECTED_PERTURBAGENS):
            if not samples_by_donor_group.get((donor, perturbagen)):
                _append_once(
                    issues,
                    "MISSING_GROUP_FOR_DONOR",
                    f"{donor} is missing {perturbagen} samples",
                    "donor",
                )

    expected_row_count = len(sample_ids) * len(PROTEIN_PANEL)
    if len(rows) != expected_row_count or len(sample_protein_pairs) != expected_row_count:
        _append_once(
            issues,
            "SCHEMA_MISSING_COLUMN",
            "fixture must be rectangular: one row per sample/protein pair",
        )


def _validate_provenance(
    provenance_path: Path,
    *,
    row_count: int,
    issues: list[ValidationIssue],
) -> None:
    if not provenance_path.exists():
        issues.append(
            ValidationIssue(
                severity="error",
                code="SCHEMA_MISSING_COLUMN",
                message=f"provenance file does not exist: {provenance_path}",
            )
        )
        return

    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    expected = {
        "source_repo": SOURCE_REPO,
        "source_commit": SOURCE_COMMIT,
        "source_file": SOURCE_FILE,
        "source_file_sha256": SOURCE_FILE_SHA256,
        "value_type": "normalized_response",
    }
    for key, value in expected.items():
        if provenance.get(key) != value:
            _append_once(
                issues,
                "UNEXPECTED_CATEGORY",
                f"provenance {key} must be {value!r}",
                key,
            )
    if provenance.get("row_count") != row_count:
        _append_once(
            issues,
            "UNEXPECTED_CATEGORY",
            "provenance row_count must match the fixture row count",
            "row_count",
        )
    selection = provenance.get("selection", {})
    if tuple(selection.get("proteins", ())) != PROTEIN_PANEL:
        _append_once(
            issues,
            "PROTEIN_NOT_IN_PANEL",
            "provenance selection.proteins must match the frozen panel",
            "selection.proteins",
        )


def _append_once(
    issues: list[ValidationIssue],
    code: str,
    message: str,
    column: str | None = None,
) -> None:
    if any(issue.code == code and issue.column == column for issue in issues):
        return
    issues.append(ValidationIssue(severity="error", code=code, message=message, column=column))


def _parse_float(value: str) -> float | None:
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
