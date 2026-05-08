# CI/CD — what runs and why

A 5-stage GitHub Actions pipeline at [`.github/workflows/cicd.yml`](../.github/workflows/cicd.yml). Production-shape *patterns* sized for a 3-day PoC.

```
Validate → Lint → Security check → Deploy → Clean-up
```

Each stage depends on the previous one — a failure short-circuits the rest. Stage 5 always runs and reports the run's overall outcome.

---

## Stage 1 · Validate

Checks the **shape** of the code before it costs money to test it. Fast (~10–15 s).

- **Detect changed paths** — `dorny/paths-filter` flags whether Python or Terraform changed, so later stages can skip work that doesn't apply.
- **YAML** — `yamllint --strict` against [`.yamllint.yml`](../.yamllint.yml).
- **JSON / JSONL** — every `.json` parses cleanly; sample data validates line-by-line.
- **Terraform** — `terraform fmt -check` + `terraform validate`.
- **Databricks Asset Bundle** — `databricks bundle validate` against the `dev` target.

## Stage 2 · Lint

Runs only if Python or DAB config changed (or on every push to `dev`).

- **`ruff check`** — pyflakes + pycodestyle + isort + bugbear + comprehensions. Config in [`pyproject.toml`](../pyproject.toml).
- **`ruff format --check`** — formatting agreement.
- **`mypy --strict`** — on `poc/databricks/lib/` (the production-shape modules).
- **`pytest` + `chispa`** — coverage report uploaded as an artefact (87% on `pipeline_run.py`; gate intentionally not enforced for PoC scope, see TODO.md).

## Stage 3 · Security check

- **`gitleaks`** — secret scan over the full git history, on every run.
- **`pip-audit`** — CVE scan against the pinned dev-deps in [`requirements-dev.txt`](../requirements-dev.txt). Fails the run on any known vulnerability.
- **`checkov`** — IaC scan against the Terraform. `soft_fail: true` for the PoC (reports findings without blocking); production would harden this.

## Stage 4 · Deploy (skeleton, gated)

This is where the production deploy pattern lives. For the PoC scope, the Azure-touching steps are **guarded by an `if:` on environment vars** — they only run if `vars.AZURE_CLIENT_ID` is set. With no vars wired, the stage runs but skips the deploy steps cleanly.

What the stage demonstrates (when wired):

- **OIDC federation** to Azure AD — no static client secrets in repo or org. The federated credential subject scopes the trust to one GitHub Environment per workflow.
- **GitHub Environment** carries the reviewer protection (0 / 1 / 2 reviewers for dev / test / prod) and scoped variables.
- **Databricks AAD auth via `az`** — no Databricks PAT in CI.
- `databricks bundle validate → deploy → smoke run` as one deploy unit.
- `concurrency.cancel-in-progress: false` — never cancel mid-deploy.

## Stage 5 · Clean-up

- Always runs (`if: always()`) so a failed earlier stage still gets a tidy summary.
- Posts a one-line status to `$GITHUB_STEP_SUMMARY` so the run page shows results without hunting through job logs.
- **Fails the run if any earlier stage failed** — this is what surfaces a red ❌ on the PR.

---

## Cross-cutting patterns

- **Permissions least-privilege** — top-level `permissions: contents: read`. Jobs widen as they need to (`id-token: write` only where Azure OIDC is needed).
- **Concurrency** — cancel-in-progress on PRs (avoid wasted CI), never cancel `dev`-branch runs (don't leave deploys half-applied).
- **Pip cache** — `setup-python`'s `cache: pip` only on Stage 2 (where PySpark + Delta are 290+ MB); Stages 1 and 3 install small tools inline without caching.
- **Action pinning** — major-version tags today; SHA pinning + `step-security/harden-runner` is the next supply-chain step. Dependabot is wired to drive the bumps.
- **Single source of truth for dev deps** — [`requirements-dev.txt`](../requirements-dev.txt) is read by Stage 2 install + pre-commit + `make ci-local`. CI cache invalidates on its hash.

## Local mirror

Same checks, locally:

```bash
make ci-local      # ruff + mypy + tf-validate + pytest + bundle-validate
pre-commit run --all-files   # ruff + terraform fmt + gitleaks + file hygiene
```

Pre-commit hooks at [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) catch issues before they reach CI.

## What I'd add for production but didn't here

- Auto-trigger CD on push to `dev` / `test` / `prod` with environment promotion gates.
- Three GitHub Environments with reviewer chains and wait timers.
- Pin every action by SHA, not major version; add `step-security/harden-runner`.
- Heavier IaC scanning (`tflint`, `tfsec`) plus `actions/dependency-review` on PRs.
- Sibling CD workflows for Synapse DDL apply, Terraform apply, ADF push.
- Tests for `format_readers.py` and `reconciliation.py` so `--cov-fail-under=80` is meaningful again.
