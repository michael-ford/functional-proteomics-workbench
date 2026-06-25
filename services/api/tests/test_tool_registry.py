import asyncio
import csv
from datetime import UTC, datetime
from typing import Literal

import pytest
from functional_proteomics_corpus import build_corpus_index, write_corpus_index
from pydantic import BaseModel, ConfigDict
from shared_schemas import AnalysisResult, EvidenceChunk

from fpw_api import create_app
from fpw_api.tools import (
    InMemoryTraceSink,
    ToolContext,
    ToolDefinition,
    ToolPermissions,
    ToolRegistry,
    ToolRegistryError,
    TraceOrigin,
    TracePolicy,
    create_default_tool_registry,
    invoke_for_mcp,
    invoke_for_web_chat,
)
from fpw_api.tools.mvp import DEMO_DATASET_ID

MVP_TOOL_NAMES = {
    "create_project",
    "get_project_status",
    "create_upload_url",
    "validate_dataset",
    "inspect_dataset_schema",
    "define_comparison",
    "run_comparison",
    "rank_proteins",
    "create_plot",
    "search_corpus",
    "attach_evidence",
    "export_report",
    "run_eval_suite",
    "get_trace",
}


class ProbeToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int
    project_id: str | None = None
    secret: str | None = None


class ProbeToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: int
    surface: Literal["web_chat", "mcp", "eval", "api"]
    secret: str | None = None


def test_default_registry_registers_frozen_mvp_tool_names() -> None:
    registry = create_default_tool_registry()

    names = {definition.name for definition in registry.list_definitions()}

    assert names == MVP_TOOL_NAMES
    assert registry.lookup("create_project").permissions.mutates_state is True
    assert registry.lookup("search_corpus").permissions.reads_corpus is True
    assert registry.lookup("run_eval_suite").permissions.scope == "global"


def test_registry_rejects_duplicate_registration() -> None:
    registry = ToolRegistry()
    definition = _probe_definition(lambda tool_input, context: _probe_output(tool_input, context))

    registry.register(definition)

    with pytest.raises(ToolRegistryError, match="tool already registered"):
        registry.register(definition)


def test_create_app_attaches_one_shared_registry_instance() -> None:
    registry = create_default_tool_registry()

    app = create_app(tool_registry=registry)

    assert app.state.tool_registry is registry


def test_registry_invocation_validates_output_and_records_redacted_trace() -> None:
    registry = ToolRegistry()
    registry.register(
        _probe_definition(lambda tool_input, context: _probe_output(tool_input, context))
    )
    sink = InMemoryTraceSink()

    result = asyncio.run(
        registry.invoke(
            "probe",
            {"value": 7, "secret": "token"},
            ToolContext(
                origin=TraceOrigin(surface="api", client="pytest"),
                trace_sink=sink,
                project_id="proj_demo",
            ),
        )
    )

    assert isinstance(result.output, ProbeToolOutput)
    assert result.output.value == 7
    assert result.output.surface == "api"
    assert len(sink.traces) == 1
    assert sink.traces[0] == result.trace
    assert result.trace.id.startswith("tc_")
    assert result.trace.status == "ok"
    assert result.trace.project_id == "proj_demo"
    assert result.trace.input["secret"] == "[redacted]"
    assert result.trace.output is not None
    assert result.trace.output["secret"] == "[redacted]"


def test_registry_records_invalid_input_trace_without_calling_handler() -> None:
    calls = 0

    def handler(tool_input: BaseModel, context: ToolContext) -> ProbeToolOutput:
        nonlocal calls
        calls += 1
        return _probe_output(tool_input, context)

    registry = ToolRegistry()
    registry.register(_probe_definition(handler))
    sink = InMemoryTraceSink()

    result = asyncio.run(
        registry.invoke(
            "probe",
            {"value": "not-an-int"},
            ToolContext(origin=TraceOrigin(surface="api"), trace_sink=sink),
        )
    )

    assert calls == 0
    assert result.output is None
    assert result.error is not None
    assert result.error.code == "invalid_input"
    assert result.trace.status == "error"
    assert sink.traces == [result.trace]


