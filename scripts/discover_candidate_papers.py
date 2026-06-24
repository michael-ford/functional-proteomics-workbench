"""Discover and rank candidate papers for the curated corpus source manifest.

The live search path wraps the locally installed ``paper-search`` CLI, while
CI-safe runs operate entirely from committed paper-search-shaped cache files.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "0.1.0"
DEFAULT_CONFIG = Path("corpus_discovery/il10_lps_config.json")
DEFAULT_CACHE_DIR = Path("corpus_discovery/cache/il10_lps")
PAPER_SEARCH_COMMAND = (
    "uv",
    "run",
    "--directory",
    "~/paper-search-mcp",
    "paper-search",
    "search",
)
SOURCE_PRIORITY = {
    "pubmed": 0,
    "pmc": 1,
    "europepmc": 2,
    "semantic": 3,
    "openalex": 4,
    "crossref": 5,
    "unpaywall": 6,
    "biorxiv": 7,
}


@dataclass(frozen=True)
class Bucket:
    name: str
    query: str
    cache_file: str
    semantic_terms: tuple[str, ...]
    required_terms: tuple[str, ...] = ()
    cap: int = 5


@dataclass
class Paper:
    title: str
    authors: str
    abstract: str
    doi: str
    year: int | None
    citation_count: int
    venue: str
    publication_type: str
    url: str
    pdf_url: str
    paper_id: str
    primary_source: str
    sources: set[str] = field(default_factory=set)
    pmids: set[str] = field(default_factory=set)
    source_records: list[dict[str, Any]] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(
            value
            for value in (
                self.title,
                self.abstract,
                self.venue,
                self.publication_type,
            )
            if value
        )


@dataclass(frozen=True)
class BucketRelevance:
    score: float
    matched_entities: tuple[str, ...]
    matched_terms: tuple[str, ...]
    title_matches: tuple[str, ...]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rank candidate corpus papers from paper-search results."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Require existing cache files and never call paper-search.",
    )
    parser.add_argument(
        "--refresh-cache",
        action="store_true",
        help="Call paper-search and overwrite cache files before ranking.",
    )
    args = parser.parse_args(argv)

    manifest = build_manifest(
        config_path=args.config,
        cache_dir=args.cache_dir,
        offline=args.offline,
        refresh_cache=args.refresh_cache,
    )
    encoded = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


def build_manifest(
    *,
    config_path: Path = DEFAULT_CONFIG,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    offline: bool = False,
    refresh_cache: bool = False,
) -> dict[str, Any]:
    config = _read_json(config_path)
    buckets = _load_buckets(config)
    cache_dir = cache_dir.resolve()

    raw_results: dict[str, dict[str, Any]] = {}
    for bucket in buckets:
        cache_path = cache_dir / bucket.cache_file
        if refresh_cache:
            raw_results[bucket.name] = _run_paper_search(bucket, config, cache_path)
        elif cache_path.exists():
            raw_results[bucket.name] = _read_json(cache_path)
        elif offline:
            raise SystemExit(f"missing cache for offline run: {cache_path}")
        else:
            raw_results[bucket.name] = _run_paper_search(bucket, config, cache_path)

    papers, bucket_hits = _dedupe_papers(raw_results, buckets)
    scored = _score_papers(papers, bucket_hits, config, buckets)
    ranked = _filter_and_cap(scored, config, buckets)

    cache_hashes = {
        bucket.name: _sha256_file(cache_dir / bucket.cache_file)
        for bucket in buckets
        if (cache_dir / bucket.cache_file).exists()
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "manifest_id": config["manifest_id"],
        "generated_at": config["as_of"],
        "mode": "offline-cache" if offline and not refresh_cache else "paper-search-cache",
        "paper_search_sources": config["sources"],
        "source_cache": {
            "cache_dir": str(cache_dir),
            "sha256": cache_hashes,
        },
        "hero_comparison": config["hero_comparison"],
        "ranking_policy": _ranking_policy(config),
        "buckets": [
            {
                "name": bucket.name,
                "query": bucket.query,
                "cap": bucket.cap,
                "semantic_terms": list(bucket.semantic_terms),
                "required_terms": list(bucket.required_terms),
            }
            for bucket in buckets
        ],
        "candidates": ranked,
    }


def _load_buckets(config: dict[str, Any]) -> list[Bucket]:
    buckets = []
    for item in config["buckets"]:
        buckets.append(
            Bucket(
                name=item["name"],
                query=item["query"],
                cache_file=item.get("cache_file") or _slugify(item["name"]) + ".json",
                semantic_terms=tuple(item.get("semantic_terms", [])),
                required_terms=tuple(item.get("required_terms", [])),
                cap=int(item.get("cap", config["ranking"]["max_candidates_per_bucket"])),
            )
        )
    return buckets


def _run_paper_search(bucket: Bucket, config: dict[str, Any], cache_path: Path) -> dict[str, Any]:
    cmd = [
        *PAPER_SEARCH_COMMAND,
        bucket.query,
        "-n",
        str(config["search"]["max_per_source"]),
        "-s",
        ",".join(config["sources"]),
    ]
    if year_filter := config["search"].get("year_filter"):
        cmd.extend(["-y", str(year_filter)])

    expanded = [str(Path(part).expanduser()) if part.startswith("~/") else part for part in cmd]
    result = subprocess.run(expanded, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    payload["_cache_metadata"] = {
        "bucket": bucket.name,
        "created_at": datetime.now(tz=UTC).isoformat(),
        "command": expanded,
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _dedupe_papers(
    raw_results: dict[str, dict[str, Any]],
    buckets: list[Bucket],
) -> tuple[dict[str, Paper], dict[str, set[str]]]:
    papers: dict[str, Paper] = {}
    bucket_hits: dict[str, set[str]] = defaultdict(set)
    for bucket in buckets:
        for record in raw_results[bucket.name].get("papers", []):
            paper = _paper_from_record(record)
            if not paper.title:
                continue
            key = _dedupe_key(paper)
            if key in papers:
                _merge_paper(papers[key], paper)
            else:
                papers[key] = paper
            bucket_hits[key].add(bucket.name)
    return papers, bucket_hits


def _paper_from_record(record: dict[str, Any]) -> Paper:
    extra = _parse_extra(record.get("extra", ""))
    published = str(record.get("published_date") or "")
    year_match = re.search(r"\b(19|20)\d{2}\b", published)
    citation_count = _int_or_zero(record.get("citations"))
    if not citation_count:
        citation_count = _int_or_zero(extra.get("citation_count"))
    source = str(record.get("source") or "").lower()
    doi = _normalize_doi(str(record.get("doi") or record.get("paper_id") or ""))
    pmid = str(extra.get("pmid") or "")
    paper_id = str(record.get("paper_id") or "")
    if not pmid and (paper_id.isdigit() or paper_id.upper().startswith("PMID:")):
        pmid = paper_id.upper().replace("PMID:", "")

    return Paper(
        title=_clean_text(record.get("title")),
        authors=_clean_text(record.get("authors")),
        abstract=_clean_text(record.get("abstract")),
        doi=doi,
        year=int(year_match.group(0)) if year_match else None,
        citation_count=citation_count,
        venue=_clean_text(extra.get("container_title") or extra.get("journal")),
        publication_type=_publication_type(record, extra),
        url=str(record.get("url") or ""),
        pdf_url=str(record.get("pdf_url") or ""),
        paper_id=paper_id,
        primary_source=source,
        sources={source} if source else set(),
        pmids={pmid} if pmid else set(),
        source_records=[record],
    )


def _merge_paper(existing: Paper, incoming: Paper) -> None:
    existing.sources.update(incoming.sources)
    existing.pmids.update(incoming.pmids)
    existing.source_records.extend(incoming.source_records)
    if incoming.citation_count > existing.citation_count:
        existing.citation_count = incoming.citation_count
    if not existing.abstract and incoming.abstract:
        existing.abstract = incoming.abstract
    if not existing.doi and incoming.doi:
        existing.doi = incoming.doi
    if not existing.venue and incoming.venue:
        existing.venue = incoming.venue
    if not existing.pdf_url and incoming.pdf_url:
        existing.pdf_url = incoming.pdf_url
    if _source_rank(incoming.primary_source) < _source_rank(existing.primary_source):
        existing.primary_source = incoming.primary_source
        existing.paper_id = incoming.paper_id
        existing.url = incoming.url or existing.url


def _score_papers(
    papers: dict[str, Paper],
    bucket_hits: dict[str, set[str]],
    config: dict[str, Any],
    buckets: list[Bucket],
) -> list[dict[str, Any]]:
    bucket_by_name = {bucket.name: bucket for bucket in buckets}
    scored = []
    for key, paper in papers.items():
        impact_score, impact_details = _impact_score(paper, config)
        bucket_scores = {
            name: _relevance_score(paper, bucket_by_name[name], config)
            for name in sorted(bucket_hits[key])
        }
        best_bucket, best_relevance = max(
            bucket_scores.items(),
            key=lambda item: (item[1].score, item[0]),
        )
        total_score = round(
            config["ranking"]["impact_weight"] * impact_score
            + config["ranking"]["relevance_weight"] * best_relevance.score,
            4,
        )
        scored.append(
            {
                "rank": 0,
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
                "doi": paper.doi,
                "pmids": sorted(paper.pmids),
                "source": paper.primary_source,
                "sources": sorted(paper.sources),
                "paper_id": paper.paper_id,
                "url": paper.url,
                "pdf_url": paper.pdf_url,
                "venue": paper.venue,
                "publication_type": paper.publication_type,
                "citations": paper.citation_count,
                "citation_velocity": impact_details["citation_velocity"],
                "matched_buckets": sorted(bucket_scores),
                "best_bucket": best_bucket,
                "matched_entities": list(best_relevance.matched_entities),
                "matched_terms": list(best_relevance.matched_terms),
                "scores": {
                    "impact": impact_score,
                    "relevance": best_relevance.score,
                    "total": total_score,
                    "impact_details": impact_details,
                },
                "why_relevant": _why_relevant(best_bucket, best_relevance),
            }
        )
    return scored


def _filter_and_cap(
    scored: list[dict[str, Any]],
    config: dict[str, Any],
    buckets: list[Bucket],
) -> list[dict[str, Any]]:
    thresholds = config["ranking"]["thresholds"]
    filtered = [
        item
        for item in scored
        if item["scores"]["impact"] >= thresholds["min_impact_score"]
        and item["scores"]["relevance"] >= thresholds["min_relevance_score"]
        and item["citations"] >= thresholds["min_citations"]
        and (not thresholds.get("require_doi") or item["doi"])
    ]
    filtered.sort(
        key=lambda item: (
            item["scores"]["total"],
            item["scores"]["relevance"],
            item["scores"]["impact"],
            item["citations"],
            item["year"] or 0,
            item["title"],
        ),
        reverse=True,
    )

    selected: list[dict[str, Any]] = []
    selected_keys: set[str] = set()
    bucket_counts: dict[str, int] = defaultdict(int)
    bucket_caps = {bucket.name: bucket.cap for bucket in buckets}
    for item in filtered:
        bucket = item["best_bucket"]
        key = item["doi"] or item["paper_id"] or _normalize_title(item["title"])
        if key in selected_keys or bucket_counts[bucket] >= bucket_caps[bucket]:
            continue
        selected.append(item)
        selected_keys.add(key)
        bucket_counts[bucket] += 1

    for index, item in enumerate(selected, start=1):
        item["rank"] = index
    return selected


def _impact_score(paper: Paper, config: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    as_of_year = int(config["as_of"][:4])
    age = max(1, as_of_year - paper.year + 1) if paper.year else 20
    citation_velocity = round(paper.citation_count / age, 2)
    venue_tiers = {
        _normalize_venue(key): float(value)
        for key, value in config["ranking"].get("venue_tiers", {}).items()
    }
    venue_score = venue_tiers.get(_normalize_venue(paper.venue), 0.35 if paper.venue else 0.25)
    publication_type_score = {
        "primary": 1.0,
        "review": 0.9,
        "preprint": 0.55,
        "proceedings": 0.45,
        "unknown": 0.6,
    }.get(paper.publication_type, 0.6)
    recency_score = _recency_score(age)
    citation_score = min(math.log10(paper.citation_count + 1) / 3.0, 1.0)
    velocity_score = min(citation_velocity / 75.0, 1.0)
    weights = config["ranking"]["impact_components"]
    impact = round(
        weights["citation_count"] * citation_score
        + weights["citation_velocity"] * velocity_score
        + weights["venue"] * venue_score
        + weights["publication_type"] * publication_type_score
        + weights["recency"] * recency_score,
        4,
    )
    return impact, {
        "citation_score": round(citation_score, 4),
        "citation_velocity": citation_velocity,
        "velocity_score": round(velocity_score, 4),
        "venue_score": round(venue_score, 4),
        "publication_type_score": publication_type_score,
        "recency_score": recency_score,
    }


def _relevance_score(paper: Paper, bucket: Bucket, config: dict[str, Any]) -> BucketRelevance:
    text = paper.text
    title = paper.title
    hero_entities = tuple(config["hero_entities"])
    matched_entities = _matched_terms(text, hero_entities)
    matched_bucket_terms = _matched_terms(text, bucket.semantic_terms)
    required_matches = _matched_terms(text, bucket.required_terms)
    title_matches = _matched_terms(title, [*hero_entities, *bucket.semantic_terms])

    entity_score = len(matched_entities) / max(1, len(hero_entities))
    bucket_score = len(matched_bucket_terms) / max(1, len(bucket.semantic_terms))
    required_score = (
        len(required_matches) / max(1, len(bucket.required_terms))
        if bucket.required_terms
        else 1.0
    )
    title_score = min(len(title_matches) / 4.0, 1.0)
    weights = config["ranking"]["relevance_components"]
    score = round(
        weights["hero_entities"] * entity_score
        + weights["bucket_semantic_terms"] * bucket_score
        + weights["required_terms"] * required_score
        + weights["title_match"] * title_score,
        4,
    )
    return BucketRelevance(
        score=score,
        matched_entities=matched_entities,
        matched_terms=matched_bucket_terms,
        title_matches=title_matches,
    )


def _ranking_policy(config: dict[str, Any]) -> dict[str, Any]:
    ranking = config["ranking"]
    return {
        "summary": (
            "Candidates are deduplicated by DOI, PMID, then normalized title; "
            "filtered by explicit impact/relevance/citation thresholds; and capped per topic bucket."
        ),
        "impact_weight": ranking["impact_weight"],
        "relevance_weight": ranking["relevance_weight"],
        "impact_components": ranking["impact_components"],
        "relevance_components": ranking["relevance_components"],
        "thresholds": ranking["thresholds"],
        "definition_of_high_impact_mainstay": (
            "A paper must pass min_impact_score, min_relevance_score, and min_citations. "
            "When require_doi is true, DOI-less records are excluded before capping. "
            "The impact score combines citation count, citation velocity, venue tier, "
            "publication type, and recency; relevance must directly match configured "
            "hero entities and bucket semantic terms."
        ),
    }


def _why_relevant(bucket: str, relevance: BucketRelevance) -> str:
    entity_text = ", ".join(relevance.matched_entities[:6]) or "configured hero entities"
    term_text = ", ".join(relevance.matched_terms[:6]) or "configured bucket terms"
    return f"Best match for '{bucket}' via entities ({entity_text}) and topic terms ({term_text})."


def _publication_type(record: dict[str, Any], extra: dict[str, Any]) -> str:
    text = " ".join(
        str(value)
        for value in (
            record.get("title"),
            record.get("categories"),
            extra.get("crossref_type"),
        )
        if value
    ).lower()
    if "preprint" in text or "biorxiv" in str(record.get("doi", "")).lower():
        return "preprint"
    if "review" in text:
        return "review"
    if "proceedings" in text or "abstract" in text:
        return "proceedings"
    if "journal-article" in text or record.get("doi"):
        return "primary"
    return "unknown"


def _matched_terms(text: str, terms: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    normalized = _normalize_search_text(text)
    matched = []
    for term in terms:
        if _term_matches(normalized, term):
            matched.append(term)
    return tuple(dict.fromkeys(matched))


def _term_matches(normalized_text: str, term: str) -> bool:
    normalized_term = _normalize_search_text(term)
    if not normalized_term:
        return False
    if normalized_term in normalized_text:
        return True
    collapsed = normalized_term.replace(" ", "")
    return bool(collapsed and collapsed in normalized_text.replace(" ", ""))


def _dedupe_key(paper: Paper) -> str:
    if paper.doi:
        return f"doi:{paper.doi}"
    if paper.pmids:
        return f"pmid:{sorted(paper.pmids)[0]}"
    return f"title:{_normalize_title(paper.title)}"


def _normalize_doi(value: str) -> str:
    value = value.strip().lower()
    value = value.removeprefix("https://doi.org/")
    value = value.removeprefix("http://doi.org/")
    if value.startswith("10."):
        return value
    return ""


def _normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _normalize_venue(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _normalize_search_text(value: str) -> str:
    value = value.lower()
    value = value.replace("\u03b1", " alpha ").replace("\u03b2", " beta ")
    value = value.replace("\u03b3", " gamma ")
    value = value.replace("-", " ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _parse_extra(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = ast.literal_eval(str(value))
    except (SyntaxError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _recency_score(age: int) -> float:
    if age <= 5:
        return 1.0
    if age <= 10:
        return 0.75
    if age <= 20:
        return 0.45
    return 0.25


def _int_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _source_rank(source: str) -> int:
    return SOURCE_PRIORITY.get(source, 99)


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
