# REVIEW.md — shared review rubric

Loaded by **both** general reviewer agents (`claude` and `codex`) in
`.github/workflows/review.yml`. Each agent does ONE comprehensive review covering all the
areas below — we deliberately run two independent vendors over the same rubric rather than
splitting personas across jobs.

## Severity calibration

- **P0** (must-fix; blocks merge): the change must not ship — security hole, data loss,
  corruption, or a regression on a critical user-facing path.
- **P1** (should-fix; blocks merge): a correctness bug, missing error handling on a
  non-trivial branch, a broken/contract-violating change, or an accessibility blocker.
- **P2** (nit; does NOT block): optional polish, judgment-call suggestions.

Reserve P0/P1 for findings you can **cite** — a `file:line`, an explicit rule in
`AGENTS.md` / `docs/`, or a concrete counter-example. Judgment calls default to **P2**. The
gate is **fail-closed**, so a false-positive P1 costs the author a round trip — be precise.

## What to look for (one pass, all areas)

- **Correctness & reliability** — logic bugs, unhandled error paths, race conditions, edge
  cases, broken tests. (Test-coverage gaps: only P1 if a non-trivial new branch is untested.)
- **Security** — injection, secrets in code/logs, missing authz/project-scoping, unsafe
  arbitrary SQL/filesystem/tool access, fabricated provenance. (See `docs/SECURITY.md`.)
- **Contracts & traces** (project-specific) — changes to `packages/shared-schemas/**` or
  protected `docs/*` only in a PR labeled `contract-change`; every new/modified tool must be
  traced (`docs/TRACE_MODEL.md`); a `source-derived` report claim must cite evidence.
- **Simplification** — verifiable duplication, dead code, or needless complexity. Flag P1
  only when concrete (a real duplicate / dead branch), else P2.
- **Product/UX** — for UI changes: loading/empty/error states, no untraced fake tool output,
  fixture data clearly marked.

## Skip (no findings against these)

- `*.db`, `*.db-wal`, `*.db-shm`, `demo_data/**` runtime artifacts; `uv.lock`, lockfiles;
  `node_modules/`, `.next/`, `dist/`, `.venv/`, `__pycache__/`; auto-generated migrations.
- Don't flag style/formatting (a formatter/linter owns it) or missing type annotations
  (the typechecker owns it).
- Don't flag pre-existing issues unmodified by this PR.

## Nit volume
Cap **P2** at **5 per review**. Beyond that, write `+ N similar` in the tally line.

## Output format
Post one PR comment that starts with a tally (`0 P0, 1 P1, 2 P2`), then a short audit trail:

- `Reviewed files:` changed files or globs actually inspected.
- `Checks run/inspected:` commands, CI jobs, or explicit `not run` notes.
- `Pass rationale:` one concise sentence explaining why there are no blocking findings, or
  what the review focused on before listing findings.
- `Residual risk:` remaining test gaps, assumptions, or `None noted`.

Then list findings sorted by severity using the exact headings `### P0`, `### P1`, `### P2`
(each with a one-line title and a `file:line` cite). End with the marker:
`<!-- reviewer:NAME sha:HEADSHA -->`. If nothing blocks, lead with `No blocking issues.`

Then print, as the **final line of stdout**, exactly one of:
- `REVIEW_VERDICT: PASS` — no P0 and no P1
- `REVIEW_VERDICT: FAIL` — one or more P0/P1

## Gate
The review job grades on the final `REVIEW_VERDICT` line. `FAIL` (or a missing verdict, or a
timeout) fails the job → branch protection blocks auto-merge. Both reviewers are required, so
the stricter verdict wins.

Exception: if the local Claude CLI exits before reviewing with a recognized usage/session
limit message, the harness posts a `reviewer:claude ... skipped`
comment and passes `review (claude)` as an availability skip. This is not a review verdict;
it exists only to avoid blocking auto-merge on local subscription quota exhaustion. Codex
review remains required and fail-closed.
