# REVIEW.md — shared review rubric (stub)

Both the Claude and Codex review agents read this file. Finalized under SPEC-007.

## Severity
- **P0** — must-fix before merge (correctness bug, security hole, data corruption, broken contract).
- **P1** — should-fix before merge (likely bug, missing trace on a new tool, contract drift).
- **P2** — nit (style, naming, minor cleanup). Cap: 5 per reviewer.

## Output format
Post one PR comment that starts with a tally (`0 P0, 1 P1, 2 P2`), uses exact headings
`### P0`, `### P1`, `### P2`, and ends with a marker: `<!-- reviewer:NAME sha:HEADSHA -->`.

Then, as the **final line of stdout**, print exactly one of:
- `REVIEW_VERDICT: PASS` — no P0 and no P1
- `REVIEW_VERDICT: FAIL` — one or more P0/P1

## Gate
The review job parses `REVIEW_VERDICT`. `FAIL` (or a missing verdict, or a timeout) fails the
job → branch protection blocks GitHub auto-merge. `PASS` lets the gate clear.

## Skip
data/ · *.db · build outputs · lockfiles · auto-generated migrations · pre-existing issues
outside the diff · pure style when a formatter owns it.
