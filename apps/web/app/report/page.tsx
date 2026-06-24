import { CitationList, ClaimList, MetricTile, StatusBadge } from "@/components/demo-artifact-ui";
import { FileText, GitBranch, PageHeader, Panel, PanelTitle } from "@/components/workspace-shell";
import { formatPercent, getDemoWorkspace } from "@/lib/demo-workspace";

export default function ReportPage() {
  const workspace = getDemoWorkspace();
  const report = workspace.report;
  const dataClaims = report.claims.filter((claim) => claim.kind === "data_derived").length;
  const sourceClaims = report.claims.filter((claim) => claim.kind === "source_derived").length;
  const interpretiveClaims = report.claims.filter((claim) => claim.kind === "interpretive").length;

  return (
    <>
      <PageHeader
        eyebrow="Analysis report"
        title={report.title}
        description={report.subtitle}
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricTile label="Claims" value={String(report.claims.length)} detail={`${dataClaims} data · ${sourceClaims} source · ${interpretiveClaims} interpretive`} tone="accent" />
        <MetricTile label="Citations" value={String(report.citations.length)} detail="Approved deterministic corpus sources" tone="success" />
        <MetricTile label="Eval score" value={formatPercent(workspace.eval_run.score)} detail={workspace.eval_run.suite} tone="success" />
        <MetricTile label="Trace-backed" value={String(Object.keys(report.generated_from).length)} detail="Report generation inputs" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_24rem]">
        <Panel className="min-h-[34rem]">
          <PanelTitle icon={FileText} title="Findings" meta={report.id} />
          <div className="border-b border-border px-4 py-4">
            <StatusBadge tone="accent">Conservative report</StatusBadge>
            <p className="mt-3 text-sm leading-6 text-muted">{report.summary}</p>
          </div>
          <ClaimList claims={report.claims} />
          <div className="border-t border-border px-4 py-4">
            <h3 className="text-sm font-semibold">Limitations</h3>
            <ul className="mt-3 space-y-2 text-sm leading-6 text-muted">
              {report.limitations.map((limitation) => (
                <li key={limitation}>{limitation}</li>
              ))}
            </ul>
          </div>
        </Panel>
        <Panel>
          <PanelTitle icon={FileText} title="Evidence queue" meta="approved" />
          <CitationList citations={report.citations} />
        </Panel>
      </div>

      <div className="mt-4">
        <Panel>
          <PanelTitle icon={GitBranch} title="Report provenance" meta="trace IDs" />
          <div className="grid gap-px bg-border md:grid-cols-2 xl:grid-cols-4">
            {Object.entries(report.generated_from).map(([label, value]) => (
              <div key={label} className="min-w-0 bg-surface px-4 py-4">
                <p className="text-xs font-semibold uppercase text-muted">{label.replaceAll("_", " ")}</p>
                <p className="mt-2 break-words font-mono text-xs leading-5">
                  {Array.isArray(value) ? value.join("\n") : value}
                </p>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </>
  );
}
