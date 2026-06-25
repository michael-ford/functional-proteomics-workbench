"""Reset the local demo workspace to the deterministic seeded state."""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
from pathlib import Path
from typing import Any

from scripts.seed_demo_project import PROJECT_ID, seed_demo_project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reset the deterministic v0.1 demo state.")
    parser.add_argument(
        "--state-root",
        type=Path,
        default=Path(".fpw_state"),
        help="Root directory for local project state.",
    )
    parser.add_argument(
        "--fixture-root",
        type=Path,
        default=Path("demo_data"),
        help="Root directory containing raw/ and processed/ demo fixture files.",
    )
    parser.add_argument(
        "--rebuild-web-artifacts",
        action="store_true",
        help="Also rebuild demo_data/artifacts for the Next.js dashboard.",
    )
    args = parser.parse_args(argv)

    summary = reset_demo_project(
        state_root=args.state_root,
        fixture_root=args.fixture_root,
        rebuild_web_artifacts=args.rebuild_web_artifacts,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def reset_demo_project(
    *,
    state_root: Path = Path(".fpw_state"),
    fixture_root: Path = Path("demo_data"),
    rebuild_web_artifacts: bool = False,
) -> dict[str, Any]:
    project_dir = state_root.resolve() / "projects" / PROJECT_ID
    if project_dir.exists():
        shutil.rmtree(project_dir)

    seed_summary = seed_demo_project(state_root=state_root, fixture_root=fixture_root)
    result: dict[str, Any] = {
        **seed_summary.as_dict(),
        "reset": True,
        "web_artifacts_rebuilt": False,
    }
    if rebuild_web_artifacts:
        from scripts import build_demo_web_artifacts

        asyncio.run(build_demo_web_artifacts.main())
        result["web_artifacts_rebuilt"] = True
    return result


if __name__ == "__main__":
    raise SystemExit(main())
