import { EvalRunPanel, MetricTile, StatusBadge } from "@/components/demo-artifact-ui";
import { GitBranch, ListChecks, PageHeader, Panel, PanelTitle, StatusPill } from "@/components/workspace-shell";
import { formatPercent, getDemoWorkspace } from "@/lib/demo-workspace";

export default function EvalsPage() {
  const workspace = getDemoWorkspace();
  const evalRun = workspace.eval_run;
  const tracesById = new Map(workspace.traces.map((trace) => [trace.id, trace]));
  const checks = evalRun.results.flatMap((result) => result.checks);
  const passedChecks = checks.filter((check) => check.passed).length;
  const traceStepCount = evalRun.results.reduce((count, result) => count + result.trace_step_ids.length, 0);

  return (
    <>
      <PageHeader
        eyebrow="Eval dashboard"
        title="Workflow correctness checks"
        description="Latest deterministic smoke eval with per-case checks and replay trace IDs from the exported log."
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricTile label="Score" value={formatPercent(evalRun.score)} detail={`${evalRun.suite} · ${evalRun.mode}`} tone="success" />
        <MetricTile label="Cases" value={String(evalRun.results.length)} detail={`${evalRun.results.filter((result) => result.passed).length} passed`} tone="accent" />
        <MetricTile label="Checks" value={`${passedChecks}/${checks.length}`} detail="All visible with verdicts" tone="success" />
        <MetricTile label="Replay traces" value={String(traceStepCount)} detail="Trace-backed eval steps" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_22rem]">
        <Panel>
          <PanelTitle icon={ListChecks} title="Eval cases" meta={evalRun.id} />
          <EvalRunPanel evalRun={evalRun} tracesById={tracesById} />
          <div className="border-t border-border px-4 py-3">
            <StatusPill>Created {new Date(evalRun.created_at).toISOString()}</StatusPill>
          </div>
        </Panel>

        <Panel>
          <PanelTitle icon={GitBranch} title="Replay coverage" meta="trace model" />
          <div className="divide-y divide-border">
            {evalRun.results.map((result) => (
              <div key={result.case_id} className="px-4 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge tone={result.passed ? "success" : "error"}>
                    {result.passed ? "passed" : "failed"}
                  </StatusBadge>
                  <span className="font-mono text-xs text-muted">{result.case_id}</span>
                </div>
                <p className="mt-3 text-sm leading-6 text-muted">
                  {result.trace_step_ids.length
                    ? `${result.trace_step_ids.length} replay step IDs are present in the exported trace log.`
                    : "This smoke envelope case records an explicit empty trace list."}
                </p>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </>
  );
}
