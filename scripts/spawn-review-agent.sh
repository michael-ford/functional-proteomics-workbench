#!/usr/bin/env bash
# Phase 1 review harness — spawn a review agent (Claude or Codex) as a CLI session inside
# tmux on the self-hosted runner, wait for it to finish, and exit with its PASS/FAIL verdict.
# The calling GitHub Actions job inherits that exit code, so this script IS the merge gate.
#
# Auth model: the CLI inherits local subscription auth on the runner host (~/.claude for
# `claude`; `codex login` for `codex`). No model API keys live in CI secrets. The agent's
# `gh` calls authenticate via the GH_TOKEN passed from the workflow.
#
# Observability: `tmux attach -t fpw-reviews` on the runner to watch a review live.
#
# Vendor-swap point: the `case "$REVIEWER"` block below is the only thing that differs
# between Claude and Codex.
#
# Usage: scripts/spawn-review-agent.sh <reviewer> <pr_number> <head_sha>
set -euo pipefail

REVIEWER="${1:?usage: spawn-review-agent.sh <reviewer> <pr> <head_sha>}"
PR="${2:?usage: spawn-review-agent.sh <reviewer> <pr> <head_sha>}"
HEAD_SHA="${3:?usage: spawn-review-agent.sh <reviewer> <pr> <head_sha>}"

REPO="${GH_REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
TIMEOUT="${REVIEW_TIMEOUT_SECS:-900}"
MODEL="${REVIEW_MODEL:-sonnet}"
WORKDIR="$(pwd)"

SESSION="fpw-reviews"
WINDOW="pr${PR}-${REVIEWER}"
TMP="${RUNNER_TEMP:-/tmp}/fpw-review"
mkdir -p "$TMP"
PROMPT="${TMP}/${WINDOW}.prompt"
RUNSH="${TMP}/${WINDOW}.run.sh"
LOG="${TMP}/${WINDOW}.log"
DONE="${TMP}/${WINDOW}.done"
rm -f "$PROMPT" "$RUNSH" "$LOG" "$DONE"

# Map reviewer -> CLI binary.
case "$REVIEWER" in
  claude) BIN="claude" ;;
  codex)  BIN="codex" ;;
  *) echo "::error::unknown reviewer '${REVIEWER}'"; exit 1 ;;
esac

# Graceful degrade: if the reviewer's CLI is not installed, skip non-blocking so a
# not-yet-provisioned reviewer (e.g. Codex) does not wedge auto-merge.
if ! command -v "$BIN" >/dev/null 2>&1; then
  echo "::warning::'${BIN}' not installed on runner — skipping ${REVIEWER} review (non-blocking)."
  gh pr comment "$PR" --repo "$REPO" \
    --body "🟡 **${REVIEWER} review skipped** — \`${BIN}\` not installed on the runner yet. <!-- reviewer:${REVIEWER} sha:${HEAD_SHA} skipped -->" || true
  exit 0
fi

# Review prompt (shared rubric lives in REVIEW.md at the repo root).
cat > "$PROMPT" <<EOF
You are the **${REVIEWER}** code reviewer for PR #${PR} in ${REPO} (head ${HEAD_SHA}).

