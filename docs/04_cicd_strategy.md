# CI/CD Strategy — Chandan Aerospace Lakehouse

**Scope:** GitHub-Actions-driven CI/CD for the four artefact families in this repo — Terraform infra, ADF pipelines, Databricks notebooks/jobs, Synapse SQL — plus Python library code. Aligned with Azure Well-Architected (Operational Excellence + Security pillars) and a textbook SDLC (Plan → Code → Build → Test → Release → Deploy → Operate → Monitor).

---

## 1. Branching model and environment promotion

```
feature/* ──▶ develop ──▶ uat ──▶ main
   PR             auto         tag         tag
   CI            DEV          UAT         PROD
```

| Branch     | Environment | Auto-deploy? | Approvals | Purpose |
| ---------- | ----------- | ------------ | --------- | --- |
| `feature/*`| —           | —            | —         | Isolated work, opens a PR into `develop`. CI runs on every push. |
| `develop`  | **dev**     | yes          | 0         | Integration branch. Auto-deploys on merge. |
| `uat`      | **uat**     | yes (tag-gated) | 1 reviewer (data-platform-lead) | Pre-prod parity environment. Requires reconciliation green for migration waves. |
| `main`     | **prod**    | tag only     | 2 reviewers (data-platform-lead + security) | Production. Manual tag promotion only — never auto-deploy on merge. |

Branch protection (`.github/CODEOWNERS` enforced):
- `develop`: requires CI green + 1 reviewer.
- `uat`: requires CI green + dev-deploy green + 1 reviewer + linear history.
- `main`: requires CI green + uat-deploy green + 2 reviewers + signed commits + linear history. Force-push and direct push disabled.

## 2. Pipeline topology

| Workflow | Trigger | Jobs |
| -- | -- | -- |
| **`ci.yml`** | PR + push to `develop`/`uat`/`main` | lint-python, lint-yaml, lint-sql, python-tests (pytest+chispa, coverage gate ≥80%), terraform-validate (fmt+validate+tflint+checkov+tfsec), bicep-validate (build+lint), adf-json-schema, security-scan (gitleaks + dependency-review), summary |
| **`cd-infra.yml`** | push to `develop`/`uat`/`main` (after CI green); manual dispatch | terraform plan → manual approval gate (uat/prod) → terraform apply via OIDC; drift snapshot artefact |
| **`cd-databricks.yml`** | push to `develop`/`uat`/`main` after CI | databricks bundle validate → deploy → smoke run via Databricks CLI |
| **`cd-adf.yml`** | push to `develop`/`uat`/`main` after CI | bicep deploy ADF resource + push linked services / datasets / pipelines / triggers via `az datafactory` |
| **`cd-synapse.yml`** | push to `develop`/`uat`/`main` after CI | apply DDL via sqlcmd, refresh views, run smoke query |
| **`drift-detection.yml`** | scheduled (weekdays 06:00 UTC) | terraform plan against prod; if drift → open issue with `drift` label and post to Teams |
| **`release.yml`** | tag `v*.*.*` on `main` | generate changelog, GitHub Release, deploy to prod, post-deploy verification |
| **`_reusable-azure-login.yml`** | called by other workflows | OIDC federated login, sets up subscription + tenant context |

## 3. Azure best-practice controls baked in

### 3.1 Identity — OIDC federation, zero static secrets
Every Azure-touching job federates a short-lived token from GitHub Actions to a User-Assigned Managed Identity in Azure (`uai-chandan-<env>-gha`). No `AZURE_CREDENTIALS` JSON, no client secrets, no PAT in repo or org secrets. Federated credentials are scoped per environment per workflow:

- Subject: `repo:malappa2304/people10_usecase:environment:dev` (and `uat`, `prod`)
- Audience: `api://AzureADTokenExchange`
- RBAC: `Contributor` on `rg-chandan-<env>` only — no subscription-level roles.

This eliminates the largest single source of breach in cloud CI/CD (leaked SP secrets) and aligns with Microsoft's guidance for GitHub-to-Azure auth.

### 3.2 IaC quality gates
Three scanners, each enforced as a required check:

| Scanner    | What it catches | Severity gate |
| ---------- | --------------- | ------------- |
| `terraform fmt` + `terraform validate` | Syntax, unused vars | Any → fail |
| `tflint`   | Provider best practice, deprecated args | Any → fail |
| `checkov`  | CIS / NIST IaC misconfig (public buckets, NSG 0.0.0.0/0, unencrypted disks) | HIGH/CRITICAL → fail; MEDIUM → warn |
| `tfsec`    | Defence-in-depth on top of Checkov | HIGH/CRITICAL → fail |

For Bicep, `bicep build` + `bicep lint` + `az deployment group what-if` runs against the target env subscription. What-if output is posted as a PR comment so the reviewer sees diff before approving.

