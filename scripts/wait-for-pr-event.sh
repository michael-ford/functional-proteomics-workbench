#!/usr/bin/env bash
# Token-efficient PR watcher for interactive implementation agents.
#
# Resolves the PR from the current branch via `gh pr view`, then blocks until a meaningful
# transition happens. Output is deliberately terse so a long-lived Codex goal session wakes
# with one compact status line instead of accumulating polling logs.
#
# Usage: scripts/wait-for-pr-event.sh [--timeout seconds] [--interval seconds]
set -euo pipefail

TIMEOUT=900
INTERVAL=45
REPO="${GH_REPO:-}"
REQUIRED_CHECKS="${REQUIRED_CHECKS:-ci,review (claude),review (codex)}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --timeout)
      TIMEOUT="${2:?--timeout requires seconds}"
      shift 2
      ;;
    --interval)
      INTERVAL="${2:?--interval requires seconds}"
      shift 2
      ;;
    --repo)
      REPO="${2:?--repo requires owner/name}"
      shift 2
      ;;
    -h|--help)
      echo "usage: wait-for-pr-event.sh [--timeout seconds] [--interval seconds] [--repo owner/name]"
      exit 0
      ;;
    *)
      echo "usage: wait-for-pr-event.sh [--timeout seconds] [--interval seconds] [--repo owner/name]" >&2
      exit 2
      ;;
  esac
done

if [ -z "$REPO" ]; then
  REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
fi

fetch_pr() {
  local branch
  branch="$(git branch --show-current 2>/dev/null || true)"
  if [ -n "$branch" ]; then
    gh pr view "$branch" --repo "$REPO" --json number,state,mergeStateStatus,statusCheckRollup,latestReviews,comments 2>/dev/null || true
  else
    gh pr view --json number,state,mergeStateStatus,statusCheckRollup,latestReviews,comments 2>/dev/null || true
  fi
}

normalize() {
  local raw_file rc
  raw_file="$(mktemp)"
  printf '%s' "$1" > "$raw_file"
  rc=0
  set +e
  python3 - "$REQUIRED_CHECKS" "$raw_file" <<'PY'
import json
import sys

required = {item.strip() for item in sys.argv[1].split(",") if item.strip()}
raw = open(sys.argv[2], encoding="utf-8").read()

if not raw.strip():
    print(json.dumps({"exists": False}))
    raise SystemExit

try:
    pr = json.loads(raw)
except json.JSONDecodeError:
    print(json.dumps({"exists": False}))
    raise SystemExit

failure_conclusions = {
    "ACTION_REQUIRED",
    "CANCELLED",
    "FAILURE",
    "FAILED",
    "STARTUP_FAILURE",
    "TIMED_OUT",
}
success_conclusions = {"SUCCESS", "NEUTRAL", "SKIPPED"}
terminal_conclusions = failure_conclusions | success_conclusions
failure_states = {"ERROR", "FAILURE", "FAILED"}
success_states = {"SUCCESS", "PASSED"}
terminal_states = {"COMPLETED"}
trusted_associations = {"OWNER", "MEMBER", "COLLABORATOR"}


def check_name(check: dict) -> str:
    return (
        check.get("name")
        or check.get("context")
        or check.get("workflowName")
        or check.get("workflow")
        or ""
    )


def compact_check(check: dict) -> dict[str, str | bool]:
    conclusion = (check.get("conclusion") or "").upper()
    status = (check.get("status") or check.get("state") or "").upper()
    if conclusion in failure_conclusions or status in failure_states:
        result = "failure"
    elif conclusion in success_conclusions or status in success_states:
        result = "success"
    elif conclusion in terminal_conclusions or status in terminal_states:
        result = conclusion.lower() or "terminal"
    else:
        result = "pending"
    return {
        "name": check_name(check),
        "result": result,
        "terminal": result != "pending",
    }


checks = {}
for check in pr.get("statusCheckRollup") or []:
    name = check_name(check)
    if not name:
        continue
    if required and name not in required:
        continue
    checks[name] = compact_check(check)


def actor_type(item: dict) -> str:
    author = item.get("author") or item.get("user") or {}
    return author.get("__typename") or author.get("type") or ""


def is_trusted_human_comment(item: dict) -> bool:
    return (
        item.get("authorAssociation") in trusted_associations
        or item.get("author_association") in trusted_associations
    ) and actor_type(item) != "Bot"


comments = [item for item in pr.get("comments") or [] if is_trusted_human_comment(item)]
reviews = pr.get("latestReviews") or pr.get("reviews") or []


def event_token(items: list[dict]) -> str:
    pieces = []
    for item in items:
        pieces.append(
            "|".join(
                [
                    str(item.get("id") or ""),
                    str(item.get("submittedAt") or item.get("createdAt") or item.get("updatedAt") or ""),
                    str((item.get("author") or item.get("user") or {}).get("login") or ""),
                ]
            )
        )
    return ";".join(sorted(pieces))


normalized = {
    "exists": True,
    "number": pr.get("number"),
    "state": pr.get("state") or "",
    "merge": pr.get("mergeStateStatus") or "",
    "checks": checks,
    "review_token": event_token(reviews),
    "comment_token": event_token(comments),
    "review_count": len(reviews),
    "comment_count": len(comments),
}
print(json.dumps(normalized, sort_keys=True))
PY
  rc="$?"
  set -e
  rm -f "$raw_file"
  return "$rc"
}

