"""CLI for exporting the shared-schemas JSON Schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from shared_schemas.schema import combined_json_schema


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("schema/shared-schemas.schema.json"),
        help="Path to write the generated JSON Schema.",
    )
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(combined_json_schema(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
