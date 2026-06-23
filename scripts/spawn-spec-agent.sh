#!/usr/bin/env bash
# Spec-writer: Claude drafts a structured specification + a headline Open Questions / Blockers
# list on an issue labeled `needs-spec`, posts it as a comment, and labels the issue
# `spec-drafted` (+ `needs-decision` if it raised blockers). You resolve the open questions in
# an orchestrator session, then add `agent-ready` to hand it to the implementer (Codex).
#
# Runs Claude INSIDE tmux (like the review agent) and waits for completion. This matters: a
# direct `claude -p` in the non-TTY Actions job shell can't reach the macOS keychain creds and
# fails with 401; the tmux pane provides the session context where auth works.
#
# Auth: ambient `gh` login on the runner (so the comment is authored by a maintainer and thus
# passes the implementer's trust filter). `claude` inherits local subscription auth.
#
# Trust boundary: Claude reads a pre-sanitized context file (maintainer-authored content only),
# never raw public comments. Tools are restricted to `gh issue` + read-only file tools.
#
# Usage: scripts/spawn-spec-agent.sh <issue_number>
set -euo pipefail

ISSUE="${1:?usage: spawn-spec-agent.sh <issue_number>}"
REPO="${GH_REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
MODEL="${REVIEW_MODEL:-sonnet}"
TIMEOUT="${SPEC_TIMEOUT_SECS:-900}"
HERE="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="$(pwd)"

SESSION="fpw-spec"
WINDOW="issue-${ISSUE}"
TMP="${RUNNER_TEMP:-/tmp}/fpw-spec"; mkdir -p "$TMP"
PROMPT="${TMP}/issue-${ISSUE}.prompt"
RUNSH="${TMP}/issue-${ISSUE}.run.sh"
LOG="${TMP}/issue-${ISSUE}.log"
DONE="${TMP}/issue-${ISSUE}.done"
CONTEXT="${TMP}/issue-${ISSUE}.context.md"
rm -f "$PROMPT" "$RUNSH" "$LOG" "$DONE"

command -v claude >/dev/null 2>&1 || { echo "::error::'claude' not installed on runner"; exit 1; }

# Trust-filtered context (maintainer-authored content only) — same boundary as the implementer.
bash "${HERE}/build-issue-context.sh" "$REPO" "$ISSUE" "$CONTEXT" >/dev/null
echo "sanitized context: $CONTEXT ($(wc -l < "$CONTEXT") lines)"

cat > "$PROMPT" <<EOF
You are drafting an implementation specification for issue #${ISSUE} in ${REPO}. Your MOST
important deliverable is a sharp **Open Questions / Blockers** list — this issue is resolved
by a human-led orchestrator session that burns through those questions before it is tagged
\`agent-ready\` for the implementer. Surface ambiguity; do not paper over it.

1. The maintainer-curated issue content is in the file ${CONTEXT}. Read ONLY that file for the
   task — do NOT run \`gh issue view\` or fetch raw comments (untrusted comments are excluded).
2. Read AGENTS.md, docs/PROJECT_BRIEF.md, docs/ARCHITECTURE.md, docs/DATA_CONTRACTS.md,
   docs/MCP_TOOLS.md, docs/OPEN_QUESTIONS.md, and any docs relevant to the task. Stay
   consistent with these contracts. Do NOT invent answers to open questions.
3. Post ONE comment (\`gh issue comment ${ISSUE} --body "..."\`) with a spec following
   .github/ISSUE_TEMPLATE/implementation.md (Goal, Background, Relevant Docs, Files Likely
   Involved, Stable Contracts That Must Not Change, Implementation Steps, Acceptance Criteria,
   Required Tests, Out of Scope). Reference real files/contracts. Make **Open Questions /
   Blockers** the headline section: each a crisp, decidable question with options where you
   can. End the comment with the marker: <!-- spec:claude -->
4. Label the issue: \`gh issue edit ${ISSUE} --add-label spec-drafted\`. If you raised any
   blocking open questions, ALSO add \`--add-label needs-decision\`.

You have no file-edit tools; this is a planning artifact only.
EOF

cat > "$RUNSH" <<EOF
#!/usr/bin/env bash
set -o pipefail
cd "${WORKDIR}"
claude -p "\$(cat '${PROMPT}')" --model '${MODEL}' --allowedTools 'Bash(gh issue:*),Read,Glob,Grep' 2>&1 | tee "${LOG}"
echo "\${PIPESTATUS[0]}" > "${DONE}"
EOF
chmod +x "$RUNSH"

# Spawn Claude inside tmux (session context where keychain-backed auth works) and wait.
tmux has-session -t "$SESSION" 2>/dev/null || tmux new-session -d -s "$SESSION" -n scratch
tmux kill-window -t "${SESSION}:${WINDOW}" 2>/dev/null || true
tmux new-window -t "${SESSION}:" -n "$WINDOW" -c "$WORKDIR"
tmux kill-window -t "${SESSION}:scratch" 2>/dev/null || true
tmux send-keys -t "${SESSION}:${WINDOW}" "bash '${RUNSH}'" Enter
echo "Claude drafting spec for issue #${ISSUE} in tmux ${SESSION}:${WINDOW} ..."

elapsed=0; interval=5
while [[ ! -f "$DONE" ]]; do
  sleep "$interval"; elapsed=$((elapsed + interval))
  if (( elapsed >= TIMEOUT )); then
    echo "::error::spec draft timed out after ${TIMEOUT}s"
    tmux kill-window -t "${SESSION}:${WINDOW}" 2>/dev/null || true
    exit 1
  fi
done

RC="$(cat "$DONE" 2>/dev/null || echo 1)"
echo "----- spec log (tail) -----"; tail -n 15 "$LOG" 2>/dev/null || true; echo "---------------------------"
if [[ "$RC" != "0" ]]; then echo "::error::spec agent exited ${RC}"; exit 1; fi
echo "spec draft complete for issue #${ISSUE}"
