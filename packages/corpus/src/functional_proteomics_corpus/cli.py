"""Corpus build command."""

from __future__ import annotations

import argparse
from pathlib import Path

from functional_proteomics_corpus.index import (
    DEFAULT_INDEX_RELATIVE,
    build_corpus_index,
    load_source_manifest,
    write_corpus_index,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the deterministic v0.1 corpus index.")
    parser.add_argument(
        "command",
        choices=["build"],
        help="Operation to run.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Optional approved source manifest JSON. Defaults to the packaged v0.1 manifest.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_INDEX_RELATIVE,
        help="Output path for the built corpus index JSON.",
    )
    args = parser.parse_args(argv)

    manifest = load_source_manifest(args.manifest)
    index = build_corpus_index(manifest)
    output = write_corpus_index(index, args.output)
    print(
        f"built corpus index sources={len(index.sources)} chunks={len(index.chunks)} "
        f"output={output}"
    )
    return 0
