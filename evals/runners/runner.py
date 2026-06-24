"""Offline eval runner for deterministic CI-safe workflow checks."""

from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from functional_proteomics_corpus import build_corpus_index, write_corpus_index
from fpw_api.tools import InMemoryTraceSink, ToolContext, TraceOrigin, create_default_tool_registry

EvalMode = Literal["smoke", "full"]

ALLOWED_CHECK_KINDS = frozenset(
    {
        "tool_choice",
        "schema_validity",
        "numeric",
        "citation_support",
        "entity_grounding",
        "unsupported_claim",
        "report_structure",
        "trace_completeness",
    }
)
ALLOWED_MODES = frozenset({"smoke", "full"})
SMOKE_CASE_ID = "case_runner_smoke"

REPORT_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "EvalRun",
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "suite", "mode", "results", "score", "created_at"],
    "properties": {
        "id": {"type": "string", "pattern": "^eval_run_.+"},
        "suite": {"type": "string", "minLength": 1},
        "mode": {"type": "string", "enum": sorted(ALLOWED_MODES)},
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["case_id", "passed", "checks", "trace_step_ids"],
                "properties": {
                    "case_id": {"type": "string", "pattern": "^case_.+"},
                    "passed": {"type": "boolean"},
                    "checks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["kind", "passed", "detail"],
                            "properties": {
                                "kind": {
                                    "type": "string",
                                    "enum": sorted(ALLOWED_CHECK_KINDS),
                                },
                                "passed": {"type": "boolean"},
                                "detail": {"type": ["string", "null"]},
                            },
                        },
                    },
                    "trace_step_ids": {
                        "type": "array",
                        "items": {"type": "string", "pattern": "^tc_.+"},
                    },
                },
            },
        },
        "score": {"type": "number", "minimum": 0, "maximum": 1},
        "created_at": {"type": "string", "format": "date-time"},
    },
}


class ReportValidationError(ValueError):
    """Raised when an eval report does not match the documented EvalRun shape."""