1. Read REVIEW.md at the repo root for the severity rubric and output format.
2. Review the diff: run \`gh pr diff ${PR}\`. Read changed files for context (read-only).
3. Post exactly ONE PR comment with your findings via \`gh pr comment ${PR} --body "..."\`,
   formatted per REVIEW.md (a tally line, then \`### P0\` / \`### P1\` / \`### P2\` sections),
   ending with the marker line: <!-- reviewer:${REVIEWER} sha:${HEAD_SHA} -->
4. Then print, as the FINAL line of your output, EXACTLY one of:
     REVIEW_VERDICT: PASS    (no P0 and no P1 findings)
     REVIEW_VERDICT: FAIL    (one or more P0 or P1 findings)

Do not modify any files. Be fast and high-signal.
EOF

# Build the per-run script (avoids tmux send-keys quoting hazards). The agent invocation is
# the vendor-swap point; flags may need tuning to the installed CLI version.
case "$REVIEWER" in
  claude)
    AGENT_INVOCATION="claude -p \"\$(cat '${PROMPT}')\" --model '${MODEL}' --allowedTools 'Bash(gh:*),Read,Glob,Grep' --permission-mode acceptEdits"
    ;;
  codex)
    # danger-full-access: the review runs on the (externally-sandboxed) runner host and needs
    # network + exec so the agent can call `gh`. read-only/workspace-write would block gh.
    AGENT_INVOCATION="codex exec --skip-git-repo-check -s danger-full-access \"\$(cat '${PROMPT}')\""
    ;;
esac

cat > "$RUNSH" <<EOF
#!/usr/bin/env bash
set -o pipefail
cd "${WORKDIR}"
export GH_TOKEN="${GH_TOKEN:-}"
${AGENT_INVOCATION} 2>&1 | tee "${LOG}"
echo "\${PIPESTATUS[0]}" > "${DONE}"
EOF
chmod +x "$RUNSH"

# Spawn inside tmux (observable). Reap any stale window for this PR+reviewer first.
tmux has-session -t "$SESSION" 2>/dev/null || tmux new-session -d -s "$SESSION" -n scratch
tmux kill-window -t "${SESSION}:${WINDOW}" 2>/dev/null || true
tmux new-window -t "${SESSION}:" -n "$WINDOW" -c "$WORKDIR"
tmux kill-window -t "${SESSION}:scratch" 2>/dev/null || true
tmux send-keys -t "${SESSION}:${WINDOW}" "bash '${RUNSH}'" Enter
echo "Spawned ${REVIEWER} review in tmux ${SESSION}:${WINDOW}  (attach: tmux attach -t ${SESSION})"

# Wait for completion or timeout.
elapsed=0; interval=5
while [[ ! -f "$DONE" ]]; do
  sleep "$interval"; elapsed=$((elapsed + interval))
  if (( elapsed >= TIMEOUT )); then
    echo "::error::${REVIEWER} review timed out after ${TIMEOUT}s"
    tmux kill-window -t "${SESSION}:${WINDOW}" 2>/dev/null || true
    exit 1
  fi
done

AGENT_RC="$(cat "$DONE" 2>/dev/null || echo 1)"
echo "----- ${REVIEWER} review log (tail) -----"
tail -n 25 "$LOG" 2>/dev/null || true
echo "-----------------------------------------"

if [[ "$AGENT_RC" != "0" ]]; then
  if [[ "$REVIEWER" == "claude" ]]; then
    LAST_LOG_LINE="$(sed '/^[[:space:]]*$/d' "$LOG" 2>/dev/null | tail -n 1 || true)"
    case "$LAST_LOG_LINE" in
      "You've hit your "*limit*"resets"*)
        echo "::warning::claude review skipped because the local Claude CLI hit a usage limit."
        gh pr comment "$PR" --repo "$REPO" \
          --body "🟡 **claude review skipped** — local Claude CLI hit a temporary usage/session limit on the runner. Required check is non-blocking for this availability failure only. <!-- reviewer:claude sha:${HEAD_SHA} skipped:usage-limit -->" || true
        exit 0
        ;;
    esac
  fi
  echo "::error::${REVIEWER} agent exited with code ${AGENT_RC}"
  exit 1
fi
# Grade on the LAST verdict line only. The prompt itself names both PASS and FAIL, and verbose
# agents (e.g. codex) echo the prompt to stdout — so grepping the whole log for FAIL yields
# false failures. The agent is instructed to print the verdict as its final line.
VERDICT_LINE="$(grep -E 'REVIEW_VERDICT:' "$LOG" | tail -n 1 || true)"
if [[ -z "$VERDICT_LINE" ]]; then
  echo "::error::${REVIEWER} produced no REVIEW_VERDICT line — failing closed."
  exit 1
elif printf '%s\n' "$VERDICT_LINE" | grep -Eq 'FAIL'; then
  echo "::error::${REVIEWER} verdict FAIL (P0/P1 present) — gating merge.  [${VERDICT_LINE}]"
  exit 1
elif printf '%s\n' "$VERDICT_LINE" | grep -Eq 'PASS'; then
  echo "${REVIEWER}: PASS  [${VERDICT_LINE}]"
  exit 0
else
  echo "::error::${REVIEWER} unparseable verdict — failing closed.  [${VERDICT_LINE}]"
  exit 1
fi
