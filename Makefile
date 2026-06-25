# Functional Proteomics Workbench — developer entrypoints (stubs; filled during IMPL wave)
.PHONY: setup test lint typecheck gen-types eval eval-smoke run-local run-web demo-reset demo-replay deploy-smoke ingest-demo-data build-corpus seed-demo-project

PNPM_STAMP := node_modules/.modules.yaml

$(PNPM_STAMP): package.json pnpm-lock.yaml pnpm-workspace.yaml apps/web/package.json
	pnpm install --frozen-lockfile

setup:            ## install deps
	pnpm install --frozen-lockfile
test:             ## run all tests (TODO)
	uv run --project packages/shared-schemas pytest packages/shared-schemas/tests
	uv run --project packages/analysis pytest packages/analysis/tests
	uv run --project packages/corpus pytest packages/corpus/tests
	uv run --project services/api pytest services/api/tests
	PYTHONPATH=$(CURDIR) uv run --project services/api pytest --rootdir=. evals/tests scripts/tests
	$(MAKE) $(PNPM_STAMP)
	pnpm test
lint:             ## lint
	uv run --project packages/analysis ruff check packages/analysis/src packages/analysis/tests
	uv run --project packages/corpus ruff check packages/corpus/src packages/corpus/tests
	uv run --project services/api ruff check services/api/src services/api/tests
	$(MAKE) $(PNPM_STAMP)
	pnpm lint
typecheck:        ## typecheck
	uv run --project packages/analysis pyright --project packages/analysis packages/analysis/src packages/analysis/tests
	uv run --project packages/corpus pyright --project packages/corpus packages/corpus/src packages/corpus/tests
	uv run --project services/api pyright --project services/api services/api/src services/api/tests
	$(MAKE) $(PNPM_STAMP)
	pnpm typecheck
	pnpm build
gen-types:        ## generate frontend TypeScript types from shared Pydantic schemas
	uv run --project packages/shared-schemas python -m shared_schemas.export_schema --output packages/shared-schemas/schema/shared-schemas.schema.json
	mkdir -p packages/shared-schemas/generated
	pnpm dlx json-schema-to-typescript -i packages/shared-schemas/schema/shared-schemas.schema.json -o packages/shared-schemas/generated/types.ts
eval:             ## run offline eval suite
	PYTHONPATH=$(CURDIR) uv run --project services/api python -m evals.runners --mode full --output evals/results/eval-latest.json
eval-smoke:       ## run deterministic CI-safe eval cases
	PYTHONPATH=$(CURDIR) uv run --project services/api python -m evals.runners --mode smoke --output evals/results/eval-smoke-latest.json
run-local:        ## run API locally
	uv run --project services/api uvicorn fpw_api.app:app --reload
run-web:          ## run web app locally
	pnpm dev:web
ingest-demo-data: ## ingest Perturb-PBMC subset (TODO)
	@echo "TODO: ingest-demo-data"
build-corpus:     ## build entity-aware RAG corpus
	uv run --project packages/corpus python -m functional_proteomics_corpus build --output .fpw_state/corpus/index.json
seed-demo-project:## seed the demo project
	uv run --project packages/shared-schemas python scripts/seed_demo_project.py
demo-reset:       ## reset demo state
	PYTHONPATH=$(CURDIR) uv run --project services/api python scripts/demo_reset.py
demo-replay:      ## rebuild dashboard demo artifacts from registry/eval replay
	PYTHONPATH=$(CURDIR) uv run --project services/api python scripts/demo_reset.py --rebuild-web-artifacts
deploy-smoke:     ## run deployment readiness smoke checks; set APP_BASE_URL for live Railway API
	PYTHONPATH=$(CURDIR) uv run --project services/api python scripts/deployment_smoke.py
