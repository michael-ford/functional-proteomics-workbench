"""Deterministic corpus ingestion and retrieval."""

from functional_proteomics_corpus.index import (
    DEFAULT_INDEX_RELATIVE,
    CorpusUnindexedError,
    build_corpus_index,
    load_corpus_index,
    search_corpus_index,
    write_corpus_index,
)
from functional_proteomics_corpus.models import Citation, CorpusIndex, EvidenceChunkRecord

__all__ = [
    "DEFAULT_INDEX_RELATIVE",
    "Citation",
    "CorpusIndex",
    "CorpusUnindexedError",
    "EvidenceChunkRecord",
    "build_corpus_index",
    "load_corpus_index",
    "search_corpus_index",
    "write_corpus_index",
]
