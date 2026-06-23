from shared_schemas.schema import combined_json_schema


def test_combined_schema_exports_core_models() -> None:
    schema = combined_json_schema()

    assert schema["$defs"]["Project"]["properties"]["id"]["type"] == "string"
    assert "schema_version" in schema["$defs"]["AnalysisResult"]["required"]
    assert "AnalysisResult" in schema["$defs"]
    assert "ArtifactRef" in schema["$defs"]
    assert schema["properties"]["Claim"]["$ref"] == "#/$defs/Claim"
