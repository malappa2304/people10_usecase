# CI/CD Strategy — Chandan Aerospace Lakehouse

**Scope:** GitHub-Actions-driven CI/CD for the four artefact families in this repo — Terraform infra, ADF pipelines, Databricks notebooks/jobs, Synapse SQL — plus Python library code. Aligned with Azure Well-Architected (Operational Excellence + Security pillars) and a textbook SDLC (Plan → Code → Build → Test → Release → Deploy → Operate → Monitor).

---

## 1. Branching model — `dev → test → prod` with merge-request promotion

```
feature/* ──MR──▶ dev ──MR──▶ test ──MR──▶ prod
   PR              auto         MR-gated      MR + tag
   CI             DEV env       TEST env      PROD env
```

Every transition is a **merge request** (GitHub pull request). No direct pushes; no force-pushes; no `--no-verify`. Code only moves forward — never sideways or backward — and only through a reviewed MR.

| Branch       | Environment | What lives here | How code lands here | Reviewers (CODEOWNERS) | Auto-deploys? |
| ------------ | ----------- | --------------- | ------------------- | ---------------------- | ------------- |
| `feature/*`  | —           | Isolated work-in-progress | `git checkout -b feature/<topic>` off `dev` | — | — |
| **`dev`**    | **DEV**     | Integration of all in-flight work | MR from `feature/*` → `dev`, CI green, 1 reviewer | data-platform-team | Yes — every merge auto-deploys to DEV |
| **`test`**   | **TEST**    | Stable, parity with prod for QA + UAT | MR from `dev` → `test`, CI green, 1 reviewer + QA sign-off | data-platform-lead + qa-team | Yes — every merge auto-deploys to TEST |
| **`prod`**   | **PROD**    | What is currently in production | MR from `test` → `prod`, **2** reviewers + signed-tag promotion | data-platform-lead + security-team + (migration-pmo if a wave) | **No** — deploy is tag-driven; reconciliation gate runs on tag push |

The `prod` branch is the production source of truth. The `main` branch is *retired* under this model — repos that still have `main` as default should rename `main → prod` once the team adopts this strategy. A note on this is in the migration backlog.

### 1.1 What a merge request must carry

Every MR must include, at minimum:

1. A description that explains **why**, links the Linear/Jira ticket, names the migration wave (if any), and lists the deploy-side blast radius.
2. Green CI (`ci.yml` summary job is the required check).
3. A reviewer ack from the right CODEOWNERS group for the paths touched.
4. The PR-template checklist completed (security, schema, migration, residency, CI/CD).
5. For schema changes: a paired up + down migration script under `poc/synapse/migrations/`.
6. For migration waves cutting over to prod: reconciliation green for ≥ 7 consecutive days for the affected pipeline (≥ 14 for SCD2 dimensions). Enforced both as a checkbox and as a fail-closed step inside `cd-infra.yml` / `cd-data-platform.yml` against `audit.reconciliation_results`.

### 1.2 Branch protection (configured in repo settings, mirrored here for the record)

| Branch | Required CI checks | Approving reviews | Restrictions |
| -- | -- | --: | -- |
| `dev`  | `CI summary` | 1 | No force-push; no direct push (must be via MR) |
| `test` | `CI summary` + dev-deploy success | 1 | Linear history; signed commits encouraged |
| `prod` | `CI summary` + test-deploy success | 2 | Linear history; **signed commits required**; tag deploys via `release.yml` only |

## 2. Pipeline topology

