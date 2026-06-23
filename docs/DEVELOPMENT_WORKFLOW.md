# Development Workflow

How work flows through this repo: CI, dual-agent review, and auto-merge.

> **This document records a deliberate reversal of the original `HANDOFF.md` governance**
> (§25.2, §26, §41), which specified human-gated merges. The owner has chosen fully
> autonomous merge gated by a strong automated review harness. See "Governance change"
> below.

## Pipeline overview

```
PR opened / synchronized / ready_for_review
  ├─ ci            → lint, typecheck, tests, eval-smoke        (status check)
  ├─ review (claude) → claude CLI session (tmux, self-hosted)  (required check)
  └─ review (codex)  → codex  CLI session (tmux, self-hosted)  (required check)
        │
        ▼  branch protection requires: ci + review (claude) + review (codex) all green
        ▼
  GitHub native auto-merge (squash) → merges with NO human click
```

**All PRs auto-merge on green.** There is no required human approval.

Claude remains a required check so auto-merge waits for it when the CLI can run. If the local
Claude CLI exits with a temporary usage/quota-limit message, the harness records an advisory
"skipped" comment and passes `review (claude)` for that availability failure only. Real Claude
P0/P1 review findings still fail the required check.

## Runner

- **Self-hosted macOS runner**, registered to this repo (`michael-ford/<repo>`).
  Self-hosted runners are repo-scoped; the existing `bestguy` runners cannot be reused
  (they are bound to a different repo), so this repo gets its own registration on the same
  Mac (`actions-runner-nomic/`).
- Review jobs `runs-on: [self-hosted, macOS]`. CI (lint/test) may run on GitHub-hosted
  `ubuntu-latest`.

## Review agents (Claude + Codex)

Both reviewers run as **local CLI sessions spawned in tmux** (pattern adapted from
bestguy's `execute.yml` + `spawn-agent.sh`), not the hosted `claude-code-action` /
Codex cloud toggle. Rationale:

- **No API-key secrets in the repo** — the CLI sessions inherit local subscription auth
  (`~/.claude` for Claude; local ChatGPT/Codex auth for Codex).
- A single spawn script (`scripts/spawn-review-agent.sh`) is the **vendor-swap point**:
  the agent command is the only thing that differs between the two reviewers.

Each reviewer:
1. Reads `REVIEW.md` (the shared severity rubric).
2. Reviews `gh pr diff` (read-only tools: `Bash(gh:*),Read,Glob,Grep`).
3. Posts a review with `### P0` / `### P1` / `### P2` findings and a tally, tagged with a
   marker (e.g. `<!-- reviewer:claude -->`).
4. Emits `REVIEW_VERDICT: PASS` if no P0/P1, else `REVIEW_VERDICT: FAIL`; the workflow job
   maps that verdict onto `review (claude)` / `review (codex)`.

If Claude is temporarily unavailable because the runner's local CLI has hit a usage/quota
limit, `review (claude)` becomes an advisory skip and succeeds. Codex review remains required
and fail-closed.

### The gating wrinkle

The reviewer CLI runs inside tmux for observability, but the workflow waits for it to finish.
If a reviewer times out, exits without a verdict, or emits an unparseable verdict, the job
fails closed. The only fail-open path is the explicit Claude usage-limit skip described above.

## Branch protection (set after Phase 1, once check names exist)

Require status checks: `ci`, `review (claude)`, `review (codex)`. Enable "Allow auto-merge".
No required human reviewers (auto-merge is the whole point).

## Governance change (vs HANDOFF)

| HANDOFF said | This repo does | Why |
|---|---|---|
| Agents may not merge; human final merge required | All PRs auto-merge on green | Owner decision; demonstrate confidence in the gate |
| ≥1 human approval | 0 human approvals | The dual model-review + CI + eval gate replaces it |
| CODEOWNERS review required for protected files | CODEOWNERS advisory only | Kept to mark contract-sensitive files |

**Positioning note:** for the Nomic audience, the hero is the *strength of the gate*
(CI + evals + two independent model reviewers, P0/P1 clean), not the absence of humans.

## Issue lifecycle (spec → implement → review → merge)

Claude authors specs and reviews; Codex implements and reviews. The division:

```
issue opened
  └─ you add `needs-spec`  ─▶ [spec.yml] Claude drafts a skeleton spec + a headline
                                Open Questions / Blockers list; labels `spec-drafted`
                                (+ `needs-decision` if it raised blockers)
  └─ orchestrator session  ─▶ you + Claude burn through the open questions across all
                                `needs-decision` issues, finalize the spec
  └─ you add `agent-ready` ─▶ [execute.yml] Codex implements in a tmux worktree
                                (`~/fpw-agent-workspaces/issue-N`, branch `agent/issue-N`),
                                opens a PR
  └─ PR                    ─▶ [review.yml] Claude + Codex review ─▶ auto-merge on green
```

Both agent workflows run on the self-hosted runner; the implementer is fire-and-forget
(attach with `tmux attach -t fpw-agents`). The implementer opens its PR using the runner's
ambient `gh` login (a real user) so the PR triggers review + auto-merge.

When an implementation PR from `agent/issue-N` is merged, `cleanup-agent.yml` runs on the
self-hosted runner and removes the corresponding tmux window, worktree, local branch, and
durable prompt/state directory. A manual `workflow_dispatch` path exists for cleanup replays.

## Labels

Single implementation label (`agent-ready`), per owner decision — no `agent-claude` /
`agent-codex` split; the default implementer is **Codex** (`IMPL_AGENT` in `execute.yml`).

| Label | Meaning |
|---|---|
| `needs-spec` | Trigger Claude's spec-drafting pass on this issue |
| `spec-drafted` | Claude has posted a spec + open-questions comment |
| `needs-decision` | Open questions block this issue; resolve in an orchestrator session |
| `agent-ready` | Spec finalized → Codex implements |
| `contract-change` | PR may touch protected contract files (`packages/shared-schemas/**`, `docs/*` contracts, `.github/workflows/**`) |

See `.github/ISSUE_TEMPLATE/` and `.github/pull_request_template.md`.
