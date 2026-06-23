# Evals

> **Protected / contract file.** Changes require a PR labeled `contract-change`. SPEC-005/eval.

## Philosophy
Small, visible, workflow-grounded. The eval suite exists to demonstrate the system is not a
free-form chatbot: it mirrors the hero workflow and checks tool choice, numeric correctness,
citation support, and unsupported-claim avoidance.

## Eval-case schema
Reuses `EvalCheck` / `EvalTraceStep` from `docs/TRACE_MODEL.md`.

```python
class EvalCase(BaseModel):
    id: str                       # case_*
    name: str
    description: str
    tags: list[str]               # e.g. ["tool_choice","analysis","citation"]
    deterministic: bool           # True => CI-safe (fixture data, mocked model adapter)
    fixture_refs: list[str] = []  # ArtifactRef uris or fixture ids
    expectations: list["EvalExpectation"]

class EvalExpectation(BaseModel):
    tool_name: str | None = None  # expected tool at this step (None = free)
    checks: list[EvalCheck]

class EvalResult(BaseModel):
    case_id: str
    passed: bool
    checks: list[EvalCheck]
    trace_step_ids: list[str]     # -> ToolCallTrace.id (the replay)

class EvalRun(BaseModel):
    id: str                       # eval_run_*
    suite: str
    mode: Literal["smoke", "full"]
    results: list[EvalResult]
    score: float                  # fraction of cases passed
    created_at: datetime
```

## Metrics (HANDOFF §19.4)
`tool_choice_accuracy` · `schema_validity` · `numeric_correctness` · `citation_support` ·
`entity_grounding` · `unsupported_claim_rate` · `report_structure_score` · `trace_completeness`.

## First suite (mirrors the hero workflow — HANDOFF §19.3)
1. Create project from a user request → returns upload URL
2. Validate the demo PBMC dataset
3. Infer/define the comparison
4. Select a **supported** analysis method
5. Rank proteins correctly from fixture data (numeric check)
6. Retrieve relevant evidence chunks (entity grounding)
7. Generate a report with **no unsupported claims** (citation support)
8. *(optional)* Refuse/constrain an unsupported arbitrary analysis request
9. *(optional)* Preserve data-derived vs source-derived vs interpretive claim typing

Cases 1–7 are designed to be **deterministic** (fixture data + mocked model adapter) so they
are CI-safe. The optional cases may need a live model call.

## Gating policy (R-eval)
The eval gate is **path-conditional** and **phase-gated**:

- **Path-conditional:** the `eval-smoke` CI job runs only when a PR touches eval-relevant
  paths — `packages/analysis/**`, `packages/corpus/**`, `services/**`, `agent_policies/**`,
  `evals/**`, `packages/shared-schemas/**`. Docs-only or frontend-only PRs skip it.
- **Phase-gated:** `eval-smoke` becomes a *required* status check (in branch protection) only
  once the system runs the workflow end-to-end. Until that milestone it runs informationally
  and does not block merge. The activation point is recorded in `docs/ROADMAP.md`.
- **CI runs deterministic cases only**, mocked model adapter, and must be 100% green to gate.
- **Full suite** (`mode: full`, real model calls) runs on `workflow_dispatch` or the
  `eval` label — non-blocking; uploads the `EvalRun` as an artifact and may comment the score
  on the PR.

## Eval page
Shows suite status, per-case pass/fail, the tool-call trace (replay), citation/numeric/
unsupported-claim checks, and the latest score. For web-chat evals it can show full replay;
for external MCP usage, server-side tool traces (`docs/TRACE_MODEL.md`).

## Adding cases
Add an `EvalCase` JSON/YAML under `evals/cases/` (protected — `contract-change` PR), with
fixtures and expected checks. Prefer `deterministic: true` so the case is CI-safe.
