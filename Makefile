# Functional Proteomics Workbench — developer entrypoints (stubs; filled during IMPL wave)
.PHONY: setup test lint typecheck gen-types eval eval-smoke run-local demo-reset ingest-demo-data build-corpus seed-demo-project

setup:            ## install deps (TODO)
	@echo "TODO: setup"
test:             ## run all tests (TODO)
	uv run --project packages/shared-schemas pytest
lint:             ## lint (TODO)
	@echo "TODO: lint (nothing to lint yet — passing)"
typecheck:        ## typecheck (TODO)
	@echo "TODO: typecheck (nothing to check yet — passing)"
gen-types:        ## generate frontend TypeScript types from shared Pydantic schemas
	uv run --project packages/shared-schemas python -m shared_schemas.export_schema --output packages/shared-schemas/schema/shared-schemas.schema.json
	mkdir -p packages/shared-schemas/generated
	pnpm dlx json-schema-to-typescript -i packages/shared-schemas/schema/shared-schemas.schema.json -o packages/shared-schemas/generated/types.ts
eval:             ## run full eval suite (TODO)
	@echo "TODO: eval"
eval-smoke:       ## run deterministic CI-safe eval cases (TODO)
	@echo "TODO: eval-smoke (no end-to-end pipeline yet — informational)"
run-local:        ## run app locally (TODO)
	@echo "TODO: run-local"
ingest-demo-data: ## ingest Perturb-PBMC subset (TODO)
	@echo "TODO: ingest-demo-data"
build-corpus:     ## build entity-aware RAG corpus (TODO)
	@echo "TODO: build-corpus"
seed-demo-project:## seed the demo project (TODO)
	@echo "TODO: seed-demo-project"
demo-reset:       ## reset demo state (TODO)
	@echo "TODO: demo-reset"
