import {
  formatNumber,
  formatPValue,
  formatPercent,
  traceDisplayName,
  type EvalRun,
  type RankingRow,
  type ReportClaim,
  type ReportCitation,
  type ToolCallTrace,
} from "@/lib/demo-workspace";

export function MetricTile({
  label,
  value,
  detail,
  tone = "neutral",
}: {
  label: string;
  value: string;
  detail?: string;
  tone?: "neutral" | "accent" | "success" | "warning";
}) {
  const toneClass = {
    neutral: "border-border bg-surface",
    accent: "border-accent/25 bg-accent-wash/40",
    success: "border-secondary/25 bg-secondary/10",
    warning: "border-amber/30 bg-amber/10",
  }[tone];

  return (
    <div className={`min-w-0 rounded border px-4 py-3 ${toneClass}`}>
      <p className="text-xs font-semibold uppercase text-muted">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-ink">{value}</p>
      {detail ? <p className="mt-1 text-xs leading-5 text-muted">{detail}</p> : null}
    </div>
  );
}

export function StatusBadge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "success" | "error" | "accent";
}) {
  const toneClass = {
    neutral: "border-border bg-wash text-muted",
    success: "border-secondary/30 bg-secondary/10 text-secondary-strong",
    error: "border-coral/30 bg-coral/10 text-coral",
    accent: "border-accent/30 bg-accent-wash text-accent-strong",
  }[tone];

  return (
    <span className={`inline-flex items-center rounded border px-2 py-1 text-xs font-semibold ${toneClass}`}>
      {children}
    </span>
  );
}

export function DirectionBadge({ direction }: { direction: RankingRow["direction"] }) {
  return (
    <StatusBadge tone={direction === "down" ? "error" : "success"}>
      {direction === "down" ? "Down" : "Up"}
    </StatusBadge>
  );
}