print_event() {
  python3 - "$1" "$2" <<'PY'
import json
import sys

kind = sys.argv[1]
state = json.loads(sys.argv[2])
number = state.get("number") or "unknown"

if kind == "merged":
    print(f"MERGED pr={number} state=MERGED")
elif kind == "merge":
    print(f"MERGE_STATE pr={number} state={state.get('merge') or 'UNKNOWN'}")
elif kind == "check_failure":
    failed = sorted(
        name
        for name, check in (state.get("checks") or {}).items()
        if check.get("result") == "failure"
    )
    print(f"CHECK_FAILURE pr={number} checks={','.join(failed) or 'unknown'}")
elif kind == "check_success":
    succeeded = sorted(
        name
        for name, check in (state.get("checks") or {}).items()
        if check.get("result") == "success"
    )
    print(f"CHECK_SUCCESS pr={number} checks={','.join(succeeded) or 'unknown'}")
elif kind == "review":
    print(f"REVIEW_EVENT pr={number} reviews={state.get('review_count', 0)}")
elif kind == "comment":
    print(f"COMMENT_EVENT pr={number} maintainer_comments={state.get('comment_count', 0)}")
elif kind == "heartbeat":
    print(
        "HEARTBEAT no-change-15m "
        f"pr={number} state={state.get('state') or 'UNKNOWN'} merge={state.get('merge') or 'UNKNOWN'}"
    )
else:
    print(f"EVENT pr={number} kind={kind}")
PY
}

event_kind() {
  python3 - "$1" "${2:-}" <<'PY'
import json
import sys

current = json.loads(sys.argv[1])
previous = json.loads(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] else None

if not current.get("exists"):
    print("no_pr")
    raise SystemExit

if current.get("state") == "MERGED":
    print("merged")
    raise SystemExit

if current.get("merge") in {"DIRTY", "CONFLICTING"}:
    print("merge")
    raise SystemExit

checks = current.get("checks") or {}
if any(check.get("result") == "failure" for check in checks.values()):
    print("check_failure")
    raise SystemExit

if previous is None:
    print("")
    raise SystemExit

if current.get("merge") != previous.get("merge"):
    print("merge")
    raise SystemExit

previous_checks = previous.get("checks") or {}
success_transition = False
for name, check in checks.items():
    previous_check = previous_checks.get(name) or {}
    if not check.get("terminal"):
        continue
    if previous_check.get("result") == check.get("result"):
        continue
    if check.get("result") == "failure":
        print("check_failure")
        raise SystemExit
    if check.get("result") == "success":
        success_transition = True

if success_transition:
    print("check_success")
    raise SystemExit

if current.get("review_token") != previous.get("review_token"):
    print("review")
    raise SystemExit

if current.get("comment_token") != previous.get("comment_token"):
    print("comment")
    raise SystemExit

print("")
PY
}

raw="$(fetch_pr)"
current="$(normalize "$raw")"
kind="$(event_kind "$current")"
case "$kind" in
  no_pr) echo "NO_PR"; exit 0 ;;
  merged) print_event merged "$current"; exit 0 ;;
  merge) print_event merge "$current"; exit 0 ;;
  check_failure) print_event check_failure "$current"; exit 0 ;;
esac

previous="$current"
deadline=$(( $(date +%s) + TIMEOUT ))

while :; do
  now="$(date +%s)"
  if [ "$now" -ge "$deadline" ]; then
    print_event heartbeat "$previous"
    exit 0
  fi

  sleep "$INTERVAL"
  raw="$(fetch_pr)"
  current="$(normalize "$raw")"
  kind="$(event_kind "$current" "$previous")"
  case "$kind" in
    "") previous="$current" ;;
    no_pr) echo "NO_PR"; exit 0 ;;
    merged|merge|check_failure|check_success|review|comment)
      print_event "$kind" "$current"
      exit 0
      ;;
    *) print_event "$kind" "$current"; exit 0 ;;
  esac
done
