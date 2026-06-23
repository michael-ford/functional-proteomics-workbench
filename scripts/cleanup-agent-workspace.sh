#!/usr/bin/env bash
# Clean up a fire-and-forget implementer session after an agent PR merges.
#
# Usage:
#   scripts/cleanup-agent-workspace.sh <head_ref> [pr_number]
#
# Only branches named exactly agent/issue-N are cleaned. This keeps the workflow from touching
# human branches or unrelated automation.
set -euo pipefail

HEAD_REF="${1:?usage: cleanup-agent-workspace.sh <head_ref> [pr_number]}"
PR_NUMBER="${2:-}"

if [[ ! "$HEAD_REF" =~ ^agent/issue-([0-9]+)$ ]]; then
  echo "not an agent issue branch: ${HEAD_REF}; nothing to clean"
  exit 0
fi

ISSUE="${BASH_REMATCH[1]}"
SESSION="${AGENT_TMUX_SESSION:-fpw-agents}"
WINDOW="issue-${ISSUE}"
BRANCH="agent/issue-${ISSUE}"
WT_ROOT="${FPW_AGENT_WORKTREE_ROOT:-${HOME}/fpw-agent-workspaces}"
WORKDIR="${WT_ROOT}/issue-${ISSUE}"
STATE="${WT_ROOT}/.state/issue-${ISSUE}"
ROOT="$(git rev-parse --show-toplevel)"

echo "cleaning agent workspace for issue #${ISSUE}${PR_NUMBER:+ (PR #${PR_NUMBER})}"

if tmux has-session -t "$SESSION" 2>/dev/null \
   && tmux list-windows -t "$SESSION" -F '#W' 2>/dev/null | grep -qx "$WINDOW"; then
  echo "killing tmux window ${SESSION}:${WINDOW}"
  tmux kill-window -t "${SESSION}:${WINDOW}" 2>/dev/null || true
else
  echo "tmux window ${SESSION}:${WINDOW} not present"
fi

if [ -d "$WORKDIR" ]; then
  echo "removing worktree ${WORKDIR}"
  git -C "$ROOT" worktree remove --force "$WORKDIR" 2>/dev/null || rm -rf "$WORKDIR"
else
  echo "worktree ${WORKDIR} not present"
fi

git -C "$ROOT" worktree prune

if git -C "$ROOT" show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  echo "deleting local branch ${BRANCH}"
  git -C "$ROOT" branch -D "$BRANCH" >/dev/null 2>&1 || true
else
  echo "local branch ${BRANCH} not present"
fi

if [ "${KEEP_AGENT_STATE:-0}" = "1" ]; then
  echo "keeping durable state ${STATE} because KEEP_AGENT_STATE=1"
elif [ -d "$STATE" ]; then
  echo "removing durable state ${STATE}"
  rm -rf "$STATE"
else
  echo "durable state ${STATE} not present"
fi

echo "agent cleanup complete for issue #${ISSUE}"
