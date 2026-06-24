import Link from "next/link";
import {
  Activity,
  BarChart3,
  Database,
  FileText,
  FlaskConical,
  GitBranch,
  Home,
  ListChecks,
  type LucideIcon,
} from "lucide-react";

import { getDemoWorkspace } from "@/lib/demo-workspace";

type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

export const navItems: NavItem[] = [
  { href: "/", label: "Project", icon: Home },
  { href: "/datasets", label: "Dataset", icon: Database },
  { href: "/report", label: "Report", icon: FileText },
  { href: "/traces", label: "Trace", icon: GitBranch },
  { href: "/evals", label: "Evals", icon: ListChecks },
];

type WorkspaceShellProps = {
  children: React.ReactNode;
};

export function WorkspaceShell({ children }: WorkspaceShellProps) {
  const workspace = getDemoWorkspace();

  return (
    <div className="min-h-screen bg-wash text-ink">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-nav-border bg-nav px-4 py-5 text-nav-ink lg:block">
        <Link href="/" className="flex items-center gap-3">
          <span className="flex size-9 items-center justify-center rounded bg-accent text-white">
            <FlaskConical size={18} aria-hidden="true" />
          </span>
          <span>
            <span className="block text-sm font-semibold">Functional Proteomics</span>
            <span className="block text-xs text-nav-muted">Agent workbench</span>
          </span>
        </Link>
        <nav aria-label="Workspace" className="mt-8 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 rounded px-3 py-2 text-sm font-medium text-nav-muted transition hover:bg-white/5 hover:text-nav-ink"
            >
              <item.icon size={17} aria-hidden="true" />
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="absolute inset-x-4 bottom-5 rounded border border-nav-border bg-nav-2 p-3">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase text-nav-muted">
            <Activity size={14} aria-hidden="true" />
            Shared state
          </div>
          <p className="mt-2 text-sm">{workspace.project.id} loaded</p>
        </div>
      </aside>

      <div className="min-w-0 lg:pl-64">
        <header className="sticky top-0 z-10 border-b border-border bg-surface/95 backdrop-blur">
          <div className="flex min-h-16 items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
            <Link href="/" className="flex items-center gap-2 font-semibold lg:hidden">
              <FlaskConical size={18} aria-hidden="true" />
              FPW
            </Link>
            <div className="hidden items-center gap-3 lg:flex">
              <span className="rounded border border-border px-2 py-1 text-xs font-medium text-muted">
                Project shell
              </span>
              <span className="text-sm text-muted">Agent-native Perturb-PBMC workspace</span>
            </div>
            <div className="flex min-w-0 items-center gap-2 text-sm">
              <span className="size-2 rounded-full bg-signal" aria-hidden="true" />
              <span className="hidden text-muted sm:inline">
                {workspace.dataset.validation.status} dataset · {workspace.trace_export.count} traces
              </span>
            </div>
          </div>
          <nav aria-label="Mobile workspace" className="grid grid-cols-1 gap-1 px-4 pb-3 sm:grid-cols-3 lg:hidden">
            {navItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="flex min-w-0 items-center justify-center gap-2 rounded border border-border bg-wash px-3 py-2 text-sm font-medium"
              >
                <item.icon size={15} aria-hidden="true" />
                {item.label}
              </Link>
            ))}
          </nav>
        </header>
        <main className="mx-auto w-full min-w-0 max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}

type PageHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
};

export function PageHeader({ eyebrow, title, description }: PageHeaderProps) {
  return (
    <div className="mb-6 border-b border-border pb-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{eyebrow}</p>
      <h1 className="mt-2 max-w-[calc(100vw-2rem)] break-words text-xl font-semibold [overflow-wrap:anywhere] sm:max-w-4xl sm:text-3xl">
        {title}
      </h1>
      <p className="mt-3 max-w-[calc(100vw-2rem)] break-words text-sm leading-6 text-muted [overflow-wrap:anywhere] sm:max-w-3xl sm:text-base">
        {description}
      </p>
    </div>
  );
}

type PanelProps = {
  children: React.ReactNode;
  className?: string;
};

export function Panel({ children, className = "" }: PanelProps) {
  return <section className={`min-w-0 rounded border border-border bg-surface ${className}`}>{children}</section>;
}

type PanelTitleProps = {
  icon: LucideIcon;
  title: string;
  meta?: string;
};

export function PanelTitle({ icon: Icon, title, meta }: PanelTitleProps) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-border px-4 py-3">
      <div className="flex min-w-0 items-center gap-2">
        <Icon size={17} aria-hidden="true" />
        <h2 className="break-words text-sm font-semibold">{title}</h2>
      </div>
      {meta ? (
        <span className="hidden max-w-[55%] break-words text-right text-xs text-muted sm:inline">
          {meta}
        </span>
      ) : null}
    </div>
  );
}

export function EmptyState({ children }: { children: React.ReactNode }) {
  return <div className="px-4 py-8 text-sm leading-6 text-muted">{children}</div>;
}

export function StatusPill({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded border border-border bg-wash px-2 py-1 text-xs font-medium text-muted">
      {children}
    </span>
  );
}

export { BarChart3, Database, FileText, GitBranch, ListChecks };
