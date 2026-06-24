from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WATCHER = ROOT / "scripts" / "wait-for-pr-event.sh"


def pr_json(
    *,
    state: str = "OPEN",
    merge: str = "CLEAN",
    checks: list[dict[str, str | None]] | None = None,
    comments: list[dict[str, object]] | None = None,
    reviews: list[dict[str, object]] | None = None,
) -> str:
    return json.dumps(
        {
            "number": 123,
            "state": state,
            "mergeStateStatus": merge,
            "statusCheckRollup": checks or [],
            "comments": comments or [],
            "latestReviews": reviews or [],
        }
    )


class WaitForPrEventTests(unittest.TestCase):
    def run_watcher(self, responses: list[str], *, timeout: int = 4, interval: int = 0) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            responses_dir = tmp / "responses"
            responses_dir.mkdir()
            for index, response in enumerate(responses, start=1):
                (responses_dir / f"{index}.json").write_text(response, encoding="utf-8")

            gh = tmp / "gh"
            gh.write_text(
                textwrap.dedent(
                    """\
                    #!/usr/bin/env bash
                    set -euo pipefail
                    if [ "${1:-}" = "repo" ]; then
                      echo '{"nameWithOwner":"michael-ford/functional-proteomics-workbench"}'
                      exit 0
                    fi
                    if [ "${1:-}" = "pr" ] && [ "${2:-}" = "view" ]; then
                      count_file="${GH_MOCK_COUNT}"
                      count="0"
                      if [ -f "$count_file" ]; then
                        count="$(cat "$count_file")"
                      fi
                      count="$((count + 1))"
                      echo "$count" > "$count_file"
                      response="${GH_MOCK_RESPONSES}/${count}.json"
                      if [ ! -f "$response" ]; then
                        response="${GH_MOCK_RESPONSES}/$(ls "$GH_MOCK_RESPONSES" | sort -n | tail -1)"
                      fi
                      cat "$response"
                      exit 0
                    fi
                    echo "unexpected gh invocation: $*" >&2
                    exit 1
                    """
                ),
                encoding="utf-8",
            )
            gh.chmod(0o755)

            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{tmp}{os.pathsep}{env['PATH']}",
                    "GH_REPO": "michael-ford/functional-proteomics-workbench",
                    "GH_MOCK_RESPONSES": str(responses_dir),
                    "GH_MOCK_COUNT": str(tmp / "count"),
                    "REQUIRED_CHECKS": "ci,review (claude),review (codex)",
                }
            )
            result = subprocess.run(
                [
                    "bash",
                    str(WATCHER),
                    "--timeout",
                    str(timeout),
                    "--interval",
                    str(interval),
                ],
                check=True,
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            return result.stdout.strip()

    def test_no_pr_sentinel_when_current_branch_has_no_pr(self) -> None:
        self.assertEqual(self.run_watcher([""], timeout=1), "NO_PR")

    def test_returns_when_required_check_transitions_to_failure(self) -> None:
        pending = pr_json(
            checks=[
                {"name": "ci", "status": "IN_PROGRESS", "conclusion": None},
                {"name": "review (codex)", "status": "QUEUED", "conclusion": None},
            ]
        )
        failed = pr_json(
            checks=[
                {"name": "ci", "status": "COMPLETED", "conclusion": "FAILURE"},
                {"name": "review (codex)", "status": "QUEUED", "conclusion": None},
            ]
        )

        self.assertEqual(
            self.run_watcher([pending, failed]),
            "CHECK_FAILURE pr=123 checks=ci",
        )

    def test_returns_when_maintainer_comment_appears(self) -> None:
        baseline = pr_json()
        with_comment = pr_json(
            comments=[
                {
                    "id": "comment-1",
                    "createdAt": "2026-06-23T12:00:00Z",
                    "authorAssociation": "OWNER",
                    "author": {"login": "michael-ford", "__typename": "User"},
                    "body": "not printed by watcher",
                }
            ]
        )

        self.assertEqual(
            self.run_watcher([baseline, with_comment]),
            "COMMENT_EVENT pr=123 maintainer_comments=1",
        )

    def test_heartbeat_after_timeout_without_change(self) -> None:
        output = self.run_watcher([pr_json()], timeout=0)

        self.assertEqual(output, "HEARTBEAT no-change-15m pr=123 state=OPEN merge=CLEAN")


if __name__ == "__main__":
    unittest.main()
