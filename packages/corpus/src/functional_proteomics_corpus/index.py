"""Deterministic approved-corpus ingestion and retrieval."""

from __future__ import annotations

import hashlib
import json
import re
from importlib import resources
from pathlib import Path
from typing import Any

from functional_proteomics_corpus.entities import (
    assay_context_tags,
    normalize_entity,
    tag_entities,
)
from functional_proteomics_corpus.models import CorpusIndex, EvidenceChunkRecord, SourceMetadata

SCHEMA_VERSION = "0.1.0"
SOURCE_MANIFEST_ID = "corpus_sources_il10_lps_v0"
DETERMINISTIC_BUILD_TIME = "2026-06-24T00:00:00Z"
DEFAULT_INDEX_RELATIVE = Path(".fpw_state/corpus/index.json")
CHUNKING_POLICY = {
    "target_words": [800, 1200],
    "overlap_words": 150,
    "strategy": "deterministic section chunks for v0.1 fixture sources",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)?")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "does",
    "for",
    "in",
    "is",
    "of",
    "or",
    "the",
    "this",
    "to",
    "what",
    "with",
}


class CorpusUnindexedError(FileNotFoundError):
    """Raised when retrieval is requested before the corpus index exists."""


def load_source_manifest(path: Path | None = None) -> dict[str, Any]:
    """Load the approved v0.1 source manifest."""

    if path is not None:
        return json.loads(path.read_text(encoding="utf-8"))
    manifest = resources.files("functional_proteomics_corpus").joinpath(
        "data/approved_sources.json"
    )
    return json.loads(manifest.read_text(encoding="utf-8"))


def build_corpus_index(manifest: dict[str, Any] | None = None) -> CorpusIndex:
    """Build a deterministic corpus index from approved fixture sources."""

    source_manifest = manifest or load_source_manifest()
    sources: list[SourceMetadata] = []
    chunks: list[EvidenceChunkRecord] = []

    for raw_source in source_manifest["sources"]:
        source = _source_metadata(raw_source)
        sources.append(source)
        for chunk_number, chunk in enumerate(_chunks_for_source(source, raw_source), start=1):
            chunks.append(
                EvidenceChunkRecord(
                    chunk_id=f"chunk_{source.source_id}_{chunk_number:04d}",
                    source_id=source.source_id,
                    text=chunk["text"],
                    section=chunk["section"],
                    entities=tuple(chunk["entities"]),
                    assay_context=tuple(assay_context_tags(chunk["entities"])),
                    citation=source.citation(),
                    embedding_status="pending",
                )
            )

    return CorpusIndex(
        schema_version=SCHEMA_VERSION,
        built_at=source_manifest.get("generated_at", DETERMINISTIC_BUILD_TIME),
        source_manifest_id=str(source_manifest["manifest_id"]),
        chunking_policy=CHUNKING_POLICY,
        sources=tuple(sources),
        chunks=tuple(chunks),
    )


def write_corpus_index(index: CorpusIndex, output: Path) -> Path:
    """Write a deterministic JSON corpus index."""

    output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(index.to_dict(), indent=2, sort_keys=True) + "\n"
    output.write_text(payload, encoding="utf-8")
    return output


def load_corpus_index(path: Path) -> CorpusIndex:
    """Load a built corpus index, failing closed when it is absent."""

    if not path.exists():
        raise CorpusUnindexedError(f"corpus index has not been built: {path}")
    return CorpusIndex.from_dict(json.loads(path.read_text(encoding="utf-8")))


def search_corpus_index(
    index: CorpusIndex,
    query: str,
    *,
    entities: list[str] | None = None,
    k: int = 5,
) -> list[dict[str, Any]]:
    """Search the built corpus with deterministic lexical/entity/topic scoring."""

    query_tokens = _tokens(query)
    query_entities = _query_entities(query, entities)
    sources_by_id = {source.source_id: source for source in index.sources}
    results: list[tuple[float, EvidenceChunkRecord, SourceMetadata, list[str]]] = []

    for chunk in index.chunks:
        source = sources_by_id[chunk.source_id]
        score, matched_entities = _score_chunk(
            query_tokens=query_tokens,
            query_entities=query_entities,
            chunk=chunk,
            source=source,
        )
        if score > 0:
            results.append((score, chunk, source, matched_entities))

    results.sort(
        key=lambda item: (
            -item[0],
            item[2].retrieval_priority,
            item[1].source_id,
            item[1].chunk_id,
        )
    )
    return [
        _result_payload(score=score, chunk=chunk, source=source, matched_entities=matched)
        for score, chunk, source, matched in results[:k]
    ]


