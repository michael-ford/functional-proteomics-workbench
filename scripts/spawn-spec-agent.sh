#!/usr/bin/env bash
# Spec-writer: Claude drafts a structured specification on a freshly opened issue, posts it as
# a comment, and labels the issue `spec-drafted`. You review/curate, then add `agent-ready` to
# hand it to the implementer (Codex). Runs headless to completion (no steering needed).
#
# Auth: `claude` inherits local subscription auth on the runner host. `gh` uses GH_TOKEN.
#
# Usage: scripts/spawn-spec-agent.sh <issue_number>
set -euo pipefail

ISSUE="${1:?usage: spawn-spec-agent.sh <issue_number>}"
REPO="${GH_REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
MODEL="${REVIEW_MODEL:-sonnet}"
TMP="${RUNNER_TEMP:-/tmp}/fpw-spec"
mkdir -p "$TMP"
PROMPT="${TMP}/issue-${ISSUE}.prompt"

if ! command -v claude >/dev/null 2>&1; then
  echo "::error::'claude' not installed on runner"; exit 1
fi

cat > "$PROMPT" <<EOF
You are drafting an implementation specification for issue #${ISSUE} in ${REPO}. Your MOST
important deliverable is a sharp **Open Questions / Blockers** list — this issue will be
resolved by a human-led orchestrator session that burns through those questions before the
issue is tagged \`agent-ready\` for the implementer. Surface ambiguity; do not paper over it.

1. Read the issue: \`gh issue view ${ISSUE} --comments\`.
2. Read AGENTS.md, docs/PROJECT_BRIEF.md, docs/ARCHITECTURE.md, docs/DATA_CONTRACTS.md,
   docs/MCP_TOOLS.md, docs/OPEN_QUESTIONS.md, and any docs relevant to the issue. Stay
   consistent with these contracts. Do NOT invent answers to open questions.
3. Post ONE comment (\`gh issue comment ${ISSUE} --body "..."\`) with a spec following
   .github/ISSUE_TEMPLATE/implementation.md (Goal, Background, Relevant Docs, Files Likely
   Involved, Stable Contracts That Must Not Change, Implementation Steps, Acceptance Criteria,
   Required Tests, Out of Scope). Reference real files/contracts. Make **Open Questions /
   Blockers** the headline section: each as a crisp, decidable question with options where you
   can. End the comment with the marker: <!-- spec:claude -->
4. Label the issue: \`gh issue edit ${ISSUE} --add-label spec-drafted\`. If you raised any
   blocking open questions, ALSO add \`--add-label needs-decision\`.

Do not modify repository files — this is a planning artifact. The issue becomes \`agent-ready\`
only after a human resolves the open questions.
EOF

echo "Claude drafting spec for issue #${ISSUE} ..."
claude -p "$(cat "$PROMPT")" \
  --model "$MODEL" \
  --allowedTools 'Bash(gh:*),Read,Glob,Grep' \
  --permission-mode acceptEdits
echo "spec draft complete for issue #${ISSUE}"
