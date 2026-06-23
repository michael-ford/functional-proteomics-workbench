import pytest
from pydantic import ValidationError

from shared_schemas import (
    AnalysisPlan,
    ArtifactRef,
    Claim,
    ComparisonSpec,
    Dataset,
    DatasetValidation,
    RankedProtein,
)


def test_dataset_contract_validates_nested_artifact_refs(utc_now, ulid) -> None:
    dataset = Dataset(
        id=f"ds_{ulid}",
        project_id="proj_demo",
        schema_version="0.1.0",
        name="Perturb-PBMC subset",
        source="selected_public",
        raw_ref=ArtifactRef(
            uri="project://proj_demo/datasets/raw.csv",
            media_type="text/csv",
            bytes=1024,
        ),
        validation=DatasetValidation(status="pending"),
        created_at=utc_now,
    )

    assert dataset.raw_ref.bytes == 1024
    assert dataset.validation.issues == []


def test_id_prefixes_are_validated(utc_now, ulid) -> None:
    with pytest.raises(ValidationError, match="expected ID matching plan_<ULID>"):
        AnalysisPlan(
            id=f"res_{ulid}",
            schema_version="0.1.0",
            project_id="proj_demo",
            dataset_id=f"ds_{ulid}",
            method_id="effect_size_summary",
            comparison=ComparisonSpec(group_a={"perturbagen": "IFNG"}, group_b={"perturbagen": "control"}),
            rationale="A focused comparison.",
            assumptions=[],
            donor_handling="paired by donor",
            limitations=[],
            created_at=utc_now,
        )


def test_model_shape_allows_invariant_checks_outside_pydantic() -> None:
    claim = Claim(text="External evidence claim.", kind="source-derived")

    assert claim.evidence_chunk_ids == []


def test_ranked_protein_rejects_invalid_probability() -> None:
    with pytest.raises(ValidationError):
        RankedProtein(
            protein="IL6",
            effect_size=1.2,
            direction="up",
            p_value=1.5,
        )