def _source_metadata(raw_source: dict[str, Any]) -> SourceMetadata:
    raw_metadata = dict(raw_source)
    raw_metadata["content_sha256"] = _content_sha256(raw_source)
    raw_metadata.pop("sections", None)
    return SourceMetadata.from_dict(raw_metadata)


def _chunks_for_source(
    source: SourceMetadata,
    raw_source: dict[str, Any],
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for section in raw_source["sections"]:
        section_title = str(section["section"])
        section_text = _normalize_whitespace(str(section["text"]))
        for text in _chunk_text(section_text):
            entity_text = " ".join([source.title, text, " ".join(source.topic_buckets)])
            entities = tag_entities(entity_text)
            chunks.append({"section": section_title, "text": text, "entities": entities})
    return chunks


def _chunk_text(text: str) -> list[str]:
    words = text.split()
    if len(words) <= CHUNKING_POLICY["target_words"][1]:
        return [text]

    target = CHUNKING_POLICY["target_words"][1]
    overlap = int(CHUNKING_POLICY["overlap_words"])
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + target, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(0, end - overlap)
    return chunks


def _score_chunk(
    *,
    query_tokens: set[str],
    query_entities: set[str],
    chunk: EvidenceChunkRecord,
    source: SourceMetadata,
) -> tuple[float, list[str]]:
    corpus_text = " ".join(
        [
            source.title,
            " ".join(source.topic_buckets),
            chunk.section or "",
            chunk.text,
            " ".join(chunk.entities),
        ]
    )
    corpus_tokens = _tokens(corpus_text)
    lexical_overlap = query_tokens & corpus_tokens
    lexical_score = len(lexical_overlap) / max(len(query_tokens), 1)

    chunk_entities = set(chunk.entities)
    if query_entities:
        matched_entities = sorted(query_entities & chunk_entities)
        entity_score = len(matched_entities) / len(query_entities)
    else:
        matched_entities = list(chunk.entities)
        entity_score = 0.15 if matched_entities else 0.0

    topic_tokens = _tokens(" ".join(source.topic_buckets))
    topic_score = len(query_tokens & topic_tokens) / max(len(query_tokens), 1)
    priority_score = 1 / max(source.retrieval_priority, 1)
    score = (lexical_score * 6) + (entity_score * 4) + (topic_score * 2) + priority_score
    return score, matched_entities


def _result_payload(
    *,
    score: float,
    chunk: EvidenceChunkRecord,
    source: SourceMetadata,
    matched_entities: list[str],
) -> dict[str, Any]:
    source_dict = source.to_dict()
    metadata = {
        "source_id": source.source_id,
        "source_type": source.source_type,
        "title": source.title,
        "topic_buckets": list(source.topic_buckets),
        "approved_for_claims": source.approved_for_claims,
        "retrieval_priority": source.retrieval_priority,
        "source_locator": source.source_locator,
        "access_route": source.access_route,
        "license_note": source.license_note,
        "content_sha256": source.content_sha256,
        "candidate_rank": source.candidate_rank,
        "citation_count": source.citation_count,
        "candidate_score": source.candidate_score,
        "venue": source.venue,
    }
    payload = chunk.to_dict()
    payload.update(
        {
            "score": round(score, 6),
            "matched_entities": matched_entities,
            "metadata": metadata,
            "source": source_dict,
        }
    )
    return payload


def _query_entities(query: str, entities: list[str] | None) -> set[str]:
    tagged = tag_entities(query)
    explicit = [normalize_entity(entity) for entity in entities or []]
    return set(tagged + explicit)


def _tokens(text: str) -> set[str]:
    return {token for token in _TOKEN_RE.findall(text.casefold()) if token not in _STOPWORDS}


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _content_sha256(raw_source: dict[str, Any]) -> str:
    payload = json.dumps(raw_source["sections"], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
