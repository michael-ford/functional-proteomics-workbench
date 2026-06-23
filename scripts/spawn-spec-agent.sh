#!/usr/bin/env bash
# Spec-writer: Claude drafts a structured specification + a headline Open Questions / Blockers
# list on an issue labeled `needs-spec`, posts it as a comment, and labels the issue
# `spec-drafted` (+ `needs-decision` if it raised blockers). You resolve the open questions in
# an orchestrator session, then add `agent-ready` to hand it to the implementer (Codex).
# Runs headless to completion.
#
# Auth: ambient `gh` login on the runner (so the comment is authored by a maintainer and thus
# passes the implementer's trust filter). `claude` inherits local subscription auth.
#
# Trust boundary: like the implementer, Claude reads a pre-sanitized context file
# (maintainer-authored content only), never raw public comments. Tools are restricted to
# `gh issue` + read-only file tools (no edits, no broad gh).
#
# Usage: scripts/spawn-spec-agent.sh <issue_number>
set -euo pipefail

ISSUE="${1:?usage: spawn-spec-agent.sh <issue_number>}"
REPO="${GH_REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
MODEL="${REVIEW_MODEL:-sonnet}"
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="${RUNNER_TEMP:-/tmp}/fpw-spec"; mkdir -p "$TMP"
PROMPT="${TMP}/issue-${ISSUE}.prompt"
CONTEXT="${TMP}/issue-${ISSUE}.context.md"

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

You have no file-edit tools; this is a planning artifact only. The issue becomes
\`agent-ready\` after a human resolves the open questions.
EOF

echo "Claude drafting spec for issue #${ISSUE} ..."
claude -p "$(cat "$PROMPT")" \
  --model "$MODEL" \
  --allowedTools 'Bash(gh issue:*),Read,Glob,Grep'
echo "spec draft complete for issue #${ISSUE}"