def run_eval_suite(
    mode: EvalMode,
    *,
    created_at: datetime | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run the current offline eval suite and return an EvalRun report."""

    if mode not in ALLOWED_MODES:
        raise ValueError(f"unsupported eval mode {mode!r}")

    now = _as_utc(created_at or datetime.now(UTC))
    report_id = run_id or _new_eval_run_id(now)
    results = [
        _run_runner_smoke_case(),
        _run_corpus_retrieval_smoke_case(eval_run_id=report_id),
    ]
    passed = sum(1 for result in results if result["passed"])
    report = {
        "id": report_id,
        "suite": "deterministic-smoke" if mode == "smoke" else "offline-skeleton",
        "mode": mode,
        "results": results,
        "score": passed / len(results),
        "created_at": _format_utc(now),
    }
    return validate_eval_run_report(report)


def validate_eval_run_report(report: dict[str, Any]) -> dict[str, Any]:
    """Validate an EvalRun report without requiring a JSON Schema dependency."""

    report = deepcopy(report)
    _require_exact_keys(
        report,
        {"id", "suite", "mode", "results", "score", "created_at"},
        path="EvalRun",
    )
    _require_prefixed_string(report["id"], "eval_run_", path="EvalRun.id")
    _require_non_empty_string(report["suite"], path="EvalRun.suite")
    if report["mode"] not in ALLOWED_MODES:
        raise ReportValidationError("EvalRun.mode must be 'smoke' or 'full'")
    _require_list(report["results"], path="EvalRun.results")
    if not isinstance(report["score"], int | float) or isinstance(report["score"], bool):
        raise ReportValidationError("EvalRun.score must be a number")
    if not 0 <= report["score"] <= 1:
        raise ReportValidationError("EvalRun.score must be between 0 and 1")
    _parse_utc_datetime(report["created_at"], path="EvalRun.created_at")

    case_count = len(report["results"])
    passed_count = 0
    for index, result in enumerate(report["results"]):
        _validate_eval_result(result, path=f"EvalRun.results[{index}]")
        if result["passed"]:
            passed_count += 1
    expected_score = 0.0 if case_count == 0 else passed_count / case_count
    if report["score"] != expected_score:
        raise ReportValidationError(
            f"EvalRun.score must equal passed cases / total cases ({expected_score})"
        )

    return report


def write_report(report: dict[str, Any], output: Path) -> Path:
    """Validate and write an EvalRun report as pretty JSON."""

    report = validate_eval_run_report(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run deterministic eval suites.")
    parser.add_argument("--mode", choices=sorted(ALLOWED_MODES), default="smoke")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evals/results/eval-latest.json"),
        help="Path for the machine-readable EvalRun JSON artifact.",
    )
    args = parser.parse_args(argv)

    report = run_eval_suite(args.mode)
    write_report(report, args.output)
    print(
        f"eval {report['id']} suite={report['suite']} mode={report['mode']} "
        f"score={report['score']:.3f} output={args.output}"
    )
    return 0 if report["score"] == 1 else 1


def _run_runner_smoke_case() -> dict[str, Any]:
    checks = [
        {
            "kind": "schema_validity",
            "passed": True,
            "detail": "Smoke case produced a valid EvalResult envelope.",
        },
        {
            "kind": "report_structure",
            "passed": True,
            "detail": "EvalRun report includes required replay and score fields.",
        },
        {
            "kind": "trace_completeness",
            "passed": True,
            "detail": "No tool calls were executed; trace_step_ids is explicitly empty.",
        },
    ]
    return {
        "case_id": SMOKE_CASE_ID,
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "trace_step_ids": [],
    }


def _run_corpus_retrieval_smoke_case(*, eval_run_id: str) -> dict[str, Any]:
    queries = [
        (
            "What public dataset and assay does this demo use?",
            {
                "src_nomic_perturb_pbmc",
                "src_nelisa_pbmc_repo",
                "src_dagher_2025_nelisa",
            },
        ),
        (
            "What evidence supports IL-10 dampening cytokine production in LPS or human "
            "immune-cell contexts?",
            {"src_dandrea_1993_il10", "src_wang_1995_il10_nfkb"},
        ),
        (
            "What context supports LPS-stimulated PBMC cytokine response interpretation?",
            {"src_degroote_1992_pbmc", "src_eggesbo_1994_lps_pbmc"},
        ),
    ]
    registry = create_default_tool_registry()
    sink = InMemoryTraceSink()
    checks: list[dict[str, Any]] = []
    trace_step_ids: list[str] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        index_path = write_corpus_index(build_corpus_index(), Path(tmpdir) / "corpus-index.json")
        context = ToolContext(
            origin=TraceOrigin(surface="eval", client="offline-runner"),
            trace_sink=sink,
            project_id="proj_demo",
            eval_run_id=eval_run_id,
            state={"corpus_index_path": index_path},
        )
        for query, expected_sources in queries:
            result = asyncio.run(
                registry.invoke(
                    "search_corpus",
                    {"query": query, "k": 3},
                    context,
                )
            )
            trace_step_ids.append(result.trace.id)
            output = result.output.model_dump(mode="json") if result.output else {"chunks": []}
            chunks = output["chunks"]
            expected_chunks = [
                chunk for chunk in chunks if chunk.get("source_id") in expected_sources
            ]
            citation_ok = bool(
                expected_chunks
                and all(
                    chunk.get("source_id")
                    and (
                        chunk.get("citation", {}).get("url")
                        or chunk.get("citation", {}).get("doi")
                    )
                    for chunk in expected_chunks
                )
            )
            entity_ok = bool(
                expected_chunks
                and any(chunk.get("matched_entities") or chunk.get("entities") for chunk in chunks)
            )
            trace_ok = (
                result.trace.status == "ok"
                and result.trace.output is not None
                and bool(result.trace.output.get("chunks"))
                and all(
                    chunk.get("source_id") and chunk.get("citation")
                    for chunk in result.trace.output["chunks"]
                )
            )
            checks.extend(
                [
                    {
                        "kind": "citation_support",
                        "passed": citation_ok,
                        "detail": f"Retrieved approved cited source for query: {query}",
                    },
                    {
                        "kind": "entity_grounding",
                        "passed": entity_ok,
                        "detail": f"Retrieved chunk includes entity tags for query: {query}",
                    },
                    {
                        "kind": "trace_completeness",
                        "passed": trace_ok,
                        "detail": "search_corpus trace records source IDs and citation metadata.",
                    },
                ]
            )

    return {
        "case_id": "case_corpus_retrieval_smoke",
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "trace_step_ids": trace_step_ids,
    }


def _validate_eval_result(result: Any, *, path: str) -> None:
    if not isinstance(result, dict):
        raise ReportValidationError(f"{path} must be an object")
    _require_exact_keys(result, {"case_id", "passed", "checks", "trace_step_ids"}, path=path)
    _require_prefixed_string(result["case_id"], "case_", path=f"{path}.case_id")
    if not isinstance(result["passed"], bool):
        raise ReportValidationError(f"{path}.passed must be a boolean")
    _require_list(result["checks"], path=f"{path}.checks")
    _require_list(result["trace_step_ids"], path=f"{path}.trace_step_ids")

    for index, check in enumerate(result["checks"]):
        _validate_eval_check(check, path=f"{path}.checks[{index}]")
    for index, trace_step_id in enumerate(result["trace_step_ids"]):
        _require_prefixed_string(
            trace_step_id,
            "tc_",
            path=f"{path}.trace_step_ids[{index}]",
        )

    if result["passed"] != all(check["passed"] for check in result["checks"]):
        raise ReportValidationError(f"{path}.passed must summarize all check verdicts")


def _validate_eval_check(check: Any, *, path: str) -> None:
    if not isinstance(check, dict):
        raise ReportValidationError(f"{path} must be an object")
    _require_exact_keys(check, {"kind", "passed", "detail"}, path=path)
    if check["kind"] not in ALLOWED_CHECK_KINDS:
        raise ReportValidationError(f"{path}.kind is not a supported EvalCheck kind")
    if not isinstance(check["passed"], bool):
        raise ReportValidationError(f"{path}.passed must be a boolean")
    if check["detail"] is not None and not isinstance(check["detail"], str):
        raise ReportValidationError(f"{path}.detail must be a string or null")


def _require_exact_keys(value: dict[str, Any], expected: set[str], *, path: str) -> None:
    actual = set(value)
    missing = expected - actual
    extra = actual - expected
    if missing:
        raise ReportValidationError(f"{path} missing required keys: {sorted(missing)}")
    if extra:
        raise ReportValidationError(f"{path} has unexpected keys: {sorted(extra)}")


def _require_non_empty_string(value: Any, *, path: str) -> None:
    if not isinstance(value, str) or value == "":
        raise ReportValidationError(f"{path} must be a non-empty string")


def _require_prefixed_string(value: Any, prefix: str, *, path: str) -> None:
    _require_non_empty_string(value, path=path)
    if not value.startswith(prefix):
        raise ReportValidationError(f"{path} must start with {prefix!r}")


def _require_list(value: Any, *, path: str) -> None:
    if not isinstance(value, list):
        raise ReportValidationError(f"{path} must be a list")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("created_at must be timezone-aware")
    return value.astimezone(UTC)


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_utc_datetime(value: Any, *, path: str) -> datetime:
    _require_non_empty_string(value, path=path)
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ReportValidationError(f"{path} must be an ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise ReportValidationError(f"{path} must include a timezone")
    return parsed.astimezone(UTC)


def _new_eval_run_id(created_at: datetime) -> str:
    return f"eval_run_{created_at.strftime('%Y%m%dT%H%M%S%fZ')}"