| Workflow | Trigger | Jobs |
| -- | -- | -- |
| **`ci.yml`** | MR + push to `dev`/`test`/`prod` | lint-python, lint-yaml, lint-sql, python-tests (pytest+chispa, coverage gate ≥80%), terraform-validate (fmt+validate+tflint+checkov+tfsec), bicep-validate (build+lint), adf-json-schema, security-scan (gitleaks + dependency-review), summary |
| **`cd-infra.yml`** | push to `dev`/`test`/`prod` (after MR merge); manual dispatch | terraform plan → manual approval gate (test/prod) → terraform apply via OIDC; drift snapshot artefact |
| **`cd-databricks.yml`** | push to `dev`/`test`/`prod` after MR | databricks bundle validate → deploy → smoke run via Databricks CLI |
| **`cd-adf.yml`** | push to `dev`/`test`/`prod` after MR | bicep deploy ADF resource + push linked services / datasets / pipelines / triggers via `az datafactory` |
| **`cd-synapse.yml`** | push to `dev`/`test`/`prod` after MR | apply DDL via sqlcmd, refresh views, run smoke query |
| **`drift-detection.yml`** | scheduled (weekdays 06:00 UTC) | terraform plan against prod; if drift → open issue with `drift` label and post to Teams |
| **`release.yml`** | tag `v*.*.*` on `prod` | generate changelog, GitHub Release, deploy to prod, post-deploy verification |
| **`_reusable-azure-login.yml`** | called by other workflows | OIDC federated login, sets up subscription + tenant context |

## 3. Azure best-practice controls baked in

### 3.1 Identity — OIDC federation, zero static secrets
Every Azure-touching job federates a short-lived token from GitHub Actions to a User-Assigned Managed Identity in Azure (`uai-chandan-<env>-gha`). No `AZURE_CREDENTIALS` JSON, no client secrets, no PAT in repo or org secrets. Federated credentials are scoped per environment per workflow:

- Subject: `repo:malappa2304/people10_usecase:environment:dev` (and `test`, `prod`)
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

For Bicep, `bicep build` + `bicep lint` + `az deployment group what-if` runs against the target env subscription. What-if output is posted as an MR comment so the reviewer sees diff before approving.

### 3.3 Application-code quality gates
- **Linters:** `ruff` (Python), `yamllint`, `sqlfluff` (Synapse SQL dialect).
- **Unit tests:** `pytest` + `chispa` for PySpark logic. Coverage gate **≥ 80%** enforced by `pytest --cov-fail-under=80`. Coverage report uploaded as artefact + MR comment via `coverage-action`.
- **Type hints:** `mypy --strict` on `poc/databricks/lib/` (the production-shape modules).
- **Notebook validation:** notebooks loaded with nbformat schema check + `databricks bundle validate` to catch parameter typos before deploy.

### 3.4 Security & compliance gates
- **`gitleaks`** on every MR: scans full diff for secrets (Azure, AWS, generic patterns). Exit non-zero on any finding.
- **`actions/dependency-review`** on MRs touching `requirements.txt` or any package manifest: blocks MRs that introduce GPL-3.0 / AGPL-3.0 transitively or any CVE ≥ HIGH.
- **CodeQL** runs nightly on `dev` for Python.
- **SBOM** generated by `anchore/sbom-action` on every release; uploaded as Release asset (CycloneDX format) for AS9100 supply-chain provenance.

### 3.5 Environment protection
GitHub Environments `dev` / `test` / `prod` each have:
- **Required reviewers:** 0 / 1 / 2 (matching branch protection).
- **Wait timer:** 0 / 5 min / 10 min (minimum window for an "abort the merge" if a reviewer changes their mind).
- **Deployment branches:** restricted (`dev` for DEV env, `test` for TEST, `prod` for PROD).
- **Environment-scoped secrets:** subscription-id and federated-credential client-id are env-scoped; same client-id can never deploy to a different env even if compromised.

A separate `prod-readonly` environment grants the drift-detection workflow read-only RBAC on the prod subscription — it can `terraform plan`, never `terraform apply`.

### 3.6 Concurrency, caching, idempotency
- `concurrency: { group: <env>-${{ github.ref }}, cancel-in-progress: true }` on MR CI. On CD, **cancel-in-progress is false** — once a deploy is running we let it finish to avoid leaving env half-applied.
- pip / terraform-providers / Databricks-CLI installs cached via `actions/cache`.
- Every deploy step is idempotent — `terraform apply` (state-managed), `az deployment group create` (incremental mode), `databricks bundle deploy` (declarative). Re-running on the same SHA is a no-op.

