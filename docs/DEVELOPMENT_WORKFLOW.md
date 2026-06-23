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
  ├─ claude-review → claude CLI session (tmux, self-hosted)    (check-run: claude-review)
  └─ codex-review  → codex  CLI session (tmux, self-hosted)    (check-run: codex-review)
        │
        ▼  branch protection requires: ci + claude-review + codex-review all green
        ▼
  GitHub native auto-merge (squash) → merges with NO human click
```

**All PRs auto-merge on green.** There is no required human approval.

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
4. **As its final action, creates a GitHub check-run** (`claude-review` / `codex-review`)
   with conclusion `success` if no P0/P1, else `failure`.

### The gating wrinkle

tmux spawns are fire-and-forget (the workflow does not wait for the agent to finish). A
**watchdog job** with a timeout fails the corresponding check-run if a reviewer never
reports, so a dead agent blocks merge rather than silently passing.

## Branch protection (set after Phase 1, once check names exist)

Require status checks: `ci`, `claude-review`, `codex-review`. Enable "Allow auto-merge".
No required reviewers (auto-merge is the whole point).

## Governance change (vs HANDOFF)

| HANDOFF said | This repo does | Why |
|---|---|---|
| Agents may not merge; human final merge required | All PRs auto-merge on green | Owner decision; demonstrate confidence in the gate |
| ≥1 human approval | 0 human approvals | The dual model-review + CI + eval gate replaces it |
| CODEOWNERS review required for protected files | CODEOWNERS advisory only | Kept to mark contract-sensitive files |

**Positioning note:** for the Nomic audience, the hero is the *strength of the gate*
(CI + evals + two independent model reviewers, P0/P1 clean), not the absence of humans.

## Labels, issue & PR templates

See `.github/ISSUE_TEMPLATE/` and `.github/pull_request_template.md`. Label taxonomy is
defined in `HANDOFF.md` §27 and finalized under SPEC-008.
