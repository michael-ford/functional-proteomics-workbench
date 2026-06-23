import { EmptyState, ListChecks, PageHeader, Panel, PanelTitle, StatusPill } from "@/components/workspace-shell";

export default function EvalsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Eval dashboard"
        title="Workflow correctness checks"
        description="Deterministic eval cases will surface here with their replay traces and tool-contract outcomes once the eval runner lands."
      />
      <div className="grid gap-4 lg:grid-cols-3">
        {["Agent workflow", "Tool parity", "Report grounding"].map((title) => (
          <Panel key={title}>
            <PanelTitle icon={ListChecks} title={title} />
            <div className="px-4 py-4">
              <StatusPill>Not run</StatusPill>
            </div>
            <EmptyState>No eval result has been recorded.</EmptyState>
          </Panel>
        ))}
      </div>
    </>
  );
}
