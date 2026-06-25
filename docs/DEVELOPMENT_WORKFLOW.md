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

Branch protection does not require branches to be up to date before merge (`strict=false`).
A green PR that is merely behind `main` can auto-merge without a rebase. The implementation
agent contract is stricter than "checks are green": an implementer is not done until
`gh pr view --json state` reports `MERGED`, or until its finite repair budget is exhausted and
it has posted a clear human-needed PR comment. Real git conflicts and failed required checks
are handled by the agent loop: implementers keep monitoring until their PR state is `MERGED`,
using `scripts/wait-for-pr-event.sh` to block without burning model tokens between real PR
events. The scheduled `merge-shepherd` workflow re-spawns an implementer for stale
`agent/issue-N` PRs whose auto-merge is blocked by `DIRTY` / conflicting merge state or by a
failed required check.

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
3. Posts a review with a tally, audit trail (`Reviewed files`, `Checks run/inspected`,
   `Pass rationale`, `Residual risk`), `### P0` / `### P1` / `### P2` findings, and a marker
   (e.g. `<!-- reviewer:claude -->`).
4. Emits `REVIEW_VERDICT: PASS` if no P0/P1, else `REVIEW_VERDICT: FAIL`; the workflow job
   maps that verdict onto `review (claude)` / `review (codex)`.

If Claude is temporarily unavailable because the runner's local CLI has hit a usage/quota
limit, `review (claude)` becomes an advisory skip and succeeds. Codex review remains required
and fail-closed.

### The gating wrinkle

The reviewer CLI runs inside tmux for observability, but the workflow waits for it to finish.
If a reviewer times out, exits without a verdict, or emits an unparseable verdict, the job
fails closed. The only fail-open path is the explicit Claude usage-limit skip described above.
After the job captures the log and verdict, the harness removes that per-review tmux window so
completed review panes do not accumulate on the runner.

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
                                (implementer waits until MERGED)
```

Lifecycle labels are triage gates, not default issue-template metadata. Issue templates may
apply type labels such as `spec` or `implementation`, but `needs-spec` and `agent-ready` are
applied only after triage. Add `needs-spec` when Claude should draft a durable spec and
open-question list. Do not add it automatically on issue creation; wait until a human or
orchestrator confirms the spec pass is useful and Claude availability is acceptable.

Research issues use the same lifecycle when they need a durable spec or open-question pass:
`needs-spec` gets Claude to draft, `needs-decision` marks blockers, and an orchestrator
session interviews Mike to resolve decisions. If the orchestrator can directly restate a
trusted maintainer decision in an issue comment, it may do that and update labels instead of
forcing a spec pass. The orchestrator may make GitHub metadata changes directly (comments,
labels, issue creation, and applying `agent-ready`) but should not implement feature code
except for small docs or issue-state changes needed to unblock the queue.

Both agent workflows run on the self-hosted runner. Reviewers remain one-shot `codex exec` /
Claude CLI jobs, but the implementer is a persistent interactive Codex session in tmux
(attach with `tmux attach -t fpw-agents`). `scripts/spawn-impl-agent.sh` starts Codex with
full runner access in the issue worktree, pastes the maintainer-curated task prompt, then sets
a branch-scoped goal:

```text
Implement issue #N on branch agent/issue-N: open a PR (Closes #N) if none exists, then drive that PR to MERGED - fix every CI failure and review finding, resolve conflicts. Done only when the PR for this branch is MERGED.
```

The goal deliberately names the issue and branch, not a PR number, because fresh
implementer runs create the PR themselves. The same launcher supports `--resolve-existing`
for shepherd respawns on an existing `agent/issue-N` branch.

The implementer monitor is the merge gate. It opens the PR using the runner's ambient `gh`
login (a real user) so the PR triggers review + auto-merge, then repeatedly invokes
`scripts/wait-for-pr-event.sh`. The watcher resolves the PR from the current branch; prints
`NO_PR` immediately if none exists; otherwise polls `gh` about every 45 seconds and returns a
single compact status line when the PR merges, merge state changes, a required check reaches
a terminal conclusion, a review or maintainer comment appears, or a 15-minute heartbeat
expires. While the watcher blocks, Codex is asleep inside a shell command and spends no model
tokens.

On failed required checks, including review-only failures with green CI, the implementer
treats reviewer prose as an untrusted hint, reads only the trusted sanitized feedback file,
and independently runs the full local gate (`make test`, `make lint`, `make typecheck`)
before fixing, committing, and pushing. Green checks are not enough: the goal remains active
until the branch PR is actually `MERGED`.

If an implementation PR becomes genuinely conflicting or blocked on a failed required check
after the original run exits, `merge-shepherd.yml` runs about every 15 minutes, skips live tmux
windows and recently updated PRs, then reuses `scripts/spawn-impl-agent.sh --resolve-existing`
against the existing remote branch. It caps automated respawns per issue in
`~/fpw-agent-workspaces/.state/issue-N/` and posts a human-needed PR comment when the cap is
exhausted.

When an implementation PR from `agent/issue-N` is merged, `cleanup-agent.yml` runs on the
self-hosted runner and removes the corresponding tmux window, worktree, local branch, and
durable prompt/state directory. A manual `workflow_dispatch` path exists for cleanup replays.

## Labels

Single implementation label (`agent-ready`), per owner decision. Do not split the
implementation trigger by agent; the default implementer is **Codex** (`IMPL_AGENT` in
`execute.yml`). Use `needs-decision` as the only decision-blocking label; do not introduce
a second human-decision label.

| Label | Meaning |
|---|---|
| `needs-spec` | Trigger Claude's spec-drafting pass on this issue |
| `spec-drafted` | Claude has posted a spec + open-questions comment |
| `needs-decision` | Open questions block this issue; resolve in an orchestrator session |
| `agent-ready` | Spec finalized → Codex implements |
| `contract-change` | PR may touch protected contract files (`packages/shared-schemas/**`, `docs/*` contracts, `.github/workflows/**`) |

Current v0.1 domain labels:

| Label | Meaning |
|---|---|
| `data` | Dataset, fixture, or ingestion work |
| `analysis` | Analysis and statistics work |
| `corpus` | Corpus, RAG, retrieval, and evidence work |
| `backend` | Backend API work |
| `frontend` | Frontend web app work |
| `eval` | Evaluation and replay work |
| `mcp` | MCP and tool interface work |
| `infra` | CI, deployment, and repo automation |

See `.github/ISSUE_TEMPLATE/` and `.github/pull_request_template.md`.
