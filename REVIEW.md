# REVIEW.md — shared review rubric (stub)

Both the Claude and Codex review agents read this file. Finalized under SPEC-007.

## Severity
- **P0** — must-fix before merge (correctness bug, security hole, data corruption, broken contract).
- **P1** — should-fix before merge (likely bug, missing trace on a new tool, contract drift).
- **P2** — nit (style, naming, minor cleanup). Cap: 5 per reviewer.

## Output format
Start with a tally (`0 P0, 1 P1, 2 P2`). Use exact headings `### P0`, `### P1`, `### P2`.
End with a marker: `<!-- reviewer:NAME -->`.

## Gate
Any `### P0` or `### P1` against the current head SHA fails this reviewer's check-run and
blocks auto-merge.

## Skip
data/ · *.db · build outputs · lockfiles · auto-generated migrations · pre-existing issues
outside the diff · pure style when a formatter owns it.