def test_project_scoped_tool_trace_uses_validated_input_project_id() -> None:
    registry = create_default_tool_registry()
    sink = InMemoryTraceSink()

    result = asyncio.run(
        invoke_for_web_chat(
            registry,
            "validate_dataset",
            {
                "project_id": "proj_demo",
                "dataset_id": "ds_01KCYAG0000000000000000000",
            },
            trace_sink=sink,
        )
    )

    assert result.error is None
    assert result.output is not None
    assert result.trace.project_id == "proj_demo"
    assert sink.traces == [result.trace]


def test_project_scoped_tool_rejects_context_input_project_id_mismatch() -> None:
    calls = 0

    def handler(tool_input: BaseModel, context: ToolContext) -> ProbeToolOutput:
        nonlocal calls
        calls += 1
        return _probe_output(tool_input, context)

    registry = ToolRegistry()
    registry.register(_probe_definition(handler))
    sink = InMemoryTraceSink()

    result = asyncio.run(
        registry.invoke(
            "probe",
            {"value": 1, "project_id": "proj_input"},
            ToolContext(
                origin=TraceOrigin(surface="api"),
                trace_sink=sink,
                project_id="proj_context",
            ),
        )
    )

    assert calls == 0
    assert result.output is None
    assert result.error is not None
    assert result.error.code == "invalid_input"
    assert result.trace.project_id == "proj_context"
    assert sink.traces == [result.trace]


def test_project_scoped_tool_without_input_project_id_requires_context() -> None:
    registry = create_default_tool_registry()
    sink = InMemoryTraceSink()

    result = asyncio.run(
        invoke_for_mcp(
            registry,
            "search_corpus",
            {"query": "IL-10"},
            trace_sink=sink,
            client="codex",
        )
    )

    assert result.output is None
    assert result.error is not None
    assert result.error.code == "invalid_input"
    assert result.trace.project_id is None
    assert result.trace.origin.surface == "mcp"
    assert sink.traces == [result.trace]


def test_registry_records_invalid_output_as_internal_error() -> None:
    registry = ToolRegistry()
    registry.register(_probe_definition(lambda _tool_input, _context: {"value": "bad"}))
    sink = InMemoryTraceSink()

    result = asyncio.run(
        registry.invoke(
            "probe",
            {"value": 1, "project_id": "proj_demo"},
            ToolContext(origin=TraceOrigin(surface="api"), trace_sink=sink),
        )
    )

    assert result.output is None
    assert result.error is not None
    assert result.error.code == "internal_error"
    assert result.trace.project_id == "proj_demo"
    assert result.trace.input == {
        "value": 1,
        "project_id": "proj_demo",
        "secret": "[redacted]",
    }
    assert result.trace.output is None
    assert sink.traces == [result.trace]


def test_web_and_mcp_adapters_call_the_same_registered_handler() -> None:
    surfaces: list[str] = []

    def handler(tool_input: BaseModel, context: ToolContext) -> ProbeToolOutput:
        surfaces.append(context.origin.surface)
        return _probe_output(tool_input, context)

    registry = ToolRegistry()
    definition = _probe_definition(handler)
    registry.register(definition)
    sink = InMemoryTraceSink()

    web_result = asyncio.run(
        invoke_for_web_chat(
            registry,
            "probe",
            {"value": 1},
            trace_sink=sink,
            project_id="proj_demo",
            chat_session_id="chat_1",
        )
    )
    mcp_result = asyncio.run(
        invoke_for_mcp(
            registry,
            "probe",
            {"value": 2},
            trace_sink=sink,
            project_id="proj_demo",
            client="codex",
            token_id="demo-token",
        )
    )

    assert registry.lookup("probe").handler is definition.handler
    assert surfaces == ["web_chat", "mcp"]
    web_output = ProbeToolOutput.model_validate(web_result.output)
    mcp_output = ProbeToolOutput.model_validate(mcp_result.output)
    assert web_output.surface == "web_chat"
    assert mcp_output.surface == "mcp"
    assert [trace.origin.surface for trace in sink.traces] == ["web_chat", "mcp"]


