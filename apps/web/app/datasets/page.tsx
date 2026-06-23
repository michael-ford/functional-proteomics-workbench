import { Database, EmptyState, PageHeader, Panel, PanelTitle, StatusPill } from "@/components/workspace-shell";

export default function DatasetPage() {
  return (
    <>
      <PageHeader
        eyebrow="Dataset handoff"
        title="Select a curated public Perturb-PBMC subset"
        description="The first shell reserves the selector and validation surfaces while DATA-001 finalizes the exact public subset and fixture format."
      />
      <div className="grid gap-4 lg:grid-cols-[1fr_22rem]">
        <Panel>
          <PanelTitle icon={Database} title="Available public subsets" meta="pending DATA-001" />
          <div className="divide-y divide-border">
            {["Subset identity", "Stimulation context", "Perturbagen/control comparison", "Protein panel"].map(
              (label) => (
                <div key={label} className="flex items-center justify-between gap-4 px-4 py-4">
                  <span className="text-sm font-medium">{label}</span>
                  <StatusPill>Not selected</StatusPill>
                </div>
              )
            )}
          </div>
        </Panel>
        <Panel>
          <PanelTitle icon={Database} title="Validation" />
          <EmptyState>
            Schema inspection, fixture provenance, and accepted preprocessing state will be shown
            after a real dataset selection is available.
          </EmptyState>
        </Panel>
      </div>
    </>
  );
}
