import { MetricTile, StatusBadge } from "@/components/demo-artifact-ui";
import { Database, PageHeader, Panel, PanelTitle, StatusPill } from "@/components/workspace-shell";
import { formatBytes, getDemoWorkspace } from "@/lib/demo-workspace";

export default function DatasetPage() {
  const workspace = getDemoWorkspace();
  const validation = workspace.dataset.validation;
  const donors = workspace.analysis_result.donor_consistency.length;
  const validationTone = validation.status === "passed" ? "success" : "error";

  return (
    <>
      <PageHeader
        eyebrow="Dataset handoff"
        title={workspace.dataset.name}
        description="Selected public Perturb-PBMC subset, validated from the committed fixture and seed manifest."
      />

      <div className="mb-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricTile label="Rows" value={String(validation.row_count)} detail="Long-format protein measurements" tone="accent" />
        <MetricTile label="Donors" value={String(donors)} detail="Matched paired units" tone="success" />
        <MetricTile label="Proteins" value={String(workspace.schema_profile.columns.find((column) => column.role === "protein")?.n_unique ?? workspace.ranking.rows.length)} detail="Frozen SPEC-006 panel" />
        <MetricTile label="Validation" value={validation.status} detail={`${validation.issues.length} blocking issues`} tone={validation.status === "passed" ? "success" : "warning"} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_22rem]">
        <Panel>
          <PanelTitle icon={Database} title="Selected public subset" meta={workspace.dataset.id} />
          <div className="divide-y divide-border">
            {[
              ["Subset identity", "Perturb-PBMC IL-10/LPS direct subset"],
              ["Stimulation context", "LPS · 2000 ng/mL"],
              ["Perturbagen/control comparison", "IL-10 50 ng/mL vs matched no-cytokine control"],
              ["Paired unit", workspace.analysis_plan.comparison.paired_by],
              ["Raw artifact", `${workspace.dataset.raw_ref.uri} · ${formatBytes(workspace.dataset.raw_ref.bytes)}`],
              ["Normalized artifact", `${workspace.dataset.normalized_ref.uri} · ${formatBytes(workspace.dataset.normalized_ref.bytes)}`],
            ].map(([label, value]) => (
              <div key={label} className="flex items-start justify-between gap-4 px-4 py-4">
                <span className="text-sm font-medium">{label}</span>
                <span className="max-w-[62%] break-words text-right text-sm text-muted">{value}</span>
              </div>
            ))}
          </div>
        </Panel>
        <Panel>
          <PanelTitle icon={Database} title="Validation" />
          <div className="px-4 py-4">
            <StatusBadge tone={validationTone}>{validation.status}</StatusBadge>
            <p className="mt-3 text-sm leading-6 text-muted">
              Fixture validation checked required columns, donor coverage, perturbagen/control
              categories, protein panel membership, rectangularity, and source provenance.
            </p>
          </div>
          <div className="border-t border-border px-4 py-3">
            <StatusPill>{validation.issues.length === 0 ? "No validation issues" : `${validation.issues.length} issues`}</StatusPill>
          </div>
        </Panel>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_0.9fr]">
        <Panel>
          <PanelTitle icon={Database} title="Schema profile" meta={workspace.schema_profile.layout} />
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] border-collapse text-left text-sm">
              <thead className="bg-wash text-xs uppercase text-muted">
                <tr>
                  <th className="border-b border-border px-4 py-3 font-semibold">Column</th>
                  <th className="border-b border-border px-4 py-3 font-semibold">Role</th>
                  <th className="border-b border-border px-4 py-3 font-semibold">Type</th>
                  <th className="border-b border-border px-4 py-3 text-right font-semibold">Unique</th>
                  <th className="border-b border-border px-4 py-3 font-semibold">Examples</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {workspace.schema_profile.columns.map((column) => (
                  <tr key={column.name}>
                    <td className="px-4 py-3 font-mono text-xs">{column.name}</td>
                    <td className="px-4 py-3">{column.role}</td>
                    <td className="px-4 py-3 text-muted">{column.dtype}</td>
                    <td className="px-4 py-3 text-right">{column.n_unique ?? "many"}</td>
                    <td className="px-4 py-3 text-muted">{column.examples.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel>
          <PanelTitle icon={Database} title="Source provenance" meta="public fixture" />
          <div className="divide-y divide-border text-sm">
            {[
              ["Repository", workspace.seed_manifest.source_repo],
              ["Commit", workspace.seed_manifest.source_commit],
              ["Source file", workspace.seed_manifest.source_file],
              ["Source file SHA-256", workspace.seed_manifest.source_file_sha256],
            ].map(([label, value]) => (
              <div key={label} className="px-4 py-3">
                <p className="text-xs font-semibold uppercase text-muted">{label}</p>
                <p className="mt-2 break-words font-mono text-xs leading-5">{value}</p>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </>
  );
}