def test_analysis_tools_create_traced_plan_result_and_ranking_artifact(tmp_path) -> None:
    registry = create_default_tool_registry()
    sink = InMemoryTraceSink()
    context = ToolContext(
        origin=TraceOrigin(surface="api", client="pytest"),
        trace_sink=sink,
        project_id="proj_demo",
        state={"state_root": tmp_path},
    )
    comparison = {
        "group_a": {"perturbagen": "IL-10"},
        "group_b": {"perturbagen": "control"},
        "stimulation_context": "LPS",
        "paired_by": "donor",
    }

    plan_result = asyncio.run(
        registry.invoke(
            "define_comparison",
            {
                "project_id": "proj_demo",
                "dataset_id": DEMO_DATASET_ID,
                "comparison": comparison,
            },
            context,
        )
    )
    assert plan_result.error is None
    assert plan_result.output is not None
    plan = plan_result.output.model_dump(mode="json")
    assert plan["method_id"] == "donor_aware_paired_difference"
    assert "Matched donors" in plan["donor_handling"]
    assert plan["limitations"]

    comparison_result = asyncio.run(
        registry.invoke(
            "run_comparison",
            {"project_id": "proj_demo", "plan_id": plan["id"]},
            context,
        )
    )

    assert comparison_result.error is None
    assert comparison_result.output is not None
    result = comparison_result.output.model_dump(mode="json")
    assert result["ranking"]["rows"][0]["protein"] == "TNF alpha"
    assert result["ranking"]["rows"][0]["q_value"] == pytest.approx(0.036458333333333336)
    assert len(result["donor_consistency"]) == 6
    AnalysisResult.model_validate(result)
    table_uri = result["table_ref"]["uri"]
    assert table_uri.startswith("project://proj_demo/analysis/results/res_")
    table_path = (
        tmp_path / "projects" / "proj_demo" / "analysis" / "results" / f"{result['id']}.csv"
    )
    with table_path.open(newline="", encoding="utf-8") as handle:
        table_rows = list(csv.DictReader(handle))
    assert table_rows[0]["protein"] == "TNF alpha"
    assert table_rows[0]["donor_count"] == "6"

    ranking_result = asyncio.run(
        registry.invoke(
            "rank_proteins",
            {"project_id": "proj_demo", "result_id": result["id"]},
            context,
        )
    )
    assert ranking_result.error is None
    assert ranking_result.output is not None
    assert ranking_result.output.model_dump(mode="json") == result["ranking"]
    assert [trace.tool_name for trace in sink.traces[-3:]] == [
        "define_comparison",
        "run_comparison",
        "rank_proteins",
    ]
    assert all(trace.status == "ok" for trace in sink.traces[-3:])
    assert all(trace.project_id == "proj_demo" for trace in sink.traces[-3:])


