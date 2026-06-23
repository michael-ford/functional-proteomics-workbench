#!/usr/bin/env bash
# Implementation agent (default: Codex), triggered by the `agent-ready` label. Sets up a git
# worktree, then spawns the implementer CLI in tmux (fire-and-forget) so it can be attached
# and steered: `tmux attach -t fpw-agents`. The agent implements the issue, commits, pushes
# branch agent/issue-N, and opens a PR — which then flows through review + auto-merge.
#
# Auth: uses the runner host's ambient `gh` login (a REAL user), NOT the ephemeral
# GITHUB_TOKEN, so the PR it opens TRIGGERS the review/automerge workflows. We therefore strip
# the Actions checkout's token header from the worktree and rely on `gh auth setup-git`.
#
# Vendor-swap: IMPL_AGENT (codex | claude).
#
# Usage: scripts/spawn-impl-agent.sh <issue_number>
set -euo pipefail

ISSUE="${1:?usage: spawn-impl-agent.sh <issue_number>}"
REPO="${GH_REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
IMPLEMENTER="${IMPL_AGENT:-codex}"

SESSION="fpw-agents"
WINDOW="issue-${ISSUE}"
BRANCH="agent/issue-${ISSUE}"
WT_ROOT="${HOME}/fpw-agent-workspaces"
WORKDIR="${WT_ROOT}/issue-${ISSUE}"
TMP="${RUNNER_TEMP:-/tmp}/fpw-impl"; mkdir -p "$TMP" "$WT_ROOT"
PROMPT="${TMP}/issue-${ISSUE}.prompt"
RUNSH="${TMP}/issue-${ISSUE}.run.sh"

case "$IMPLEMENTER" in
  codex)  BIN=codex ;;
  claude) BIN=claude ;;
  *) echo "::error::unknown IMPL_AGENT '$IMPLEMENTER'"; exit 1 ;;
esac
command -v "$BIN" >/dev/null 2>&1 || { echo "::error::'$BIN' not installed on runner"; exit 1; }

# Make git push use the host user's ambient credentials (not GITHUB_TOKEN).
gh auth setup-git 2>/dev/null || true

# Fresh worktree from origin/main.
git fetch -q origin main
if [ -d "$WORKDIR" ]; then git worktree remove --force "$WORKDIR" 2>/dev/null || rm -rf "$WORKDIR"; fi
git worktree prune
git branch -D "$BRANCH" 2>/dev/null || true
git worktree add -q -b "$BRANCH" "$WORKDIR" origin/main

# Strip the Actions checkout's GITHUB_TOKEN auth header + reset origin to a plain URL so the
# agent's push/PR uses ambient `gh` creds (and thus triggers downstream workflows).
git config --unset-all "http.https://github.com/.extraheader" 2>/dev/null || true
git -C "$WORKDIR" remote set-url origin "https://github.com/${REPO}.git"
echo "worktree: $WORKDIR on $BRANCH"

cat > "$PROMPT" <<EOF
You are implementing issue #${ISSUE} in ${REPO}. You are on a fresh worktree at ${WORKDIR},
branch ${BRANCH} (based on origin/main).

1. Read the issue and its spec/comments: \`gh issue view ${ISSUE} --comments\`.
2. Read AGENTS.md and the relevant docs/ contracts. Follow them. Do NOT change protected
   contract files (packages/shared-schemas/**, docs/DATA_CONTRACTS.md, docs/MCP_TOOLS.md,
   docs/TRACE_MODEL.md, docs/EVALS.md, docs/SECURITY.md, .github/workflows/**) unless the
   issue is labeled contract-change.
3. Implement the issue with a focused diff; add tests where the repo expects them.
4. Commit with a clear message, then \`git push -u origin ${BRANCH}\`.
5. Open a PR: \`gh pr create --fill --head ${BRANCH}\`, body linking "Closes #${ISSUE}".
   It will be reviewed by Claude + Codex and auto-merged once CI + both reviews are green.

If the issue depends on an unresolved item in docs/OPEN_QUESTIONS.md, stop and comment on the
issue asking for a human decision instead of guessing.
EOF

case "$IMPLEMENTER" in
  codex)  AGENT_INVOCATION="codex exec --skip-git-repo-check -s danger-full-access \"\$(cat '${PROMPT}')\"" ;;
  claude) AGENT_INVOCATION="claude --dangerously-skip-permissions \"\$(cat '${PROMPT}')\"" ;;
esac

cat > "$RUNSH" <<EOF
#!/usr/bin/env bash
cd "${WORKDIR}"
${AGENT_INVOCATION}
EOF
chmod +x "$RUNSH"

# Spawn in tmux, fire-and-forget. Reap a dead window of the same name; bail on a live one.
tmux has-session -t "$SESSION" 2>/dev/null || tmux new-session -d -s "$SESSION" -n scratch
if tmux list-windows -t "$SESSION" -F '#W' 2>/dev/null | grep -qx "$WINDOW"; then
  PANE_CMD=$(tmux list-panes -t "${SESSION}:${WINDOW}" -F '#{pane_current_command}' | head -1)
  if [ "$PANE_CMD" = "$BIN" ]; then echo "::error::live agent already in ${SESSION}:${WINDOW}"; exit 1; fi
  tmux kill-window -t "${SESSION}:${WINDOW}" 2>/dev/null || true
fi
tmux new-window -t "${SESSION}:" -n "$WINDOW" -c "$WORKDIR"
tmux kill-window -t "${SESSION}:scratch" 2>/dev/null || true
tmux send-keys -t "${SESSION}:${WINDOW}" "bash '${RUNSH}'" Enter
echo "Spawned ${IMPLEMENTER} implementer in tmux ${SESSION}:${WINDOW} (attach: tmux attach -t ${SESSION})"
