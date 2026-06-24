import {
  BarChart3,
  Database,
  FileText,
  GitBranch,
  PageHeader,
  Panel,
  PanelTitle,
  StatusPill,
} from "@/components/workspace-shell";
import { EffectPlot, MetricTile, RankedProteinTable, StatusBadge, TraceTable } from "@/components/demo-artifact-ui";
import { formatBytes, formatNumber, formatPercent, getDemoWorkspace } from "@/lib/demo-workspace";

export default function ProjectDashboardPage() {
  const workspace = getDemoWorkspace();
  const topRows = workspace.ranking.rows.slice(0, 8);
  const topDecrease = workspace.ranking.rows[0];
  const donors = workspace.analysis_result.donor_consistency.length;
  const proteins = workspace.ranking.rows.length;
  const validationTone = workspace.dataset.validation.status === "passed" ? "success" : "error";

  return (
    <>
      <PageHeader
        eyebrow="Project dashboard"
        title={workspace.project.title}
        description="Seeded IL-10/LPS public subset with matched donor controls, analysis artifacts, report claims, traces, and eval replay."
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricTile
          label="Dataset rows"
          value={String(workspace.dataset.validation.row_count)}
          detail={`${donors} matched donors · ${proteins} proteins`}
          tone="accent"
        />
        <MetricTile
          label="Top paired effect"
          value={formatNumber(topDecrease.effect_size, 3)}
          detail={`${topDecrease.protein} · ${formatPercent(topDecrease.donor_consistency)} donor consistency`}
          tone="warning"
        />
        <MetricTile
          label="Trace export"
          value={String(workspace.trace_export.count)}
          detail="Tool calls from web and eval surfaces"
          tone="success"
        />
        <MetricTile
          label="Eval score"
          value={formatPercent(workspace.eval_run.score)}
          detail={`${workspace.eval_run.suite} · ${workspace.eval_run.mode}`}
          tone="success"
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <Panel>
          <PanelTitle icon={Database} title="Project state" meta={workspace.project.id} />
          <div className="grid gap-px bg-border sm:grid-cols-3">
            {[
              ["Dataset", workspace.dataset.name],
              ["Analysis method", workspace.analysis_plan.method_id],
              ["Result artifact", workspace.analysis_result.id],
            ].map(([label, value]) => (
              <div key={label} className="bg-surface p-4">
                <p className="text-xs font-semibold uppercase text-muted">{label}</p>
                <p className="mt-3 break-words text-sm font-semibold leading-5">{value}</p>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-2 border-t border-border px-4 py-3 text-sm">
            <StatusBadge tone={validationTone}>{workspace.dataset.validation.status}</StatusBadge>
            <span className="text-muted">
              {workspace.seed_manifest.source_file} · {formatBytes(workspace.dataset.raw_ref.bytes)}
            </span>
          </div>
        </Panel>

        <Panel>
          <PanelTitle icon={GitBranch} title="Agent handoff" meta={workspace.analysis_plan.id} />
          <div className="divide-y divide-border text-sm">
            {[
              ["Comparison", "IL-10 vs matched no-cytokine control"],
              ["Stimulation", workspace.analysis_plan.comparison.stimulation_context],
              ["Paired by", workspace.analysis_plan.comparison.paired_by],
              ["Report", workspace.report.id],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between gap-4 px-4 py-3">
                <span className="font-medium">{label}</span>
                <span className="max-w-[62%] break-words text-right text-muted">{value}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="mt-4 grid gap-4">
        <Panel>
          <PanelTitle icon={BarChart3} title="Effect plot" meta="real analysis artifact" />
          <div className="px-4 py-4">
            <EffectPlot rows={workspace.ranking.rows} />
          </div>
        </Panel>

        <Panel>
          <PanelTitle icon={BarChart3} title="Ranked proteins" meta={workspace.ranking.metric} />
          <RankedProteinTable rows={topRows} />
          <div className="border-t border-border px-4 py-3">
            <StatusPill>{workspace.ranking.correction}</StatusPill>
          </div>
        </Panel>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[0.85fr_1.15fr]">
        <Panel>
          <PanelTitle icon={FileText} title="Report readout" meta={workspace.report.id} />
          <div className="divide-y divide-border">
            {workspace.report.claims.map((claim) => (
              <div key={claim.label} className="px-4 py-4">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge tone={claim.kind === "data_derived" ? "accent" : "neutral"}>
                    {claim.kind.replace("_", " ")}
                  </StatusBadge>
                  <span className="text-sm font-semibold">{claim.label}</span>
                </div>
                <p className="mt-2 text-sm leading-6 text-muted">{claim.text}</p>
              </div>
            ))}
          </div>
        </Panel>

        <Panel>
          <PanelTitle icon={GitBranch} title="Recent tool traces" meta="trace model export" />
          <TraceTable traces={workspace.traces} limit={5} />
        </Panel>
      </div>
    </>
  );
}