def test_registry_only_hero_replay_creates_artifacts_and_project_trace(tmp_path) -> None:
    index_path = write_corpus_index(build_corpus_index(), tmp_path / "corpus-index.json")
    registry = create_default_tool_registry()
    sink = InMemoryTraceSink()
    context = ToolContext(
        origin=TraceOrigin(surface="api", client="pytest"),
        trace_sink=sink,
        state={"state_root": tmp_path, "corpus_index_path": index_path},
    )
    comparison = {
        "group_a": {"perturbagen": "IL-10"},
        "group_b": {"perturbagen": "control"},
        "stimulation_context": "LPS",
        "paired_by": "donor",
    }

    project_result = asyncio.run(
        registry.invoke("create_project", {"title": "Fixture demo"}, context)
    )
    assert project_result.error is None
    assert project_result.output is not None
    project_output = project_result.output.model_dump(mode="json")
    project_id = project_output["project_id"]
    context = ToolContext(
        origin=TraceOrigin(surface="api", client="pytest"),
        trace_sink=sink,
        project_id=project_id,
        state=context.state,
    )

    upload_result = asyncio.run(
        registry.invoke("create_upload_url", {"project_id": project_id}, context)
    )
    validation_result = asyncio.run(
        registry.invoke(
            "validate_dataset",
            {"project_id": project_id, "dataset_id": DEMO_DATASET_ID},
            context,
        )
    )
    schema_result = asyncio.run(
        registry.invoke(
            "inspect_dataset_schema",
            {"project_id": project_id, "dataset_id": DEMO_DATASET_ID},
            context,
        )
    )
    plan_result = asyncio.run(
        registry.invoke(
            "define_comparison",
            {
                "project_id": project_id,
                "dataset_id": DEMO_DATASET_ID,
                "comparison": comparison,
            },
            context,
        )
    )
    assert plan_result.output is not None
    plan_output = plan_result.output.model_dump(mode="json")
    comparison_result = asyncio.run(
        registry.invoke(
            "run_comparison",
            {"project_id": project_id, "plan_id": plan_output["id"]},
            context,
        )
    )
    assert comparison_result.output is not None
    comparison_output = comparison_result.output.model_dump(mode="json")
    ranking_result = asyncio.run(
        registry.invoke(
            "rank_proteins",
            {"project_id": project_id, "result_id": comparison_output["id"]},
            context,
        )
    )
    plot_result = asyncio.run(
        registry.invoke(
            "create_plot",
            {
                "project_id": project_id,
                "result_id": comparison_output["id"],
                "plot_type": "ranked_effect_bar",
            },
            context,
        )
    )
    corpus_result = asyncio.run(
        registry.invoke(
            "search_corpus",
            {
                "query": "IL-10 dampens LPS cytokine production",
                "entities": ["IL-10", "LPS"],
                "k": 2,
            },
            context,
        )
    )
    assert corpus_result.output is not None
    corpus_output = corpus_result.output.model_dump(mode="json")
    chunk_ids = [
        scored["chunk"]["id"]
        for scored in corpus_output["chunks"]
        if scored["metadata"]["approved_for_claims"]
    ][:2]
    attach_result = asyncio.run(
        registry.invoke(
            "attach_evidence",
            {"project_id": project_id, "chunk_ids": chunk_ids},
            context,
        )
    )
    assert attach_result.output is not None
    attach_output = attach_result.output.model_dump(mode="json")
    report_result = asyncio.run(
        registry.invoke(
            "export_report",
            {
                "project_id": project_id,
                "result_id": comparison_output["id"],
                "attachment_ids": [attach_output["id"]],
            },
            context,
        )
    )
    eval_result = asyncio.run(
        registry.invoke("run_eval_suite", {"suite": "smoke"}, context)
    )
    trace_result = asyncio.run(
        registry.invoke("get_trace", {"project_id": project_id}, context)
    )

    for result in [
        upload_result,
        validation_result,
        schema_result,
        ranking_result,
        plot_result,
        report_result,
        eval_result,
        trace_result,
    ]:
        assert result.error is None
        assert result.output is not None
    assert validation_result.output is not None
    assert upload_result.output is not None
    assert schema_result.output is not None
    assert plot_result.output is not None
    assert report_result.output is not None
    assert eval_result.output is not None
    assert trace_result.output is not None
    upload_output = upload_result.output.model_dump(mode="json")
    validation_output = validation_result.output.model_dump(mode="json")
    schema_output = schema_result.output.model_dump(mode="json")
    plot_output = plot_result.output.model_dump(mode="json")
    report_output = report_result.output.model_dump(mode="json")
    eval_output = eval_result.output.model_dump(mode="json")
    expires_at = datetime.fromisoformat(upload_output["expires_at"].replace("Z", "+00:00"))
    assert expires_at > datetime.now(UTC)
    assert validation_output["status"] == "passed"
    assert schema_output["detected_axes"]["perturbagen"] == "perturbagen"
    assert plot_output["spec_ref"]["uri"].endswith(".json")
    assert report_output["claims"][1]["kind"] == "source-derived"
    assert report_output["claims"][1]["evidence_chunk_ids"]
    assert eval_output["status"] == "passed"
    trace_output = trace_result.output.model_dump(mode="json")
    tool_names = [trace["tool_name"] for trace in trace_output["traces"]]
    assert tool_names == [
        "create_project",
        "create_upload_url",
        "validate_dataset",
        "inspect_dataset_schema",
        "define_comparison",
        "run_comparison",
        "rank_proteins",
        "create_plot",
        "search_corpus",
        "attach_evidence",
        "export_report",
    ]
    assert all(trace["status"] == "ok" for trace in trace_output["traces"])
    dataset_root = tmp_path / "projects" / project_id / "datasets"
    assert (dataset_root / "raw" / "nelisa_pbmc_il10_lps_subset.csv").exists()
    assert (dataset_root / "raw" / "provenance.json").exists()
    assert (dataset_root / "normalized" / "nelisa_pbmc_il10_lps_long.parquet").exists()
    plot_path = tmp_path / "projects" / project_id / "analysis" / "plots"
    report_path = tmp_path / "projects" / project_id / "reports"
    assert any(plot_path.glob("plot_*.json"))
    assert any(report_path.glob("rep_*.md"))


