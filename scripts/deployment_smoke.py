"""Deployment and demo replay smoke checks for local and Railway environments."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from scripts.demo_reset import reset_demo_project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deployment readiness smoke checks.")
    parser.add_argument(
        "--api-url",
        default=os.environ.get("APP_BASE_URL", "http://127.0.0.1:8000"),
        help="Base URL for the deployed or local API.",
    )
    parser.add_argument(
        "--skip-http",
        action="store_true",
        help="Only run local deterministic demo replay checks.",
    )
    args = parser.parse_args(argv)

    checks = run_deployment_smoke(api_url=args.api_url, skip_http=args.skip_http)
    print(json.dumps({"checks": checks}, indent=2, sort_keys=True))
    failed = [check for check in checks if check["status"] not in {"ok", "skipped"}]
    return 1 if failed else 0


def run_deployment_smoke(*, api_url: str, skip_http: bool = False) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    checks.append(_env_check())
    if skip_http:
        checks.append({"name": "api_ready", "status": "skipped", "detail": "HTTP skipped"})
    else:
        checks.append(_api_ready_check(api_url))
    checks.append(_demo_reset_check())
    return checks


def _env_check() -> dict[str, Any]:
    provider = os.environ.get("MODEL_PROVIDER", "openrouter")
    has_openrouter_key = bool(os.environ.get("OPENROUTER_API_KEY", "").strip())
    use_mock = os.environ.get("FPW_USE_MOCK_MODEL", "").casefold() in {"1", "true", "yes"}
    mode = "mock" if use_mock or not has_openrouter_key else "openrouter"
    return {
        "name": "runtime_env",
        "status": "ok",
        "detail": f"MODEL_PROVIDER={provider}; chat_adapter_mode={mode}",
    }


def _api_ready_check(api_url: str) -> dict[str, Any]:
    ready_url = f"{api_url.rstrip('/')}/ready"
    request = urllib.request.Request(ready_url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"name": "api_ready", "status": "failed", "detail": str(exc)}

    if payload.get("status") == "ready":
        return {"name": "api_ready", "status": "ok", "detail": ready_url}
    return {"name": "api_ready", "status": "failed", "detail": json.dumps(payload)}


def _demo_reset_check() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        summary = reset_demo_project(state_root=tmp_path / ".fpw_state")
        project_dir = Path(str(summary["project_dir"]))
        required = [
            project_dir / "project.json",
            project_dir / "datasets" / "dataset.json",
            project_dir / "datasets" / "validation.json",
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            return {
                "name": "demo_reset",
                "status": "failed",
                "detail": f"missing files: {', '.join(missing)}",
            }
        return {
            "name": "demo_reset",
            "status": "ok",
            "detail": f"project_id={summary['project_id']}; rows={summary['row_count']}",
        }


if __name__ == "__main__":
    raise SystemExit(main())
