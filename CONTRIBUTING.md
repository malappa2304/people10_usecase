# Contributing

Thanks for working on the Chandan Aerospace lakehouse. This page is the short form; longer detail lives in [`docs/04_cicd_strategy.md`](docs/04_cicd_strategy.md).

## Branching

```
feature/* ──▶ develop ──▶ uat ──▶ main
```

- Branch off `develop` for features and fixes.
- One PR per concern — don't bundle unrelated changes.
- Conventional Commits enforced via PR title check: `feat(adf): add supplier file event trigger`.

## Before you open a PR

1. Run unit tests locally: `PYTHONPATH=poc pytest poc/tests/ -v --cov=poc/databricks/lib --cov-fail-under=80`.
2. `ruff check poc/` and `ruff format poc/`.
3. `terraform fmt -recursive poc/infrastructure/terraform/`.
4. Walk the PR template checklist — every box that applies.

## Code style

- **Python:** PEP 8 via `ruff`; type hints on every public function in `poc/databricks/lib/` (`mypy --strict`).
- **PySpark notebooks:** keep notebook code thin; logic that can be tested goes in `poc/databricks/lib/`.
- **Terraform:** modules in `poc/infrastructure/terraform/`; one resource concern per file.
- **SQL (Synapse):** idempotent DDL (`IF OBJECT_ID … DROP` / `IF NOT EXISTS`); `sqlfluff` clean.
- **YAML / ADF JSON:** 2-space indent; field order — `name` first, `type` second, then `properties`.

## What needs which review (CODEOWNERS)

- Networking, Key Vault, security workflows → `@security-team`
- DQ rules + DLT expectations → `@quality-engineering`
- Reconciliation tolerance + cutover gate → `@migration-pmo`
- Synapse schema / curated views → `@analytics-team`
- Everything else → `@data-platform-team`

## Schema changes

Breaking changes to Silver / Gold tables require a paired up + down migration script under `poc/synapse/migrations/`. The PR template enforces this with a checkbox.

## Secrets

- Never commit secrets. `gitleaks` runs on every PR and will block merge.
- Service-to-service auth is **managed identity only**. Federation for CI/CD is OIDC; no service principals.
- Local dev secrets go in `.env.local` (already gitignored).

## Tests

- Add a unit test for any new function in `poc/databricks/lib/`.
- Add a functional test case to `qa/test_cases/` for any new pipeline behaviour. Severity drives regression frequency.
- Mark each new test with the design-doc section it covers.

## Releases

Tagged on `main` only:

```
git tag -s v1.4.0 -m 'Wave 3 — Manufacturing'
git push origin v1.4.0
```

`release.yml` cuts a GitHub Release with auto-changelog + SBOM, then dispatches the prod CD workflows.
