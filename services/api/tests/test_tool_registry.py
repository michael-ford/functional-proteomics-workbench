import asyncio
import csv
from typing import Literal

import pytest
from functional_proteomics_corpus import build_corpus_index, write_corpus_index
from pydantic import BaseModel, ConfigDict
from shared_schemas import AnalysisResult

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
            "get_project_status",
            {"project_id": "proj_demo"},
            trace_sink=sink,
        )
    )

    assert result.output is None
    assert result.error is not None
    assert result.error.code == "out_of_scope"
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
    assert output["chunks"][0]["source_id"] in {
        "src_dandrea_1993_il10",
        "src_wang_1995_il10_nfkb",
    }
    assert output["chunks"][0]["citation"]["doi"]
    assert output["chunks"][0]["matched_entities"]
    assert sink.traces[-1].tool_name == "search_corpus"
    assert sink.traces[-1].status == "ok"
    assert sink.traces[-1].output is not None
    assert sink.traces[-1].output["chunks"][0]["source_id"] == output["chunks"][0]["source_id"]
    assert sink.traces[-1].output["chunks"][0]["citation"]["doi"]


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
