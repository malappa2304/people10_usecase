# =============================================================================
# Makefile — one-command developer experience.
# Usage:
#   make help        # see everything
#   make test        # run unit tests with coverage gate
#   make lint        # ruff + sqlfluff
#   make smoke       # validate + smoke run on dev (needs Databricks CLI auth)
#   make tf-fmt      # terraform fmt -recursive
#   make tf-plan     # terraform plan against dev (needs az login)
#   make ci-local    # run the same checks CI runs, locally
# =============================================================================

.PHONY: help test lint lint-py lint-sql tf-fmt tf-validate tf-plan \
        bundle-validate bundle-deploy-dev smoke ci-local clean

PY        ?= python3
PYTHONPATH := poc

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ---- Python -----------------------------------------------------------------

test: ## Run pytest + chispa with coverage gate (>=80%)
	PYTHONPATH=$(PYTHONPATH) pytest poc/tests/ -v \
		--cov=poc/databricks/lib \
		--cov-report=term \
		--cov-fail-under=80

lint-py: ## ruff check + format-check + mypy --strict on production lib
	ruff check poc/
	ruff format --check poc/
	mypy --strict --ignore-missing-imports poc/databricks/lib/

# ---- SQL --------------------------------------------------------------------

lint-sql: ## sqlfluff against Synapse SQL
	sqlfluff lint --dialect tsql poc/synapse/

lint: lint-py lint-sql ## All linters

# ---- Terraform --------------------------------------------------------------

tf-fmt: ## terraform fmt -recursive
	cd poc/infrastructure/terraform && terraform fmt -recursive

tf-validate: ## terraform init -backend=false + validate
	cd poc/infrastructure/terraform && terraform init -backend=false && terraform validate

tf-plan: ## terraform plan against dev (requires az login)
	cd poc/infrastructure/terraform && terraform plan -var environment=dev -no-color

# ---- Databricks Asset Bundle ------------------------------------------------

bundle-validate: ## databricks bundle validate against dev target
	databricks bundle validate --target dev

bundle-deploy-dev: ## databricks bundle deploy --target dev (requires DATABRICKS_HOST + az login)
	databricks bundle deploy --target dev --auto-approve

smoke: bundle-validate ## Validate + smoke run of scd2_dim_material on dev
	databricks bundle run scd2_dim_material_smoke --target dev

# ---- CI mirror --------------------------------------------------------------

ci-local: lint test tf-validate bundle-validate ## Run the same checks CI runs, locally

# ---- House-keeping ----------------------------------------------------------

clean: ## Remove pyc, coverage, terraform plan artefacts
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -f .coverage coverage.xml
	rm -f poc/infrastructure/terraform/tfplan
	rm -rf .pytest_cache .ruff_cache .mypy_cache
