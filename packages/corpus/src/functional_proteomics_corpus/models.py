"""Corpus data models kept separate from protected shared contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

SourceType = Literal["paper", "docs", "github", "webpage", "supplement"]


@dataclass(frozen=True, slots=True)
class Citation:
    url: str | None = None
    doi: str | None = None
    paper_title: str | None = None
    authors: str | None = None
    year: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Citation:
        return cls(
            url=_optional_str(value.get("url")),
            doi=_optional_str(value.get("doi")),
            paper_title=_optional_str(value.get("paper_title")),
            authors=_optional_str(value.get("authors")),
            year=_optional_str(value.get("year")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "doi": self.doi,
            "paper_title": self.paper_title,
            "authors": self.authors,
            "year": self.year,
        }


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    source_id: str
    source_type: SourceType
    title: str
    url: str | None
    doi: str | None
    license_note: str | None
    topic_buckets: tuple[str, ...]
    approved_for_claims: bool
    retrieval_priority: int
    source_locator: str
    access_route: str
    ingested_at: str
    content_sha256: str
    authors: str | None = None
    year: str | None = None
    venue: str | None = None
    candidate_rank: int | None = None
    citation_count: int | None = None
    candidate_score: float | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> SourceMetadata:
        return cls(
            source_id=str(value["source_id"]),
            source_type=_source_type(value["source_type"]),
            title=str(value["title"]),
            url=_optional_str(value.get("url")),
            doi=_optional_str(value.get("doi")),
            license_note=_optional_str(value.get("license_note")),
            topic_buckets=tuple(str(bucket) for bucket in value["topic_buckets"]),
            approved_for_claims=bool(value["approved_for_claims"]),
            retrieval_priority=int(value["retrieval_priority"]),
            source_locator=str(value["source_locator"]),
            access_route=str(value["access_route"]),
            ingested_at=str(value["ingested_at"]),
            content_sha256=str(value["content_sha256"]),
            authors=_optional_str(value.get("authors")),
            year=_optional_str(value.get("year")),
            venue=_optional_str(value.get("venue")),
            candidate_rank=_optional_int(value.get("candidate_rank")),
            citation_count=_optional_int(value.get("citation_count")),
            candidate_score=_optional_float(value.get("candidate_score")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "title": self.title,
            "url": self.url,
            "doi": self.doi,
            "license_note": self.license_note,
            "topic_buckets": list(self.topic_buckets),
            "approved_for_claims": self.approved_for_claims,
            "retrieval_priority": self.retrieval_priority,
            "source_locator": self.source_locator,
            "access_route": self.access_route,
            "ingested_at": self.ingested_at,
            "content_sha256": self.content_sha256,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "candidate_rank": self.candidate_rank,
            "citation_count": self.citation_count,
            "candidate_score": self.candidate_score,
        }

    def citation(self) -> Citation:
        return Citation(
            url=self.url,
            doi=self.doi,
            paper_title=self.title if self.source_type == "paper" else None,
            authors=self.authors,
            year=self.year,
        )


@dataclass(frozen=True, slots=True)
class EvidenceChunkRecord:
    chunk_id: str
    source_id: str
    text: str
    section: str | None
    entities: tuple[str, ...]
    assay_context: tuple[str, ...]
    citation: Citation
    embedding_status: Literal["pending", "embedded"] = "pending"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> EvidenceChunkRecord:
        return cls(
            chunk_id=str(value["id"]),
            source_id=str(value["source_id"]),
            text=str(value["text"]),
            section=_optional_str(value.get("section")),
            entities=tuple(str(entity) for entity in value.get("entities", [])),
            assay_context=tuple(str(entity) for entity in value.get("assay_context", [])),
            citation=Citation.from_dict(value["citation"]),
            embedding_status=_embedding_status(value.get("embedding_status", "pending")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.chunk_id,
            "source_id": self.source_id,
            "text": self.text,
            "section": self.section,
            "entities": list(self.entities),
            "assay_context": list(self.assay_context),
            "citation": self.citation.to_dict(),
            "embedding_status": self.embedding_status,
        }


@dataclass(frozen=True, slots=True)
class CorpusIndex:
    schema_version: str
    built_at: str
    source_manifest_id: str
    chunking_policy: dict[str, Any]
    sources: tuple[SourceMetadata, ...]
    chunks: tuple[EvidenceChunkRecord, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CorpusIndex:
        return cls(
            schema_version=str(value["schema_version"]),
            built_at=str(value["built_at"]),
            source_manifest_id=str(value["source_manifest_id"]),
            chunking_policy=dict(value["chunking_policy"]),
            sources=tuple(SourceMetadata.from_dict(source) for source in value["sources"]),
            chunks=tuple(EvidenceChunkRecord.from_dict(chunk) for chunk in value["chunks"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "built_at": self.built_at,
            "source_manifest_id": self.source_manifest_id,
            "chunking_policy": self.chunking_policy,
            "sources": [source.to_dict() for source in self.sources],
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _source_type(value: Any) -> SourceType:
    if value not in {"paper", "docs", "github", "webpage", "supplement"}:
        raise ValueError(f"unsupported source_type: {value!r}")
    return value


def _embedding_status(value: Any) -> Literal["pending", "embedded"]:
    if value not in {"pending", "embedded"}:
        raise ValueError(f"unsupported embedding_status: {value!r}")
    return value
