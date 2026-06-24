"""Build committed demo artifacts consumed by the v0.1 web UI.

The web app renders these artifacts instead of hard-coding biological results in
React. Inputs come from the committed fixture, the seed script, the shared tool
registry, the corpus indexer, and the eval runner.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.runners.runner import run_eval_suite, validate_eval_run_report  # noqa: E402
from functional_proteomics_corpus import build_corpus_index, write_corpus_index  # noqa: E402
from fpw_api.tools import InMemoryTraceSink, ToolContext, TraceOrigin  # noqa: E402
from fpw_api.tools.mvp import DEMO_DATASET_ID, DEMO_PROJECT_ID, create_default_tool_registry  # noqa: E402
from fpw_api.traces import ToolCallTrace, export_tool_calls_jsonl  # noqa: E402
from scripts.seed_demo_project import seed_demo_project  # noqa: E402

ARTIFACT_ROOT = REPO_ROOT / "demo_data" / "artifacts"
FIXTURE_ROOT = REPO_ROOT / "demo_data"
WEB_STATE_PATH = ARTIFACT_ROOT / "web-demo-state.json"
TRACE_PATH = ARTIFACT_ROOT / "traces" / "tool_calls.jsonl"
EVAL_PATH = ARTIFACT_ROOT / "eval-smoke.json"

DEMO_ULID = "01K1M9M8J6T2P3R4S5T6V7W8X9"
CHAT_SESSION_ID = f"chat_{DEMO_ULID}"
CHAT_MESSAGE_ID = f"msg_{DEMO_ULID}"
EVAL_RUN_ID = f"eval_run_{DEMO_ULID}"

COMPARISON = {
    "group_a": {"perturbagen": "IL-10"},
    "group_b": {"perturbagen": "control"},
    "stimulation_context": "LPS",
    "paired_by": "donor",
}

EVIDENCE_QUERIES = [
    "What public dataset and assay does this demo use?",
    (
        "What evidence supports IL-10 dampening cytokine production in LPS or human "
        "immune-cell contexts?"
    ),
    "What context supports LPS-stimulated PBMC cytokine response interpretation?",
]


async def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        state_root = tmp_path / ".fpw_state"
        corpus_index_path = write_corpus_index(
            build_corpus_index(),
            tmp_path / "corpus-index.json",
        )
        seed_demo_project(state_root=state_root, fixture_root=FIXTURE_ROOT)
        project_dir = state_root / "projects" / DEMO_PROJECT_ID

        sink = InMemoryTraceSink()
        registry = create_default_tool_registry()
        context = ToolContext(
            origin=TraceOrigin(surface="web_chat", client="web"),
            trace_sink=sink,
            project_id=DEMO_PROJECT_ID,
            chat_session_id=CHAT_SESSION_ID,
            chat_message_id=CHAT_MESSAGE_ID,
            state={
                "state_root": str(state_root),
                "corpus_index_path": str(corpus_index_path),
            },
        )

        plan_result = await registry.invoke(
            "define_comparison",
            {
                "project_id": DEMO_PROJECT_ID,
                "dataset_id": DEMO_DATASET_ID,
                "comparison": COMPARISON,
            },
            context,
        )
        _require_output(plan_result.output, "define_comparison")

        analysis_result = await registry.invoke(
            "run_comparison",
            {"project_id": DEMO_PROJECT_ID, "plan_id": plan_result.output.id},
            context,
        )
        _require_output(analysis_result.output, "run_comparison")

        ranking_result = await registry.invoke(
            "rank_proteins",
            {"project_id": DEMO_PROJECT_ID, "result_id": analysis_result.output.id},
            context,
        )
        _require_output(ranking_result.output, "rank_proteins")

        evidence_results = []
        for query in EVIDENCE_QUERIES:
            evidence_result = await registry.invoke(
                "search_corpus",
                {"query": query, "k": 3},
                context,
            )
            _require_output(evidence_result.output, "search_corpus")
            evidence_results.append(
                {
                    "query": query,
                    "trace_id": evidence_result.trace.id,
                    "output": evidence_result.output.model_dump(mode="json"),
                }
            )

        eval_report, eval_trace_ids = await _build_eval_report_with_exported_traces(
            registry=registry,
            trace_sink=sink,
            corpus_index_path=corpus_index_path,
        )

        durable_traces = [
            ToolCallTrace.model_validate(trace.model_dump(mode="json")) for trace in sink.traces
        ]

        report = _build_report_artifact(
            analysis=analysis_result.output.model_dump(mode="json"),
            ranking=ranking_result.output.model_dump(mode="json"),
            evidence_results=evidence_results,
            analysis_trace_id=analysis_result.trace.id,
            ranking_trace_id=ranking_result.trace.id,
        )

        web_state = {
            "schema_version": "0.1.0",
            "generated_by": "scripts/build_demo_web_artifacts.py",
            "project": _read_json(project_dir / "project.json"),
            "dataset": _read_json(project_dir / "datasets" / "dataset.json"),
            "schema_profile": _read_json(project_dir / "datasets" / "schema_profile.json"),
            "validation": _read_json(project_dir / "datasets" / "validation.json"),
            "seed_manifest": _read_json(project_dir / "seed_manifest.json"),
            "analysis_plan": plan_result.output.model_dump(mode="json"),
            "analysis_result": analysis_result.output.model_dump(mode="json"),
            "ranking": ranking_result.output.model_dump(mode="json"),
            "evidence_results": evidence_results,
            "report": report,
            "eval_run": eval_report,
            "trace_export": {
                "path": "traces/tool_calls.jsonl",
                "count": len(durable_traces),
                "web_chat_trace_ids": [trace.id for trace in durable_traces if trace.origin.surface == "web_chat"],
                "eval_trace_ids": eval_trace_ids,
            },
        }

        if ARTIFACT_ROOT.exists():
            shutil.rmtree(ARTIFACT_ROOT)
        TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _write_json(WEB_STATE_PATH, web_state)
        _write_json(EVAL_PATH, eval_report)
        TRACE_PATH.write_text(export_tool_calls_jsonl(durable_traces), encoding="utf-8")

    print(f"wrote {WEB_STATE_PATH.relative_to(REPO_ROOT)}")
    print(f"wrote {TRACE_PATH.relative_to(REPO_ROOT)}")
    print(f"wrote {EVAL_PATH.relative_to(REPO_ROOT)}")
    return 0


async def _build_eval_report_with_exported_traces(
    *,
    registry: Any,
    trace_sink: InMemoryTraceSink,
    corpus_index_path: Path,
) -> tuple[dict[str, Any], list[str]]:
    eval_context = ToolContext(
        origin=TraceOrigin(surface="eval", client="offline-runner"),
        trace_sink=trace_sink,
        project_id=DEMO_PROJECT_ID,
        eval_run_id=EVAL_RUN_ID,
        state={"corpus_index_path": str(corpus_index_path)},
    )
    trace_ids: list[str] = []
    for query in EVIDENCE_QUERIES:
        result = await registry.invoke("search_corpus", {"query": query, "k": 3}, eval_context)
        _require_output(result.output, "search_corpus")
        trace_ids.append(result.trace.id)

    report = await asyncio.to_thread(run_eval_suite, "smoke", run_id=EVAL_RUN_ID)
    for case in report["results"]:
        if case["case_id"] == "case_corpus_retrieval_smoke":
            case["trace_step_ids"] = trace_ids
    return validate_eval_run_report(report), trace_ids


def _build_report_artifact(
    *,
    analysis: dict[str, Any],
    ranking: dict[str, Any],
    evidence_results: list[dict[str, Any]],
    analysis_trace_id: str,
    ranking_trace_id: str,
) -> dict[str, Any]:
    rows = ranking["rows"]
    top_rows = rows[:6]
    top_down = [row for row in top_rows if row["direction"] == "down"]
    evidence = _flatten_evidence(evidence_results)
    citations = _unique_citations(evidence)
    top_names = ", ".join(row["protein"] for row in top_rows[:3])

    return {
        "id": "report_demo_il10_lps",
        "schema_version": "0.1.0",
        "project_id": DEMO_PROJECT_ID,
        "title": "IL-10 vs matched control under LPS 2000 ng/mL",
        "subtitle": "Conservative demo report generated from the seeded public Perturb-PBMC fixture.",
        "generated_from": {
            "analysis_result_id": analysis["id"],
            "analysis_trace_id": analysis_trace_id,
            "ranking_trace_id": ranking_trace_id,
            "evidence_trace_ids": [result["trace_id"] for result in evidence_results],
        },
        "summary": (
            f"The donor-aware paired analysis ranks {top_names} as the largest response-value "
            "changes in the IL-10 condition versus matched no-cytokine controls. The display "
            "treats p/q values as exploratory and emphasizes effect size plus donor consistency."
        ),
        "claims": [
            {
                "kind": "data_derived",
                "label": "Ranked fixture result",
                "text": (
                    f"{len(top_down)}/{len(top_rows)} of the top ranked proteins decrease under "
                    "IL-10 in the seeded LPS comparison; each row is computed from donor-level "
                    "paired differences."
                ),
                "support": [
                    {"type": "analysis_result", "id": analysis["id"], "trace_id": analysis_trace_id},
                    {"type": "ranking", "trace_id": ranking_trace_id},
                ],
            },
            {
                "kind": "source_derived",
                "label": "Dataset and assay provenance",
                "text": (
                    "The selected fixture is tied to the public Perturb-PBMC/nELISA-PBMC source "
                    "lineage and an nELISA assay context source approved for demo claims."
                ),
                "support": _citation_support(citations, ["src_nomic_perturb_pbmc", "src_nelisa_pbmc_repo", "src_dagher_2025_nelisa"]),
            },
            {
                "kind": "interpretive",
                "label": "Conservative biological readout",
                "text": (
                    "The result supports a descriptive readout of IL-10-associated dampening "
                    "across LPS inflammatory-response proteins in this fixture; it does not "
                    "establish a mechanism or generalize beyond the demo subset."
                ),
                "support": [
                    {"type": "analysis_result", "id": analysis["id"], "trace_id": analysis_trace_id},
                    *_citation_support(citations, ["src_dandrea_1993_il10", "src_wang_1995_il10_nfkb"]),
                ],
            },
        ],
        "limitations": [
            "The donor count is small; exploratory p/q values should not be treated as hard significance calls.",
            "The fixture carries public H5AD normalized_response values verbatim and is not renormalized in v0.1.",
            "The report is descriptive and source-grounded; mechanistic claims are out of scope.",
        ],
        "citations": citations,
    }


def _flatten_evidence(evidence_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for result in evidence_results:
        for chunk in result["output"]["chunks"]:
            chunks.append({**chunk, "query": result["query"], "trace_id": result["trace_id"]})
    return chunks


def _unique_citations(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: dict[str, dict[str, Any]] = {}
    for item in evidence:
        metadata = item["metadata"]
        chunk = item["chunk"]
        source_id = metadata["source_id"]
        citations.setdefault(
            source_id,
            {
                "source_id": source_id,
                "title": metadata["title"],
                "source_type": metadata["source_type"],
                "source_locator": metadata["source_locator"],
                "url": chunk["citation"].get("url"),
                "doi": chunk["citation"].get("doi"),
                "trace_id": item["trace_id"],
                "approved_for_claims": metadata["approved_for_claims"],
            },
        )
    return sorted(citations.values(), key=lambda citation: citation["source_id"])


def _citation_support(citations: list[dict[str, Any]], source_ids: list[str]) -> list[dict[str, Any]]:
    by_source_id = {citation["source_id"]: citation for citation in citations}
    return [
        {
            "type": "citation",
            "source_id": source_id,
            "title": by_source_id[source_id]["title"],
            "trace_id": by_source_id[source_id]["trace_id"],
        }
        for source_id in source_ids
        if source_id in by_source_id
    ]


def _require_output(output: Any, tool_name: str) -> None:
    if output is None:
        raise RuntimeError(f"{tool_name} did not produce output")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