### 3.3 Application-code quality gates
- **Linters:** `ruff` (Python), `yamllint`, `sqlfluff` (Synapse SQL dialect).
- **Unit tests:** `pytest` + `chispa` for PySpark logic. Coverage gate **≥ 80%** enforced by `pytest --cov-fail-under=80`. Coverage report uploaded as artefact + PR comment via `coverage-action`.
- **Type hints:** `mypy --strict` on `poc/databricks/lib/` (the production-shape modules).
- **Notebook validation:** notebooks loaded with nbformat schema check + `databricks bundle validate` to catch parameter typos before deploy.

### 3.4 Security & compliance gates
- **`gitleaks`** on every PR: scans full diff for secrets (Azure, AWS, generic patterns). Exit non-zero on any finding.
- **`actions/dependency-review`** on PRs touching `requirements.txt` or any package manifest: blocks PRs that introduce GPL-3.0 / AGPL-3.0 transitively or any CVE ≥ HIGH.
- **CodeQL** runs nightly on `develop` for Python.
- **SBOM** generated by `anchore/sbom-action` on every release; uploaded as Release asset (CycloneDX format) for AS9100 supply-chain provenance.

### 3.5 Environment protection
GitHub Environments `dev` / `uat` / `prod` each have:
- **Required reviewers:** 0 / 1 / 2 (matching branch protection).
- **Wait timer:** 0 / 5 min / 10 min (minimum window for an "abort the merge" if a reviewer changes their mind).
- **Deployment branches:** restricted (`develop` for dev, `uat` for uat, `main` for prod).
- **Environment-scoped secrets:** subscription-id and federated-credential client-id are env-scoped; same client-id can never deploy to a different env even if compromised.

### 3.6 Concurrency, caching, idempotency
- `concurrency: { group: <env>-${{ github.ref }}, cancel-in-progress: true }` on PR CI. On CD, **cancel-in-progress is false** — once a deploy is running we let it finish to avoid leaving env half-applied.
- pip / terraform-providers / Databricks-CLI installs cached via `actions/cache`.
- Every deploy step is idempotent — `terraform apply` (state-managed), `az deployment group create` (incremental mode), `databricks bundle deploy` (declarative). Re-running on the same SHA is a no-op.

### 3.7 Observability of CI/CD itself
- Every workflow writes a structured summary to `$GITHUB_STEP_SUMMARY` (table of changes, what-if diff, test counts).
- Slack/Teams notifications on any failure on `develop`/`uat`/`main`.
- Workflow logs retained 90 days (matches AS9100 audit retention for change records).

## 4. SDLC phase mapping

| Phase | Where it lives in this repo |
| -- | -- |
| **Plan** | GitHub Issues + Project board (auto-linked via PR template); design doc in `docs/02_design_document.md` |
| **Code** | Feature branch from `develop`; conventional-commits enforced via PR title check |
| **Build** | `ci.yml` — lint, type-check, unit-test, IaC validate |
| **Test** | `qa/` test plan + cases; `tests/` unit; Databricks integration tests in dev workspace; performance tests via Databricks Workflows fixture |
| **Release** | tag `v*.*.*` on `main` → `release.yml` cuts a GitHub Release with auto-generated changelog and SBOM |
| **Deploy** | `cd-*.yml` workflows, env-scoped, OIDC-authenticated |
| **Operate** | Azure Monitor + Log Analytics + audit Delta table (see `docs/02_design_document.md` §9) |
| **Monitor** | `drift-detection.yml` for IaC drift; alerting via Action Groups |

## 5. Rollback and recovery

- **Terraform:** state stored in versioned Azure blob; rollback = `terraform apply` of the previous tagged plan or `git revert` + new release.
- **ADF:** `az datafactory` deploy is idempotent against the JSON artefacts; rollback = revert + redeploy.
- **Databricks:** Databricks Asset Bundles deploy with a `target` per env; rollback = redeploy previous bundle version. Notebook history preserved in workspace.
- **Synapse:** DDL changes are wrapped in idempotent `IF OBJECT_ID … DROP` blocks; for schema-breaking changes a paired up + down migration script is required (enforced by PR template checklist).

Mean-time-to-recover target: **< 30 min** for app-layer rollback, **< 4 h** for full infra restore (matches the DR RTO in §9 of the design doc).

## 6. What changes for migration waves

During the 18-month Strangler Fig migration the CD workflows enforce one extra gate:

```
develop → dev (auto)
uat     → uat (deploy-only)
main    → prod (deploy + parallel-run + reconciliation green)
```

`cd-infra.yml` and `cd-data-platform.yml` jobs targeting **prod** read `audit.reconciliation_results` for the affected pipeline before the deploy step, and **fail-closed** if `within_tolerance = false` for the past 7 consecutive days. This makes "you can't cut over until reconciliation says you're identical" a property of the pipeline, not a process owned by a person.

## 7. Hardening backlog (called out, not yet in scope)

- Pin every action by SHA (not tag) — prevents tag-replay supply-chain attack. Use `actions/checkout@<sha>` etc.
- Add `step-security/harden-runner` for egress allowlisting.
- Add `cosign` signing of container images (when the team adopts containerised Spark jobs).
- Move from environment-scoped secrets to fully-OIDC-federated identities for external services (Snyk, Datadog, etc.) — currently those still use PATs.
