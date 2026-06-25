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

from functional_proteomics_analysis import DEFAULT_METHOD_ID
from functional_proteomics_corpus import build_corpus_index, write_corpus_index
from fpw_api.tools import InMemoryTraceSink, ToolContext, TraceOrigin, create_default_tool_registry
from fpw_api.tools.mvp import DEMO_DATASET_ID

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
HERO_CASE_IDS = (
    "case_hero_01_create_project",
    "case_hero_02_validate_dataset",
    "case_hero_03_define_comparison",
    "case_hero_04_select_method",
    "case_hero_05_rank_proteins",
    "case_hero_06_retrieve_evidence",
    "case_hero_07_generate_report",
)
DEFAULT_CASES_DIR = Path(__file__).resolve().parents[1] / "cases"

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

HERO_COMPARISON: dict[str, Any] = {
    "group_a": {"perturbagen": "IL-10"},
    "group_b": {"perturbagen": "control"},
    "stimulation_context": "LPS",
    "paired_by": "donor",
}


class ReportValidationError(ValueError):
    """Raised when an eval report does not match the documented EvalRun shape."""


class EvalCaseConfigurationError(ValueError):
    """Raised when formal deterministic eval case files are missing or invalid."""


def run_eval_suite(
    mode: EvalMode,
    *,
    created_at: datetime | None = None,
    run_id: str | None = None,
    cases_dir: Path | None = None,
) -> dict[str, Any]:
    """Run the current offline eval suite and return an EvalRun report."""

    if mode not in ALLOWED_MODES:
        raise ValueError(f"unsupported eval mode {mode!r}")

    case_specs = _load_hero_case_specs(cases_dir or DEFAULT_CASES_DIR)
    now = _as_utc(created_at or datetime.now(UTC))
    report_id = run_id or _new_eval_run_id(now)
    results = _run_hero_workflow_cases(eval_run_id=report_id, case_specs=case_specs)
    passed = sum(1 for result in results if result["passed"])
    report = {
        "id": report_id,
        "suite": "deterministic-hero-workflow" if mode == "smoke" else "offline-hero-workflow",
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


def _load_hero_case_specs(cases_dir: Path) -> dict[str, dict[str, Any]]:
    case_specs: dict[str, dict[str, Any]] = {}
    for path in sorted(cases_dir.glob("*.json")):
        spec = json.loads(path.read_text(encoding="utf-8"))
        case_id = spec.get("id")
        if isinstance(case_id, str):
            case_specs[case_id] = spec

    missing = [case_id for case_id in HERO_CASE_IDS if case_id not in case_specs]
    if missing:
        raise EvalCaseConfigurationError(f"missing required hero eval cases: {missing}")

    for case_id in HERO_CASE_IDS:
        _validate_eval_case_spec(case_specs[case_id], path=f"{cases_dir}/{case_id}.json")
    return {case_id: case_specs[case_id] for case_id in HERO_CASE_IDS}


def _validate_eval_case_spec(spec: dict[str, Any], *, path: str) -> None:
    required = {"id", "name", "description", "tags", "deterministic", "expectations"}
    _require_exact_keys(spec, required | {"fixture_refs"}, path=path)
    _require_prefixed_string(spec["id"], "case_", path=f"{path}.id")
    _require_non_empty_string(spec["name"], path=f"{path}.name")
    _require_non_empty_string(spec["description"], path=f"{path}.description")
    _require_list(spec["tags"], path=f"{path}.tags")
    if spec["deterministic"] is not True:
        raise EvalCaseConfigurationError(f"{path}.deterministic must be true for smoke")
    _require_list(spec["fixture_refs"], path=f"{path}.fixture_refs")
    _require_list(spec["expectations"], path=f"{path}.expectations")
    if not spec["expectations"]:
        raise EvalCaseConfigurationError(f"{path}.expectations must not be empty")
    for index, expectation in enumerate(spec["expectations"]):
        _validate_case_expectation(expectation, path=f"{path}.expectations[{index}]")


def _validate_case_expectation(expectation: Any, *, path: str) -> None:
    if not isinstance(expectation, dict):
        raise EvalCaseConfigurationError(f"{path} must be an object")
    _require_exact_keys(expectation, {"tool_name", "checks"}, path=path)
    if expectation["tool_name"] is not None:
        _require_non_empty_string(expectation["tool_name"], path=f"{path}.tool_name")
    _require_list(expectation["checks"], path=f"{path}.checks")
    if not expectation["checks"]:
        raise EvalCaseConfigurationError(f"{path}.checks must not be empty")
    for index, check in enumerate(expectation["checks"]):
        _validate_eval_check(check, path=f"{path}.checks[{index}]")


def _run_hero_workflow_cases(
    *,
    eval_run_id: str,
    case_specs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    registry = create_default_tool_registry()
    sink = InMemoryTraceSink()
    state: dict[str, Any] = {"projects": {}}
    with tempfile.TemporaryDirectory() as tmpdir:
        state["state_root"] = tmpdir
        state["corpus_index_path"] = write_corpus_index(
            build_corpus_index(),
            Path(tmpdir) / "corpus-index.json",
        )
        context = ToolContext(
            origin=TraceOrigin(surface="eval", client="offline-runner"),
            trace_sink=sink,
            eval_run_id=eval_run_id,
            state=state,
        )

        case1 = _invoke(
            registry,
            "create_project",
            {"title": "IL-10/LPS Perturb-PBMC hero workflow"},
            context,
        )
        project_id = _output(case1)["project_id"]
        context = ToolContext(
            origin=context.origin,
            trace_sink=sink,
            project_id=project_id,
            eval_run_id=eval_run_id,
            state=state,
        )
        case2_validate = _invoke(
            registry,
            "validate_dataset",
            {"project_id": project_id, "dataset_id": DEMO_DATASET_ID},
            context,
        )
        case2_schema = _invoke(
            registry,
            "inspect_dataset_schema",
            {"project_id": project_id, "dataset_id": DEMO_DATASET_ID},
            context,
        )
        case3 = _invoke(
            registry,
            "define_comparison",
            {
                "project_id": project_id,
                "dataset_id": DEMO_DATASET_ID,
                "comparison": HERO_COMPARISON,
            },
            context,
        )
        case4 = _invoke(
            registry,
            "define_comparison",
            {
                "project_id": project_id,
                "dataset_id": DEMO_DATASET_ID,
                "comparison": HERO_COMPARISON,
            },
            context,
        )
        plan_id = _output(case4)["id"]
        case5_run = _invoke(
            registry,
            "run_comparison",
            {"project_id": project_id, "plan_id": plan_id},
            context,
        )
        result_id = _output(case5_run)["id"]
        case5_rank = _invoke(
            registry,
            "rank_proteins",
            {"project_id": project_id, "result_id": result_id, "metric": "effect_size"},
            context,
        )
        case6_searches = [
            _invoke(
                registry,
                "search_corpus",
                {
                    "query": query,
                    "entities": entities,
                    "k": 3,
                },
                context,
            )
            for query, entities in [
                (
                    "public Perturb-PBMC nELISA dataset provenance and assay context",
                    ["Perturb-PBMC", "nELISA"],
                ),
                (
                    "IL-10 dampening LPS-stimulated PBMC cytokine response",
                    ["IL-10", "LPS", "PBMC"],
                ),
                (
                    "LPS stimulated PBMC inflammatory cytokine response interpretation",
                    ["LPS", "PBMC"],
                ),
            ]
        ]
        chunk_ids = _retrieved_chunk_ids(case6_searches)
        case7_attach = _invoke(
            registry,
            "attach_evidence",
            {"project_id": project_id, "chunk_ids": chunk_ids},
            context,
        )
        case7_report = _invoke(
            registry,
            "export_report",
            {
                "project_id": project_id,
                "result_id": result_id,
                "attachment_ids": [_output(case7_attach)["id"]],
            },
            context,
        )

    return [
        _result(
            "case_hero_01_create_project",
            case_specs,
            [case1],
            [
                _check(
                    "tool_choice",
                    _trace_tool(case1) == "create_project",
                    "create_project executed through the shared ToolRegistry.",
                ),
                _check(
                    "schema_validity",
                    _ok(case1)
                    and _output(case1)["upload_url"].endswith("source=selected_public")
                    and _output(case1)["project_id"].startswith("proj_"),
                    "Created project returns selected_public handoff URL and project id.",
                ),
                _trace_check([case1]),
            ],
        ),
        _result(
            "case_hero_02_validate_dataset",
            case_specs,
            [case2_validate, case2_schema],
            [
                _check(
                    "tool_choice",
                    [_trace_tool(case2_validate), _trace_tool(case2_schema)]
                    == ["validate_dataset", "inspect_dataset_schema"],
                    "Validation and schema inspection ran via registry tools.",
                ),
                _check(
                    "schema_validity",
                    _ok(case2_validate)
                    and _ok(case2_schema)
                    and _output(case2_validate)["status"] == "passed"
                    and _output(case2_validate)["row_count"] == 2394
                    and _output(case2_schema)["layout"] == "long",
                    "Approved Perturb-PBMC fixture validates and reports long layout.",
                ),
                _trace_check([case2_validate, case2_schema]),
            ],
        ),
        _result(
            "case_hero_03_define_comparison",
            case_specs,
            [case3],
            [
                _check(
                    "tool_choice",
                    _trace_tool(case3) == "define_comparison",
                    "Comparison was defined through define_comparison.",
                ),
                _check(
                    "schema_validity",
                    _comparison_matches_hero(_output(case3)["comparison"]),
                    "Comparison is IL-10 vs matched control under LPS paired by donor.",
                ),
                _trace_check([case3]),
            ],
        ),
        _result(
            "case_hero_04_select_method",
            case_specs,
            [case4],
            [
                _check(
                    "tool_choice",
                    _trace_tool(case4) == "define_comparison",
                    "Method selection is produced by the plan-generating registry tool.",
                ),
                _check(
                    "schema_validity",
                    _output(case4)["method_id"] == DEFAULT_METHOD_ID
                    and not _output(case4)["unsupported_assumptions"]
                    and "Matched donors" in _output(case4)["donor_handling"],
                    "Selected supported donor-aware paired difference method with assumptions.",
                ),
                _trace_check([case4]),
            ],
        ),
        _result(
            "case_hero_05_rank_proteins",
            case_specs,
            [case5_run, case5_rank],
            [
                _check(
                    "tool_choice",
                    [_trace_tool(case5_run), _trace_tool(case5_rank)]
                    == ["run_comparison", "rank_proteins"],
                    "Analysis and ranking ran through registry tools.",
                ),
                _numeric_top_rank_check(_output(case5_rank)["rows"][0]),
                _check(
                    "schema_validity",
                    _output(case5_run)["method_id"] == DEFAULT_METHOD_ID
                    and _output(case5_rank)["correction"].startswith("Benjamini-Hochberg"),
                    "Analysis result includes method, table ref, ranking, and correction.",
                ),
                _trace_check([case5_run, case5_rank]),
            ],
        ),
        _result(
            "case_hero_06_retrieve_evidence",
            case_specs,
            case6_searches,
            [
                _check(
                    "tool_choice",
                    all(_trace_tool(search) == "search_corpus" for search in case6_searches),
                    "All evidence retrieval used search_corpus.",
                ),
                _citation_check(case6_searches),
                _entity_grounding_check(case6_searches),
                _trace_check(case6_searches),
            ],
        ),
        _result(
            "case_hero_07_generate_report",
            case_specs,
            [case7_attach, case7_report],
            [
                _check(
                    "tool_choice",
                    [_trace_tool(case7_attach), _trace_tool(case7_report)]
                    == ["attach_evidence", "export_report"],
                    "Evidence attachment and report export ran through registry tools.",
                ),
                _report_structure_check(_output(case7_report)),
                _unsupported_claim_check(_output(case7_report)),
                _trace_check([case7_attach, case7_report]),
            ],
        ),
    ]


def _invoke(registry: Any, tool_name: str, payload: dict[str, Any], context: ToolContext) -> Any:
    return asyncio.run(registry.invoke(tool_name, payload, context))


def _result(
    case_id: str,
    case_specs: dict[str, dict[str, Any]],
    invocations: list[Any],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    expected_tools = [
        expectation["tool_name"]
        for expectation in case_specs[case_id]["expectations"]
        if expectation["tool_name"] is not None
    ]
    actual_tools = [_trace_tool(invocation) for invocation in invocations]
    stub_free = all(
        invocation.trace.status == "ok"
        and (
            invocation.trace.error is None
            or "not implemented in the ToolRegistry skeleton" not in invocation.trace.error.message
        )
        for invocation in invocations
    )
    checks = [
        _check(
            "tool_choice",
            actual_tools == expected_tools,
            f"Expected tool sequence {expected_tools}; observed {actual_tools}.",
        ),
        *checks,
        _check("schema_validity", stub_free, "No invoked tool returned a stubbed-tool error."),
    ]
    return {
        "case_id": case_id,
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "trace_step_ids": [invocation.trace.id for invocation in invocations],
    }


def _check(kind: str, passed: bool, detail: str | None) -> dict[str, Any]:
    return {"kind": kind, "passed": bool(passed), "detail": detail}


def _trace_check(invocations: list[Any]) -> dict[str, Any]:
    return _check(
        "trace_completeness",
        all(
            invocation.trace.id.startswith("tc_")
            and invocation.trace.status == "ok"
            and invocation.trace.eval_run_id is not None
            and invocation.trace.origin.surface == "eval"
            and invocation.trace.output is not None
            for invocation in invocations
        ),
        "Every registry invocation produced an eval-origin ToolCallTrace with output.",
    )


def _numeric_top_rank_check(row: dict[str, Any]) -> dict[str, Any]:
    passed = (
        row["protein"] == "TNF alpha"
        and _approx(row["effect_size"], -0.8155901585)
        and row["direction"] == "down"
        and _approx(row["p_value"], 0.03125)
        and _approx(row["q_value"], 0.036458333333333336)
        and _approx(row["donor_consistency"], 1.0)
    )
    return _check(
        "numeric",
        passed,
        "Top rank fields match fixture-derived effect size, p-value, q-value, and consistency.",
    )


def _citation_check(searches: list[Any]) -> dict[str, Any]:
    return _check(
        "citation_support",
        all(
            any(
                chunk["chunk"]["citation"].get("url") or chunk["chunk"]["citation"].get("doi")
                for chunk in _output(search)["chunks"]
            )
            for search in searches
        ),
        "Each retrieval step returned at least one cited approved chunk.",
    )


def _entity_grounding_check(searches: list[Any]) -> dict[str, Any]:
    return _check(
        "entity_grounding",
        all(
            any(chunk["matched_entities"] or chunk["chunk"]["entities"] for chunk in _output(search)["chunks"])
            for search in searches
        ),
        "Each retrieval step returned entity-grounded chunks.",
    )


def _report_structure_check(report: dict[str, Any]) -> dict[str, Any]:
    claim_kinds = {claim["kind"] for claim in report["claims"]}
    return _check(
        "report_structure",
        bool(report["markdown_ref"]["uri"].endswith(".md"))
        and {"data-derived", "source-derived", "interpretive", "limitation"}.issubset(
            claim_kinds
        ),
        "Report artifact has markdown ref and required claim types.",
    )


def _unsupported_claim_check(report: dict[str, Any]) -> dict[str, Any]:
    claims = report["claims"]
    unsupported_phrases = ("mechanism", "causes", "proves", "generalizes")
    source_claims_supported = all(
        claim["evidence_chunk_ids"]
        for claim in claims
        if claim["kind"] in {"source-derived", "interpretive"}
    )
    unsupported = any(
        phrase in claim["text"].lower()
        and "not as a demonstrated molecular mechanism" not in claim["text"].lower()
        for claim in claims
        for phrase in unsupported_phrases
    )
    return _check(
        "unsupported_claim",
        source_claims_supported and not unsupported,
        "Source-derived/interpretive claims are cited and avoid unsupported mechanisms.",
    )


def _retrieved_chunk_ids(searches: list[Any]) -> list[str]:
    chunk_ids: list[str] = []
    for search in searches:
        chunks = _output(search)["chunks"]
        if not chunks:
            continue
        chunk_ids.append(chunks[0]["chunk"]["id"])
    return chunk_ids


def _comparison_matches_hero(comparison: dict[str, Any]) -> bool:
    return all(comparison.get(key) == value for key, value in HERO_COMPARISON.items())


def _ok(invocation: Any) -> bool:
    return invocation.trace.status == "ok" and invocation.output is not None


def _output(invocation: Any) -> dict[str, Any]:
    if invocation.output is None:
        return {}
    return invocation.output.model_dump(mode="json")


def _trace_tool(invocation: Any) -> str:
    return invocation.trace.tool_name


def _approx(actual: float, expected: float, *, tolerance: float = 1e-9) -> bool:
    return abs(actual - expected) <= tolerance


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
