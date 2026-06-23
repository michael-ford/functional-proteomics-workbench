#!/usr/bin/env bash
# Build a TRUST-FILTERED issue context file for agents that run with host access
# (spawn-impl-agent.sh, spawn-spec-agent.sh). This is the content trust boundary.
#
# Includes: the issue title + body ONLY if the opener is a maintainer, plus comments authored
# by maintainers (author_association ∈ OWNER/MEMBER/COLLABORATOR, and not a bot). All
# untrusted / public content (including the title for non-maintainer openers) is excluded. The
# agent reads the resulting FILE (content is never evaluated by a shell), and must not fetch
# raw comments itself.
#
# Usage: build-issue-context.sh <repo> <issue_number> <out_file>
set -euo pipefail

REPO="${1:?usage: build-issue-context.sh <repo> <issue> <out_file>}"
ISSUE="${2:?usage: build-issue-context.sh <repo> <issue> <out_file>}"
OUT="${3:?usage: build-issue-context.sh <repo> <issue> <out_file>}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
gh api "repos/${REPO}/issues/${ISSUE}" > "${TMP}/issue.json"
# --slurp so multi-page results are a single valid JSON document (array of pages); flattened
# defensively in Python below.
gh api --paginate --slurp "repos/${REPO}/issues/${ISSUE}/comments" > "${TMP}/comments.json"

python3 - "${TMP}/issue.json" "${TMP}/comments.json" "$OUT" <<'PY'
import json, sys
issue = json.load(open(sys.argv[1]))
raw = json.load(open(sys.argv[2]))
# Flatten --slurp output (array of pages) or a plain array, defensively.
comments = []
for page in raw:
    comments.extend(page) if isinstance(page, list) else comments.append(page)

out = open(sys.argv[3], "w")
TRUST = {"OWNER", "MEMBER", "COLLABORATOR"}
def trusted(o):
    return o.get("author_association") in TRUST and (o.get("user") or {}).get("type") != "Bot"

# Title and body are untrusted for non-maintainer openers — neutralize both.
title = issue["title"] if trusted(issue) else "(title omitted — non-maintainer opener)"
out.write(f"# Issue #{issue['number']}: {title}\n\n")
if trusted(issue):
    out.write(f"## Description (maintainer {issue['user']['login']})\n\n{issue.get('body') or ''}\n\n")
else:
    out.write(f"## Description — OMITTED\n\nIssue opener {issue['user']['login']} is not a "
              "maintainer; title and body excluded from the trust boundary. A maintainer must "
              "restate the task in a trusted comment.\n\n")
kept = [c for c in comments if trusted(c)]
out.write(f"## Maintainer-authored comments ({len(kept)} trusted; untrusted omitted)\n\n")
for c in kept:
    out.write(f"### {c['user']['login']} ({c['author_association']})\n\n{c.get('body') or ''}\n\n")
if not kept:
    out.write("_(none)_\n")
PY
echo "$OUT"
