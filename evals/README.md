# Eval Runner

The eval runner is an offline skeleton for the pytest-based eval system described in
`docs/EVALS.md`. It currently executes one deterministic runner smoke case and writes an
`EvalRun` JSON report. It does not call a live model.

Run it with:

```sh
make eval-smoke
make eval
```

Both commands write ignored report artifacts under `evals/results/`.

## Report artifact

The report JSON mirrors the protected `EvalRun` envelope:

```json
{
  "id": "eval_run_20260623T120000000000Z",
  "suite": "runner-smoke",
  "mode": "smoke",
  "results": [
    {
      "case_id": "case_runner_smoke",
      "passed": true,
      "checks": [
        {
          "kind": "schema_validity",
          "passed": true,
          "detail": "Smoke case produced a valid EvalResult envelope."
        }
      ],
      "trace_step_ids": []
    }
  ],
  "score": 1.0,
  "created_at": "2026-06-23T12:00:00Z"
}
```

`trace_step_ids` is present for trace replay compatibility. The current smoke case does not
invoke the tool registry, so it records an explicit empty list rather than inventing tool
call traces.
