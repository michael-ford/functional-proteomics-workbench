import {
  BarChart3,
  Database,
  EmptyState,
  FileText,
  GitBranch,
  PageHeader,
  Panel,
  PanelTitle,
  StatusPill,
} from "@/components/workspace-shell";
import { ChatPanel } from "@/components/chat-panel";

const workflow = [
  ["Project", "Created by agent"],
  ["Dataset", "Curated public subset pending"],
  ["Validation", "No schema inspection yet"],
  ["Analysis", "No comparison plan yet"],
  ["Report", "No evidence-backed report yet"],
];

export default function ProjectDashboardPage() {
  return (
    <>
      <PageHeader
        eyebrow="Project dashboard"
        title="Demo project workspace"
        description="A shared project surface for the web app and MCP tools: state, dataset handoff, analysis artifacts, evidence-backed report, and trace replay."
      />
      <div className="mb-4">
        <ChatPanel />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel>
          <PanelTitle icon={Database} title="Project state" meta="empty shell" />
          <div className="grid gap-px bg-border sm:grid-cols-3">
            {[
              ["Dataset", "Not selected"],
              ["Analysis plan", "Not defined"],
              ["Artifacts", "None"],
            ].map(([label, value]) => (
              <div key={label} className="bg-surface p-4">
                <p className="text-xs font-semibold uppercase text-muted">{label}</p>
                <p className="mt-3 text-lg font-semibold">{value}</p>
              </div>
            ))}
          </div>
        </Panel>

        <Panel>
          <PanelTitle icon={GitBranch} title="Agent handoff" meta="reserved" />
          <EmptyState>
            Tool-created URLs, selected dataset metadata, validation status, and downstream run
            identifiers will appear here when the shared registry is connected.
          </EmptyState>
        </Panel>
      </div>

      <div className="mt-4 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel>
          <PanelTitle icon={BarChart3} title="Workflow" />
          <div className="divide-y divide-border">
            {workflow.map(([label, state]) => (
              <div key={label} className="flex items-center justify-between gap-3 px-4 py-3">
                <span className="text-sm font-medium">{label}</span>
                <StatusPill>{state}</StatusPill>
              </div>
            ))}
          </div>
        </Panel>

        <Panel>
          <PanelTitle icon={FileText} title="Analysis surface" meta="no results" />
          <div className="grid gap-px bg-border md:grid-cols-2">
            <div className="min-h-52 bg-surface p-4">
              <h3 className="text-sm font-semibold">Ranked proteins</h3>
              <EmptyState>No effect sizes, donor consistency metrics, or p-values have been computed.</EmptyState>
            </div>
            <div className="min-h-52 bg-surface p-4">
              <h3 className="text-sm font-semibold">Plot artifact</h3>
              <EmptyState>No plot artifact is available.</EmptyState>
            </div>
          </div>
        </Panel>
      </div>
    </>
  );
}