def test_validate_dataset_rejects_out_of_scope_dataset() -> None:
    registry = create_default_tool_registry()
    sink = InMemoryTraceSink()

    result = asyncio.run(
        registry.invoke(
            "validate_dataset",
            {"project_id": "proj_demo", "dataset_id": "ds_01KCYAG0000000000000000001"},
            ToolContext(origin=TraceOrigin(surface="api", client="pytest"), trace_sink=sink),
        )
    )

    assert result.output is None
    assert result.error is not None
    assert result.error.code == "out_of_scope"


def test_inspect_dataset_schema_does_not_mutate_project_state(tmp_path) -> None:
    registry = create_default_tool_registry()
    sink = InMemoryTraceSink()

    result = asyncio.run(
        registry.invoke(
            "inspect_dataset_schema",
            {"project_id": "proj_demo", "dataset_id": DEMO_DATASET_ID},
            ToolContext(
                origin=TraceOrigin(surface="api", client="pytest"),
                trace_sink=sink,
                state={"state_root": tmp_path},
            ),
        )
    )

    assert result.error is None
    assert result.output is not None
    output = result.output.model_dump(mode="json")
    assert output["layout"] == "long"
    assert not (tmp_path / "projects").exists()
    assert "projects" not in sink.traces[0].input


def test_create_plot_rejects_unsupported_plot_type(tmp_path) -> None:
    registry = create_default_tool_registry()
    sink = InMemoryTraceSink()
    context = ToolContext(
        origin=TraceOrigin(surface="api", client="pytest"),
        trace_sink=sink,
        project_id="proj_demo",
        state={"state_root": tmp_path},
    )
    comparison = {
        "group_a": {"perturbagen": "IL-10"},
        "group_b": {"perturbagen": "control"},
        "stimulation_context": "LPS",
        "paired_by": "donor",
    }
    plan_result = asyncio.run(
        registry.invoke(
            "define_comparison",
            {"project_id": "proj_demo", "dataset_id": DEMO_DATASET_ID, "comparison": comparison},
            context,
        )
    )
    assert plan_result.output is not None
    plan_output = plan_result.output.model_dump(mode="json")
    analysis_result = asyncio.run(
        registry.invoke(
            "run_comparison",
            {"project_id": "proj_demo", "plan_id": plan_output["id"]},
            context,
        )
    )
    assert analysis_result.output is not None
    analysis_output = analysis_result.output.model_dump(mode="json")

    result = asyncio.run(
        registry.invoke(
            "create_plot",
            {
                "project_id": "proj_demo",
                "result_id": analysis_output["id"],
                "plot_type": "heatmap",
            },
            context,
        )
    )

    assert result.output is None
    assert result.error is not None
    assert result.error.code == "unsupported_plot"


def test_create_plot_unknown_result_returns_not_found() -> None:
    registry = create_default_tool_registry()
    sink = InMemoryTraceSink()

    result = asyncio.run(
        registry.invoke(
            "create_plot",
            {
                "project_id": "proj_demo",
                "result_id": "res_01KCYAG0000000000000000000",
                "plot_type": "ranked_effect_bar",
            },
            ToolContext(origin=TraceOrigin(surface="api", client="pytest"), trace_sink=sink),
        )
    )

    assert result.output is None
    assert result.error is not None
    assert result.error.code == "not_found"
    assert result.trace.error is not None
    assert result.trace.error.code == "not_found"


def test_define_comparison_rejects_non_demo_project(tmp_path) -> None:
    registry = create_default_tool_registry()
    sink = InMemoryTraceSink()

    result = asyncio.run(
        registry.invoke(
            "define_comparison",
            {
                "project_id": "proj_other",
                "dataset_id": DEMO_DATASET_ID,
                "comparison": {
                    "group_a": {"perturbagen": "IL-10"},
                    "group_b": {"perturbagen": "control"},
                    "stimulation_context": "LPS",
                    "paired_by": "donor",
                },
            },
            ToolContext(
                origin=TraceOrigin(surface="api", client="pytest"),
                trace_sink=sink,
                state={"state_root": tmp_path},
            ),
        )
    )

    assert result.output is None
    assert result.error is not None
    assert result.error.code == "out_of_scope"
    assert not (tmp_path / "projects" / "proj_other").exists()


