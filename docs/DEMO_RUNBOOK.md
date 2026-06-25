# Demo Deployment Runbook

This runbook covers the v0.1 Railway demo reset and smoke path.

## Railway Services

Deploy two Railway services from this repository:

- API service: `uv run --project services/api uvicorn fpw_api.app:app --host 0.0.0.0 --port $PORT`
- Web service: `pnpm install --frozen-lockfile && pnpm --filter @fpw/web build`, then `pnpm --filter @fpw/web start`

The root `Procfile` declares matching `api` and `web` process commands for Railway service
configuration.

Set the web service variable `FPW_API_BASE_URL` to the public API service URL so `/api/fpw/*`
rewrites reach FastAPI.

## Required Environment Variables

- `DATABASE_URL`: Railway Postgres URL once durable state is enabled.
- `APP_BASE_URL`: public API base URL, used by deployment smoke and OpenRouter request metadata.
- `FPW_API_BASE_URL`: public API base URL for the Next.js service rewrite.
- `MCP_DEMO_TOKEN`: bearer token for the mounted MCP endpoint.
- `MODEL_PROVIDER`: `openrouter` for the live demo.
- `OPENROUTER_MODEL`: current Kimi model, default `moonshotai/kimi-k2`.
- `OPENROUTER_API_KEY`: set only in Railway variables or retrieved locally with `sec`; never commit it.
- `FPW_USE_MOCK_MODEL`: `false` for live demo, `true` for deterministic local/CI fallback.
- `ARTIFACT_ROOT`: Railway volume mount for project artifacts when persistent artifact storage is enabled.

Local secret retrieval pattern:

```bash
export OPENROUTER_API_KEY="$(sec get functional-proteomics-workbench OPENROUTER_API_KEY)"
```

Do not print the key. If the project secret file does not exist yet, create it with the
local `sec` workflow before running the live adapter.

## Reset And Replay

```bash
make demo-reset
make demo-replay
make eval-smoke
```

`make demo-reset` removes stale `proj_demo` state, reseeds the approved public Perturb-PBMC
fixture, and leaves committed web artifacts untouched. `make demo-replay` also rebuilds the
dashboard demo artifacts and exports trace/eval replay artifacts.

## Deployment Smoke

For a live Railway API:

```bash
APP_BASE_URL=https://your-api-service.up.railway.app make deploy-smoke
```

For local deterministic replay without HTTP:

```bash
PYTHONPATH="$PWD" uv run --project services/api python scripts/deployment_smoke.py --skip-http
```

The smoke check verifies runtime adapter mode, `/ready`, and a deterministic demo reset. It
reports only whether `OPENROUTER_API_KEY` is configured; it never prints secret values.

## Final Pre-Recording Checklist

- Railway API `/ready` returns `ready`.
- Railway web service opens the dashboard and chat panel.
- `make demo-reset` and `make eval-smoke` pass from a clean checkout.
- `make demo-replay` is run only when committed dashboard artifacts intentionally need refresh.
- Web chat uses real OpenRouter/Kimi when `OPENROUTER_API_KEY` is present.
- Deterministic fallback is confirmed with `FPW_USE_MOCK_MODEL=true`.
- Trace page shows web and eval traces with no secret-bearing fields.
- Report page cites only approved deterministic corpus sources.
