# Runner Setup & Branch Protection (Phase 1)

These are the one-time, admin/interactive steps the harness needs that **must be run by the
repo owner** (they need an interactive token / repo-admin). Run them on the Mac that will host
the runner. The CI/review/auto-merge workflows are already committed.

## 1. Register a self-hosted macOS runner (dedicated to this repo)

The existing `bestguy` runners are bound to a different repo and cannot be reused. Register a
fresh one (same Mac is fine):

```bash
# Get a registration token (repo admin):
gh api -X POST repos/michael-ford/functional-proteomics-workbench/actions/runners/registration-token --jq .token

mkdir -p ~/actions-runner-nomic && cd ~/actions-runner-nomic
# Download the macOS arm64 runner (check github.com/actions/runner/releases for the latest):
curl -o actions-runner-osx-arm64.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.XXX.X/actions-runner-osx-arm64-2.XXX.X.tar.gz
tar xzf actions-runner-osx-arm64.tar.gz

./config.sh \
  --url https://github.com/michael-ford/functional-proteomics-workbench \
  --token <REGISTRATION_TOKEN> \
  --name fpw-mac-runner \
  --labels macOS \
  --unattended

# Keep it alive (launchd):
./svc.sh install
./svc.sh start
```

Workflows target `runs-on: [self-hosted, macOS]`. The `self-hosted` label is implicit; the
`macOS` label is set above.

## 2. Provision the review CLIs on the runner host

- **Claude** — already installed (`claude` v2.1.186). Ensure it's logged in for the runner's
  user (`claude` inherits `~/.claude`).
- **Codex** — **not yet installed.** Until it is, the `review (codex)` job posts a
  "skipped" note and passes non-blocking (`scripts/spawn-review-agent.sh`). To enable:
  install the Codex CLI, `codex login`, then verify `codex exec` works, and add
  `review (codex)` to required checks (step 4).

## 3. Branch protection on `main` (required status checks, no human review)

> **Do this BEFORE enabling auto-merge (step 4).** With auto-merge on but no required checks,
> a PR could merge unreviewed.

Start by requiring `ci` + `review (claude)`. Add `review (codex)` once Codex is live, and
`eval-smoke` at the eval-gate activation milestone (`docs/ROADMAP.md`).

```bash
gh api -X PUT repos/michael-ford/functional-proteomics-workbench/branches/main/protection \
  --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "checks": [
      { "context": "ci" },
      { "context": "review (claude)" }
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
```

> `required_pull_request_reviews: null` = **no human approval required** — auto-merge is the
> intended path (`docs/DEVELOPMENT_WORKFLOW.md`). `strict: true` requires branches be up to
> date before merge.

## 4. Enable auto-merge on the repo (after branch protection)

```bash
gh api -X PATCH repos/michael-ford/functional-proteomics-workbench \
  -F allow_auto_merge=true -F delete_branch_on_merge=true -F allow_squash_merge=true
```

## 5. Validate on a throwaway PR

```bash
git switch -c chore/harness-smoketest
echo "harness smoke $(date)" >> docs/ROADMAP.md
git commit -am "chore: harness smoke test" && git push -u origin chore/harness-smoketest
gh pr create --fill
```

Expect: `ci` green, `review (claude)` posts a comment + verdict and clears, `review (codex)`
posts "skipped", auto-merge fires once required checks are green. **First run is also where
you tune the `claude -p` / `codex exec` flags** in `scripts/spawn-review-agent.sh` if a CLI
version differs.