### 3.7 Observability of CI/CD itself
- Every workflow writes a structured summary to `$GITHUB_STEP_SUMMARY` (table of changes, what-if diff, test counts).
- Slack/Teams notifications on any failure on `dev`/`test`/`prod`.
- Workflow logs retained 90 days (matches AS9100 audit retention for change records).

## 4. SDLC phase mapping

| Phase | Where it lives in this repo |
| -- | -- |
| **Plan** | GitHub Issues + Project board (auto-linked via PR template); design doc in `docs/02_design_document.md` |
| **Code** | `feature/*` branch from `dev`; conventional-commits enforced via PR title check |
| **Build** | `ci.yml` — lint, type-check, unit-test, IaC validate |
| **Test** | `qa/` test plan + cases; `tests/` unit; Databricks integration tests in dev workspace; QA sign-off **at the `dev → test` MR**; UAT-style validation on `test` env |
| **Release** | tag `v*.*.*` on `prod` → `release.yml` cuts a GitHub Release with auto-generated changelog and SBOM |
| **Deploy** | `cd-*.yml` workflows, env-scoped, OIDC-authenticated. **Promotion is the merge of an MR**, not a manual deploy click. |
| **Operate** | Azure Monitor + Log Analytics + audit Delta table (see `docs/02_design_document.md` §9) |
| **Monitor** | `drift-detection.yml` for IaC drift; alerting via Action Groups |

Day-by-day promotion runbook: see [`05_promotion_runbook.md`](05_promotion_runbook.md).

## 5. Rollback and recovery

- **Terraform:** state stored in versioned Azure blob; rollback = `terraform apply` of the previous tagged plan or revert MR + new release.
- **ADF:** `az datafactory` deploy is idempotent against the JSON artefacts; rollback = revert MR + redeploy.
- **Databricks:** Databricks Asset Bundles deploy with a `target` per env; rollback = redeploy previous bundle version. Notebook history preserved in workspace.
- **Synapse:** DDL changes are wrapped in idempotent `IF OBJECT_ID … DROP` blocks; for schema-breaking changes a paired up + down migration script is required (enforced by PR template checklist).

Mean-time-to-recover target: **< 30 min** for app-layer rollback, **< 4 h** for full infra restore (matches the DR RTO in §9 of the design doc).

Rollback is itself an MR — a `revert` MR opened from the prod commit you want to undo, reviewed and merged like any other change. There is no "rollback button" outside of the MR flow.

## 6. What changes for migration waves

During the 18-month Strangler Fig migration the CD workflows enforce one extra gate at `test → prod`:

```
dev   → DEV  (auto on MR merge)
test  → TEST (auto on MR merge — QA sign-off in the MR review)
prod  → PROD (tag on prod branch + reconciliation green for ≥ 7 days)
```

`cd-infra.yml` and the data-plane CD jobs targeting **prod** read `audit.reconciliation_results` for the affected pipeline before the deploy step, and **fail-closed** if `within_tolerance = false` for the past 7 consecutive days. This makes "you can't cut over until reconciliation says you're identical" a property of the pipeline, not a process owned by a person.

## 7. Hardening backlog (called out, not yet in scope)

- Pin every action by SHA (not tag) — prevents tag-replay supply-chain attack. Use `actions/checkout@<sha>` etc.
- Add `step-security/harden-runner` for egress allowlisting.
- Add `cosign` signing of container images (when the team adopts containerised Spark jobs).
- Move from environment-scoped secrets to fully-OIDC-federated identities for external services (Snyk, Datadog, etc.) — currently those still use PATs.
- Rename the legacy default branch from `main` to `prod` once all in-flight branches and external links are migrated.