export function RankedProteinTable({ rows, limit }: { rows: RankingRow[]; limit?: number }) {
  const visibleRows = limit ? rows.slice(0, limit) : rows;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] border-collapse text-left text-sm">
        <thead className="bg-wash text-xs uppercase text-muted">
          <tr>
            <th className="border-b border-border px-4 py-3 font-semibold">Rank</th>
            <th className="border-b border-border px-4 py-3 font-semibold">Protein</th>
            <th className="border-b border-border px-4 py-3 font-semibold">Direction</th>
            <th className="border-b border-border px-4 py-3 text-right font-semibold">Effect</th>
            <th className="border-b border-border px-4 py-3 text-right font-semibold">Donors</th>
            <th className="border-b border-border px-4 py-3 text-right font-semibold">p</th>
            <th className="border-b border-border px-4 py-3 text-right font-semibold">q</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {visibleRows.map((row, index) => (
            <tr key={row.protein} className="bg-surface">
              <td className="px-4 py-3 text-muted">{index + 1}</td>
              <td className="px-4 py-3 font-semibold text-ink">{row.protein}</td>
              <td className="px-4 py-3">
                <DirectionBadge direction={row.direction} />
              </td>
              <td className="px-4 py-3 text-right font-mono">{formatNumber(row.effect_size, 3)}</td>
              <td className="px-4 py-3 text-right">{formatPercent(row.donor_consistency)}</td>
              <td className="px-4 py-3 text-right font-mono">{formatPValue(row.p_value)}</td>
              <td className="px-4 py-3 text-right font-mono">{formatPValue(row.q_value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function EffectPlot({ rows }: { rows: RankingRow[] }) {
  const width = 760;
  const height = 360;
  const pad = { left: 54, right: 34, top: 24, bottom: 46 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const maxEffect = Math.max(...rows.map((row) => Math.abs(row.effect_size))) || 1;
  const maxY = Math.max(...rows.map((row) => -Math.log10(Math.max(row.q_value, 0.0001)))) || 1;
  const labelRows = rows.slice(0, 4);
  const topLabels = new Map(labelRows.map((row, index) => [row.protein, index]));

  const x = (effect: number) => pad.left + ((effect + maxEffect) / (2 * maxEffect)) * plotWidth;
  const y = (qValue: number) => {
    const score = -Math.log10(Math.max(qValue, 0.0001));
    return pad.top + (1 - score / maxY) * plotHeight;
  };

  return (
    <div className="overflow-x-auto">
      <svg
        role="img"
        aria-label="Effect-size plot for ranked proteins"
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
      >
        <rect x="0" y="0" width={width} height={height} fill="#ffffff" />
        <line
          x1={pad.left}
          y1={height - pad.bottom}
          x2={width - pad.right}
          y2={height - pad.bottom}
          stroke="#d3d6e2"
        />
        <line x1={pad.left} y1={pad.top} x2={pad.left} y2={height - pad.bottom} stroke="#d3d6e2" />
        <line
          x1={x(0)}
          y1={pad.top}
          x2={x(0)}
          y2={height - pad.bottom}
          stroke="#8a95a0"
          strokeDasharray="4 4"
        />
        {[-maxEffect, 0, maxEffect].map((tick) => (
          <g key={tick}>
            <line
              x1={x(tick)}
              y1={height - pad.bottom}
              x2={x(tick)}
              y2={height - pad.bottom + 5}
              stroke="#8a95a0"
            />
            <text x={x(tick)} y={height - 18} textAnchor="middle" fontSize="12" fill="#5b6772">
              {formatNumber(tick, 1)}
            </text>
          </g>
        ))}
        {[0, maxY / 2, maxY].map((tick) => (
          <g key={tick}>
            <line
              x1={pad.left - 5}
              y1={pad.top + (1 - tick / maxY) * plotHeight}
              x2={pad.left}
              y2={pad.top + (1 - tick / maxY) * plotHeight}
              stroke="#8a95a0"
            />
            <text
              x={pad.left - 10}
              y={pad.top + (1 - tick / maxY) * plotHeight + 4}
              textAnchor="end"
              fontSize="12"
              fill="#5b6772"
            >
              {formatNumber(tick, 1)}
            </text>
          </g>
        ))}
        <text x={width / 2} y={height - 2} textAnchor="middle" fontSize="12" fill="#5b6772">
          Mean paired effect size, IL-10 minus control
        </text>
        <text x="14" y={height / 2} transform={`rotate(-90 14 ${height / 2})`} textAnchor="middle" fontSize="12" fill="#5b6772">
          -log10 exploratory q
        </text>
        {rows.map((row) => {
          const cx = x(row.effect_size);
          const cy = y(row.q_value);
          const fill = row.direction === "down" ? "#f96b6b" : "#4ad889";
          const labelIndex = topLabels.get(row.protein);
          return (
            <g key={row.protein}>
              <circle cx={cx} cy={cy} r={labelIndex !== undefined ? 6 : 4} fill={fill} opacity="0.86" />
              {labelIndex !== undefined ? (
                <text
                  x={cx + (row.effect_size < 0 ? -10 : 10)}
                  y={cy + 16 + labelIndex * 13}
                  textAnchor={row.effect_size < 0 ? "end" : "start"}
                  fontSize="11"
                  fill="#0e1116"
                >
                  {row.protein}
                </text>
              ) : null}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function TraceTable({ traces, limit }: { traces: ToolCallTrace[]; limit?: number }) {
  const visibleTraces = limit ? traces.slice(0, limit) : traces;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[880px] border-collapse text-left text-sm">
        <thead className="bg-wash text-xs uppercase text-muted">
          <tr>
            <th className="border-b border-border px-4 py-3 font-semibold">Time</th>
            <th className="border-b border-border px-4 py-3 font-semibold">Surface</th>
            <th className="border-b border-border px-4 py-3 font-semibold">Tool</th>
            <th className="border-b border-border px-4 py-3 font-semibold">Status</th>
            <th className="border-b border-border px-4 py-3 text-right font-semibold">Latency</th>
            <th className="border-b border-border px-4 py-3 font-semibold">Provenance</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {visibleTraces.map((trace) => (
            <tr key={trace.id} className={trace.status === "error" ? "bg-coral/5" : "bg-surface"}>
              <td className="px-4 py-3 text-xs text-muted">{formatTimestamp(trace.started_at)}</td>
              <td className="px-4 py-3">{traceDisplayName(trace)}</td>
              <td className="px-4 py-3 font-semibold">{trace.tool_name}</td>
              <td className="px-4 py-3">
                <StatusBadge tone={trace.status === "ok" ? "success" : "error"}>{trace.status}</StatusBadge>
              </td>
              <td className="px-4 py-3 text-right font-mono">{trace.latency_ms} ms</td>
              <td className="px-4 py-3 text-xs text-muted">
                <span className="font-mono text-ink">{trace.id}</span>
                {trace.eval_run_id ? <span className="block">eval {trace.eval_run_id}</span> : null}
                {trace.chat_session_id ? <span className="block">chat {trace.chat_session_id}</span> : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function TraceDetails({ traces }: { traces: ToolCallTrace[] }) {
  return (
    <div className="divide-y divide-border">
      {traces.map((trace) => (
        <details key={trace.id} className="group">
          <summary className="flex cursor-pointer flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm">
            <span className="font-semibold">{trace.tool_name}</span>
            <span className="font-mono text-xs text-muted">{trace.id}</span>
          </summary>
          <div className="grid gap-px bg-border md:grid-cols-2">
            <JsonBlock title="Input" value={trace.input} />
            <JsonBlock title="Output" value={trace.output ?? trace.error ?? { status: trace.status }} />
          </div>
        </details>
      ))}
    </div>
  );
}

export function ClaimList({ claims }: { claims: ReportClaim[] }) {
  return (
    <div className="divide-y divide-border">
      {claims.map((claim) => (
        <article key={claim.label} className="px-4 py-4">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge tone={claim.kind === "data_derived" ? "accent" : "neutral"}>
              {claim.kind.replace("_", " ")}
            </StatusBadge>
            <h3 className="text-sm font-semibold">{claim.label}</h3>
          </div>
          <p className="mt-3 text-sm leading-6 text-muted">{claim.text}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {claim.support.map((support, index) => (
              <span key={`${claim.label}-${index}`} className="rounded border border-border bg-wash px-2 py-1 font-mono text-[11px] text-muted">
                {support.source_id ?? support.trace_id ?? support.id}
              </span>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

export function CitationList({ citations }: { citations: ReportCitation[] }) {
  return (
    <div className="divide-y divide-border">
      {citations.map((citation) => (
        <article key={citation.source_id} className="px-4 py-4">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge tone={citation.approved_for_claims ? "success" : "neutral"}>
              {citation.source_type}
            </StatusBadge>
            <span className="font-mono text-xs text-muted">{citation.source_id}</span>
          </div>
          <h3 className="mt-2 text-sm font-semibold leading-5">{citation.title}</h3>
          <p className="mt-2 break-words text-xs leading-5 text-muted">
            {citation.doi ? `DOI ${citation.doi}` : citation.url ?? citation.source_locator}
          </p>
        </article>
      ))}
    </div>
  );
}

export function EvalRunPanel({ evalRun, tracesById }: { evalRun: EvalRun; tracesById: Map<string, ToolCallTrace> }) {
  return (
    <div className="divide-y divide-border">
      {evalRun.results.map((result) => (
        <article key={result.case_id} className="px-4 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="font-mono text-sm font-semibold">{result.case_id}</h3>
            <StatusBadge tone={result.passed ? "success" : "error"}>{result.passed ? "passed" : "failed"}</StatusBadge>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {result.checks.map((check, index) => (
              <div key={`${result.case_id}-${check.kind}-${index}`} className="border-t border-border pt-2 text-sm">
                <div className="flex items-center gap-2">
                  <StatusBadge tone={check.passed ? "success" : "error"}>{check.kind}</StatusBadge>
                </div>
                {check.detail ? <p className="mt-2 text-xs leading-5 text-muted">{check.detail}</p> : null}
              </div>
            ))}
          </div>
          {result.trace_step_ids.length ? (
            <div className="mt-4 space-y-2">
              {result.trace_step_ids.map((traceId) => {
                const trace = tracesById.get(traceId);
                return (
                  <div key={traceId} className="rounded border border-border bg-wash px-3 py-2 text-xs">
                    <span className="font-mono text-muted">{traceId}</span>
                    {trace ? <span className="ml-2 font-semibold">{trace.tool_name}</span> : null}
                  </div>
                );
              })}
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}

function JsonBlock({ title, value }: { title: string; value: unknown }) {
  return (
    <div className="min-w-0 bg-surface px-4 py-4">
      <h3 className="text-xs font-semibold uppercase text-muted">{title}</h3>
      <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap break-words rounded border border-border bg-wash p-3 text-xs leading-5 text-ink">
        {JSON.stringify(value, null, 2)}
      </pre>
    </div>
  );
}

function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}
