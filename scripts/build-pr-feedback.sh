#!/usr/bin/env bash
# Trusted PR-feedback for the self-monitoring implementer. The agent reads THIS file's output,
# never raw `gh pr view --comments` (reviewer markers are just text and are spoofable on a
# public repo). Emits, for the PR's current head SHA:
#   - each check's status
#   - failing CI/eval logs (from the runner — trustworthy)
#   - maintainer-authored comments only (bot comments are NOT trusted: review.yml runs review
#     code from the PR head, so a PR could post arbitrary github-actions[bot] comments)
#
# Usage: build-pr-feedback.sh <pr_number> <out_file>
set -euo pipefail

PR="${1:?usage: build-pr-feedback.sh <pr> <out_file>}"
OUT="${2:?usage: build-pr-feedback.sh <pr> <out_file>}"
REPO="${GH_REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
HEAD_SHA="$(gh pr view "$PR" --repo "$REPO" --json headRefOid -q .headRefOid)"
[ -n "$HEAD_SHA" ] || { echo "::error::could not resolve head SHA for PR $PR"; exit 1; }

{
  echo "# PR #$PR trusted feedback (head $HEAD_SHA)"
  echo
  echo "## Check status"
  gh pr checks "$PR" --repo "$REPO" 2>/dev/null || true
  echo
  echo "## Failing CI/eval logs (current head only)"
} > "$OUT"

for rid in $(gh run list --repo "$REPO" --commit "$HEAD_SHA" \
               --json databaseId,conclusion \
               --jq '.[]|select(.conclusion=="failure")|.databaseId' 2>/dev/null); do
  echo "### run $rid (failed)" >> "$OUT"
  gh run view "$rid" --repo "$REPO" --log-failed 2>/dev/null | tail -80 >> "$OUT" || true
  echo >> "$OUT"
done

CJSON="$(mktemp)"
gh api --paginate --slurp "repos/${REPO}/issues/${PR}/comments" > "$CJSON"
python3 - "$CJSON" "$HEAD_SHA" >> "$OUT" <<'PY'
import json, sys
raw = json.load(open(sys.argv[1])); head = sys.argv[2]
comments = []
for page in raw:
    comments.extend(page) if isinstance(page, list) else comments.append(page)
TRUST = {"OWNER", "MEMBER", "COLLABORATOR"}
def trusted(c):
    # Maintainer-authored HUMAN comments only. Bot comments are NOT trusted: review.yml runs
    # spawn-review-agent.sh from the PR head, so a PR could post arbitrary github-actions[bot]
    # comments. Reviewer findings reach the agent only via the failing-CI logs above, or a
    # maintainer relaying them.
    u = c.get("user") or {}
    return c.get("author_association") in TRUST and u.get("type") != "Bot"
print("\n## Maintainer comments (current head only; reviewer bot prose is NOT auto-trusted)\n")
kept = [c for c in comments if trusted(c) and head in (c.get("body") or "")]
for c in kept:
    u = (c.get("user") or {}).get("login")
    print(f"### {u} ({c.get('author_association')})\n\n{c.get('body') or ''}\n")
if not kept:
    print("_(no maintainer comments for the current head)_")
PY
rm -f "$CJSON"
echo "$OUT"
