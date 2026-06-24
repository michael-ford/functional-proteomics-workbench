from __future__ import annotations

import json

import pytest

from functional_proteomics_corpus import (
    CorpusUnindexedError,
    build_corpus_index,
    load_corpus_index,
    search_corpus_index,
    write_corpus_index,
)
from functional_proteomics_corpus.cli import main


def test_build_corpus_index_is_deterministic_for_fixture_sources(tmp_path) -> None:
    first = build_corpus_index()
    second = build_corpus_index()

    assert first.to_dict() == second.to_dict()
    assert [source.source_id for source in first.sources] == [
        "src_nomic_perturb_pbmc",
        "src_nelisa_pbmc_repo",
        "src_dagher_2025_nelisa",
        "src_dandrea_1993_il10",
        "src_wang_1995_il10_nfkb",
        "src_degroote_1992_pbmc",
        "src_eggesbo_1994_lps_pbmc",
    ]
    assert all(source.content_sha256 for source in first.sources)
    assert all(chunk.citation.url or chunk.citation.doi for chunk in first.chunks)

    first_path = write_corpus_index(first, tmp_path / "first.json")
    second_path = write_corpus_index(second, tmp_path / "second.json")
    assert first_path.read_bytes() == second_path.read_bytes()


@pytest.mark.parametrize(
    ("query", "expected_source_ids"),
    [
        (
            "What public dataset and assay does this demo use?",
            {
                "src_nomic_perturb_pbmc",
                "src_nelisa_pbmc_repo",
                "src_dagher_2025_nelisa",
            },
        ),
        (
            "What evidence supports IL-10 dampening cytokine production in LPS or human "
            "immune-cell contexts?",
            {"src_dandrea_1993_il10", "src_wang_1995_il10_nfkb"},
        ),
        (
            "What context supports LPS-stimulated PBMC cytokine response interpretation?",
            {"src_degroote_1992_pbmc", "src_eggesbo_1994_lps_pbmc"},
        ),
    ],
)
def test_search_corpus_returns_source_grounded_chunks(query, expected_source_ids) -> None:
    results = search_corpus_index(build_corpus_index(), query, k=3)

    assert results
    assert {results[0]["source_id"]} <= expected_source_ids
    assert any(result["source_id"] in expected_source_ids for result in results)
    assert all(result["citation"]["url"] or result["citation"]["doi"] for result in results)
    assert any(result["entities"] for result in results)
    assert all(result["metadata"]["content_sha256"] for result in results)


def test_load_corpus_index_fails_closed_when_unbuilt(tmp_path) -> None:
    with pytest.raises(CorpusUnindexedError, match="corpus index has not been built"):
        load_corpus_index(tmp_path / "missing-index.json")


def test_build_corpus_cli_writes_machine_readable_index(tmp_path) -> None:
    output = tmp_path / "corpus-index.json"

    exit_code = main(["build", "--output", str(output)])

    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["source_manifest_id"] == "corpus_sources_il10_lps_v0"
    assert len(payload["sources"]) == 7
    assert len(payload["chunks"]) >= 7
