from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from evals.runners import (
    REPORT_SCHEMA,
    EvalCaseConfigurationError,
    ReportValidationError,
    run_eval_suite,
    validate_eval_run_report,
)
from evals.runners.runner import HERO_CASE_IDS
from evals.runners.runner import main


class EvalRunnerTests(unittest.TestCase):
    def test_smoke_runner_returns_passing_eval_run_report(self) -> None:
        report = run_eval_suite(
            "smoke",
            created_at=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
            run_id="eval_run_test",
        )

        self.assertEqual(report["suite"], "deterministic-hero-workflow")
        self.assertEqual(report["mode"], "smoke")
        self.assertEqual(report["score"], 1.0)
        case_ids = [result["case_id"] for result in report["results"]]
        self.assertEqual(case_ids, list(HERO_CASE_IDS))
        self.assertTrue(all(result["trace_step_ids"] for result in report["results"]))
        rank_result = next(
            result
            for result in report["results"]
            if result["case_id"] == "case_hero_05_rank_proteins"
        )
        self.assertTrue(
            any(check["kind"] == "numeric" and check["passed"] for check in rank_result["checks"])
        )
        report_result = next(
            result
            for result in report["results"]
            if result["case_id"] == "case_hero_07_generate_report"
        )
        self.assertTrue(
            any(
                check["kind"] == "unsupported_claim" and check["passed"]
                for check in report_result["checks"]
            )
        )

    def test_report_schema_documents_eval_run_shape(self) -> None:
        self.assertEqual(
            REPORT_SCHEMA["required"],
            ["id", "suite", "mode", "results", "score", "created_at"],
        )
        result_schema = REPORT_SCHEMA["properties"]["results"]["items"]
        self.assertIn("trace_step_ids", result_schema["required"])
        check_schema = result_schema["properties"]["checks"]["items"]
        self.assertIn("schema_validity", check_schema["properties"]["kind"]["enum"])

    def test_report_schema_validation_rejects_missing_required_fields(self) -> None:
        report = run_eval_suite(
            "smoke",
            created_at=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
            run_id="eval_run_test",
        )
        del report["score"]

        with self.assertRaisesRegex(ReportValidationError, "missing required keys"):
            validate_eval_run_report(report)

    def test_report_schema_validation_rejects_inconsistent_score(self) -> None:
        report = run_eval_suite(
            "smoke",
            created_at=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
            run_id="eval_run_test",
        )
        report["score"] = 0.5

        with self.assertRaisesRegex(ReportValidationError, "passed cases / total cases"):
            validate_eval_run_report(report)

    def test_smoke_runner_rejects_missing_required_hero_case(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cases_dir = Path(tmpdir)
            source_dir = Path(__file__).resolve().parents[1] / "cases"
            for source in source_dir.glob("*.json"):
                if source.name != "case_hero_07_generate_report.json":
                    (cases_dir / source.name).write_text(
                        source.read_text(encoding="utf-8"),
                        encoding="utf-8",
                    )

            with self.assertRaisesRegex(EvalCaseConfigurationError, "missing required"):
                run_eval_suite(
                    "smoke",
                    created_at=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
                    run_id="eval_run_test",
                    cases_dir=cases_dir,
                )

    def test_cli_writes_machine_readable_report_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "eval-smoke.json"

            exit_code = main(["--mode", "smoke", "--output", str(output)])

            self.assertEqual(exit_code, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            validate_eval_run_report(report)
            self.assertEqual(report["mode"], "smoke")


if __name__ == "__main__":
    unittest.main()
