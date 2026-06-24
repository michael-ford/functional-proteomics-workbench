from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.discover_candidate_papers import build_manifest, main


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = REPO_ROOT / "corpus_discovery" / "il10_lps_config.json"
CACHE_DIR = REPO_ROOT / "corpus_discovery" / "cache" / "il10_lps"


def test_build_manifest_from_cache_is_deterministic() -> None:
    first = build_manifest(config_path=CONFIG, cache_dir=CACHE_DIR, offline=True)
    second = build_manifest(config_path=CONFIG, cache_dir=CACHE_DIR, offline=True)

    assert first == second
    assert first["manifest_id"] == "corpus_candidates_il10_lps_v0"
    assert first["mode"] == "offline-cache"
    assert first["source_cache"]["sha256"]


def test_manifest_filters_ranks_and_caps_candidates() -> None:
    manifest = build_manifest(config_path=CONFIG, cache_dir=CACHE_DIR, offline=True)
    candidates = manifest["candidates"]

    assert candidates
    assert [candidate["rank"] for candidate in candidates] == list(range(1, len(candidates) + 1))
    assert _totals(candidates) == sorted(_totals(candidates), reverse=True)
    assert "10.1007/978-94-015-0788-2_6" not in _dois(candidates)
    assert "10.1038/s41598-026-49474-3" not in _dois(candidates)

    thresholds = manifest["ranking_policy"]["thresholds"]
    for candidate in candidates:
        assert candidate["scores"]["impact"] >= thresholds["min_impact_score"]
        assert candidate["scores"]["relevance"] >= thresholds["min_relevance_score"]
        assert candidate["citations"] >= thresholds["min_citations"]
        assert candidate["doi"]
        assert candidate["matched_entities"]
        assert candidate["matched_terms"]
        assert candidate["why_relevant"].startswith("Best match for")

    caps = {bucket["name"]: bucket["cap"] for bucket in manifest["buckets"]}
    for bucket, cap in caps.items():
        assert sum(1 for candidate in candidates if candidate["best_bucket"] == bucket) <= cap


def test_manifest_contains_expected_il10_lps_mainstays() -> None:
    manifest = build_manifest(config_path=CONFIG, cache_dir=CACHE_DIR, offline=True)
    dois = _dois(manifest["candidates"])

    assert "10.1084/jem.178.3.1041" in dois
    assert "10.1074/jbc.270.16.9558" in dois
    assert "10.1016/1043-4666(92)90062-v" in dois
    assert "10.1038/s41592-025-02861-6" in dois


def test_cli_writes_manifest(tmp_path: Path) -> None:
    output = tmp_path / "manifest.json"

    exit_code = main(
        [
            "--config",
            str(CONFIG),
            "--cache-dir",
            str(CACHE_DIR),
            "--offline",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    manifest = json.loads(output.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "0.1.0"
    assert manifest["candidates"]


def test_offline_mode_requires_cache(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="missing cache for offline run"):
        build_manifest(config_path=CONFIG, cache_dir=tmp_path, offline=True)


def _dois(candidates: list[dict[str, object]]) -> set[str]:
    return {str(candidate["doi"]) for candidate in candidates}


def _totals(candidates: list[dict[str, object]]) -> list[float]:
    return [float(candidate["scores"]["total"]) for candidate in candidates]
