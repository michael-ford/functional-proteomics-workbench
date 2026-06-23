from shared_schemas import EntityPrefix, Project, is_prefixed_ulid, new_id


def test_new_id_uses_requested_prefix() -> None:
    dataset_id = new_id(EntityPrefix.DATASET)

    assert dataset_id.startswith("ds_")
    assert is_prefixed_ulid(dataset_id, EntityPrefix.DATASET)


def test_project_allows_seeded_demo_id(utc_now) -> None:
    project = Project(
        id="proj_demo",
        schema_version="0.1.0",
        title="Demo",
        status="created",
        created_at=utc_now,
        updated_at=utc_now,
    )

    assert project.id == "proj_demo"