def test_define_comparison_rejects_unsupported_unpaired_assumption() -> None:
    registry = create_default_tool_registry()
    sink = InMemoryTraceSink()

    result = asyncio.run(
        registry.invoke(
            "define_comparison",
            {
                "project_id": "proj_demo",
                "dataset_id": DEMO_DATASET_ID,
                "comparison": {
                    "group_a": {"perturbagen": "IL-10"},
                    "group_b": {"perturbagen": "control"},
                    "stimulation_context": "LPS",
                    "paired_by": "sample_id",
                },
            },
            ToolContext(
                origin=TraceOrigin(surface="api", client="pytest"),
                trace_sink=sink,
                project_id="proj_demo",
            ),
        )
    )

    assert result.output is None
    assert result.error is not None
    assert result.error.code == "invalid_input"
    assert "paired_by='donor'" in result.error.message
    assert sink.traces[-1].tool_name == "define_comparison"
    assert sink.traces[-1].status == "error"


def test_search_corpus_reads_built_index_and_traces_citations(tmp_path) -> None:
    index_path = write_corpus_index(build_corpus_index(), tmp_path / "corpus-index.json")
    registry = create_default_tool_registry()
    sink = InMemoryTraceSink()

    result = asyncio.run(
        registry.invoke(
            "search_corpus",
            {
                "query": "What evidence supports IL-10 dampening cytokine production in LPS?",
                "entities": ["IL-10", "LPS"],
                "k": 2,
            },
            ToolContext(
                origin=TraceOrigin(surface="api", client="pytest"),
                trace_sink=sink,
                project_id="proj_demo",
                state={"corpus_index_path": index_path},
            ),
        )
    )

    assert result.error is None
    assert result.output is not None
    output = result.output.model_dump(mode="json")
    assert output["chunks"]
    first = output["chunks"][0]
    assert first["metadata"]["source_id"] in {
        "src_dandrea_1993_il10",
        "src_wang_1995_il10_nfkb",
    }
    EvidenceChunk.model_validate(first["chunk"])
    assert first["chunk"]["schema_version"] == "0.1.0"
    assert first["chunk"]["source_id"].startswith("src_")
    assert first["metadata"]["contract_source_id"] == first["chunk"]["source_id"]
    assert first["chunk"]["citation"]["doi"]
    assert first["matched_entities"]
    assert sink.traces[-1].tool_name == "search_corpus"
    assert sink.traces[-1].status == "ok"
    assert sink.traces[-1].output is not None
    assert (
        sink.traces[-1].output["chunks"][0]["metadata"]["source_id"]
        == first["metadata"]["source_id"]
    )
    assert sink.traces[-1].output["chunks"][0]["chunk"]["citation"]["doi"]


def test_search_corpus_fails_closed_before_index_build(tmp_path) -> None:
    registry = create_default_tool_registry()
    sink = InMemoryTraceSink()

    result = asyncio.run(
        registry.invoke(
            "search_corpus",
            {"query": "IL-10 evidence"},
            ToolContext(
                origin=TraceOrigin(surface="api", client="pytest"),
                trace_sink=sink,
                project_id="proj_demo",
                state={"corpus_index_path": tmp_path / "missing-index.json"},
            ),
        )
    )

    assert result.output is None
    assert result.error is not None
    assert result.error.code == "corpus_unindexed"
    assert sink.traces[-1].status == "error"


def _probe_definition(handler) -> ToolDefinition:
    return ToolDefinition(
        name="probe",
        description="Probe tool used by registry tests.",
        input_model=ProbeToolInput,
        output_model=ProbeToolOutput,
        error_codes=["invalid_input", "internal_error"],
        permissions=ToolPermissions(scope="project", mutates_state=False),
        trace=TracePolicy(redact_input_keys=["secret"], redact_output_keys=["secret"]),
        handler=handler,
    )


def _probe_output(tool_input: BaseModel, context: ToolContext) -> ProbeToolOutput:
    typed_input = ProbeToolInput.model_validate(tool_input)
    return ProbeToolOutput(
        value=typed_input.value,
        surface=context.origin.surface,
        secret=typed_input.secret,
    )
