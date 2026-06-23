import { EmptyState, GitBranch, PageHeader, Panel, PanelTitle, StatusPill } from "@/components/workspace-shell";

const columns = ["time", "surface", "tool", "status", "artifact"];

export default function TracePage() {
  return (
    <>
      <PageHeader
        eyebrow="Trace inspection"
        title="Tool-call audit trail"
        description="The trace view is reserved for replaying real web, MCP, and eval tool calls against the same project state."
      />
      <Panel>
        <PanelTitle icon={GitBranch} title="Trace log" meta="no calls recorded" />
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-left text-sm">
            <thead className="bg-wash text-xs uppercase text-muted">
              <tr>
                {columns.map((column) => (
                  <th key={column} className="border-b border-border px-4 py-3 font-semibold">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td colSpan={columns.length} className="px-4 py-8">
                  <EmptyState>No trace records are available.</EmptyState>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="border-t border-border px-4 py-3">
          <StatusPill>Trace storage pending API integration</StatusPill>
        </div>
      </Panel>
    </>
  );
}
