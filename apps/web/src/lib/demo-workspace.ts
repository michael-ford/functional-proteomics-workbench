import fs from "node:fs";
import path from "node:path";

export type ValidationStatus = "pending" | "passed" | "failed";
export type TraceSurface = "web_chat" | "mcp" | "eval" | "api";
export type TraceStatus = "ok" | "error";
export type Direction = "up" | "down";

export type ArtifactRef = {
  uri: string;
  media_type: string;
  bytes?: number | null;
  sha256?: string | null;
};

export type RankingRow = {
  protein: string;
  effect_size: number;
  direction: Direction;
  p_value: number;
  q_value: number;
  donor_consistency: number;
};

export type ToolCallTrace = {
  id: string;
  project_id: string | null;
  origin: {
    surface: TraceSurface;
    client: string | null;
    token_id: string | null;
  };
  tool_name: string;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  artifact_refs: ArtifactRef[];
  status: TraceStatus;
  error: { code: string; message: string; retryable: boolean } | null;
  started_at: string;
  ended_at: string;
  latency_ms: number;
  chat_session_id: string | null;
  chat_message_id: string | null;
  eval_run_id: string | null;
};

export type EvalCheck = {
  kind: string;
  passed: boolean;
  detail: string | null;
};

export type EvalResult = {
  case_id: string;
  passed: boolean;
  checks: EvalCheck[];
  trace_step_ids: string[];
};

export type EvalRun = {
  id: string;
  suite: string;
  mode: "smoke" | "full";
  results: EvalResult[];
  score: number;
  created_at: string;
};

export type ReportClaim = {
  kind: "data_derived" | "source_derived" | "interpretive";
  label: string;
  text: string;
  support: Array<Record<string, string>>;
};

export type ReportCitation = {
  source_id: string;
  title: string;
  source_type: string;
  source_locator: string;
  url: string | null;
  doi: string | null;
  trace_id: string;
  approved_for_claims: boolean;
};

export type DemoWorkspace = {
  schema_version: string;
  project: {
    id: string;
    title: string;
    status: string;
    context_md: string;
    created_at: string;
    updated_at: string;
  };
  dataset: {
    id: string;
    name: string;
    source: string;
    raw_ref: ArtifactRef;
    normalized_ref: ArtifactRef;
    validation: {
      status: ValidationStatus;
      row_count: number | null;
      issues: Array<Record<string, unknown>>;
    };
    created_at: string;
  };
  schema_profile: {
    layout: string;
    columns: Array<{
      name: string;
      dtype: string;
      role: string;
      n_unique: number | null;
      examples: string[];
    }>;
    detected_axes: Record<string, string | null>;
  };
  seed_manifest: {
    source_repo: string;
    source_commit: string;
    source_file: string;
    source_file_sha256: string;
    artifact_refs: string[];
  };
  analysis_plan: {
    id: string;
    method_id: string;
    comparison: {
      group_a: Record<string, string>;
      group_b: Record<string, string>;
      stimulation_context: string;
      paired_by: string;
    };
    donor_handling: string;
    replicate_handling: string;
    multiple_testing: string;
    assumptions: string[];
    limitations: string[];
  };
  analysis_result: {
    id: string;
    method_id: string;
    table_ref: ArtifactRef;
    donor_consistency: Array<{
      donor: string;
      agrees_with_consensus: boolean;
      note: string;
    }>;
  };
  ranking: {
    rows: RankingRow[];
    metric: string;
    correction: string;
  };
  evidence_results: Array<{
    query: string;
    trace_id: string;
    output: {
      chunks: Array<{
        score: number;
        metadata: {
          source_id: string;
          title: string;
          approved_for_claims: boolean;
          source_type: string;
          source_locator: string;
          topic_buckets: string[];
        };
        chunk: {
          id: string;
          text: string;
          entities: string[];
          citation: {
            url?: string | null;
            doi?: string | null;
          };
        };
      }>;
    };
  }>;
  report: {
    id: string;
    title: string;
    subtitle: string;
    summary: string;
    generated_from: Record<string, string | string[]>;
    claims: ReportClaim[];
    limitations: string[];
    citations: ReportCitation[];
  };
  eval_run: EvalRun;
  trace_export: {
    path: string;
    count: number;
    web_chat_trace_ids: string[];
    eval_trace_ids: string[];
  };
  traces: ToolCallTrace[];
};

let cachedWorkspace: DemoWorkspace | null = null;

export function getDemoWorkspace(): DemoWorkspace {
  if (cachedWorkspace) {
    return cachedWorkspace;
  }
  const root = findRepoRoot(process.cwd());
  const artifactRoot = path.join(root, "demo_data", "artifacts");
  const state = readJson<DemoWorkspace>(path.join(artifactRoot, "web-demo-state.json"));
  const traces = readJsonl<ToolCallTrace>(path.join(artifactRoot, "traces", "tool_calls.jsonl"));
  cachedWorkspace = { ...state, traces };
  return cachedWorkspace;
}

export function formatNumber(value: number, digits = 3): string {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: Math.min(1, digits),
  }).format(value);
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatPValue(value: number): string {
  return value < 0.001 ? "<0.001" : value.toFixed(3);
}

export function formatBytes(value?: number | null): string {
  if (value == null) {
    return "unknown";
  }
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${formatNumber(value / 1024, 1)} KB`;
  }
  return `${formatNumber(value / (1024 * 1024), 1)} MB`;
}

export function traceDisplayName(trace: ToolCallTrace): string {
  const client = trace.origin.client ? ` / ${trace.origin.client}` : "";
  return `${trace.origin.surface}${client}`;
}

function findRepoRoot(start: string): string {
  let current = path.resolve(start);
  while (true) {
    if (fs.existsSync(path.join(current, "demo_data", "artifacts", "web-demo-state.json"))) {
      return current;
    }
    const parent = path.dirname(current);
    if (parent === current) {
      throw new Error("Unable to locate demo_data/artifacts from current working directory.");
    }
    current = parent;
  }
}

function readJson<T>(filePath: string): T {
  return JSON.parse(fs.readFileSync(filePath, "utf8")) as T;
}

function readJsonl<T>(filePath: string): T[] {
  return fs
    .readFileSync(filePath, "utf8")
    .trim()
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line) as T);
}
