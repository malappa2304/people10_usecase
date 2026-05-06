# Security Test Cases

Verifies the posture controls described in design §6.6 (Governance, Security, Compliance) and the CI/CD security gates in `docs/04_cicd_strategy.md` §3.4.

---

## TC-SC-001 · No public IP on data plane
**Severity:** Critical · **Covers:** Terraform `public_network_access_enabled = false` on storage, Synapse, Databricks; Private Endpoints

- **Given** the production environment is fully deployed
- **When** an external scan attempts to reach `chandanlake.dfs.core.windows.net`, `syn-chandan-prod.sql.azuresynapse.net`, the Databricks workspace URL from a non-allowlisted IP
- **Then** all attempts return network-level deny / unreachable; Defender for Cloud "publicly accessible storage" finding is absent.

## TC-SC-002 · Managed identity only — zero service principals
**Severity:** Critical · **Covers:** ADF managed identity; CI/CD OIDC

- **Given** the prod resource group
- **When** the `Microsoft.Authorization/roleAssignments` are listed
- **Then** every assignment has `principalType = ManagedIdentity` (no `ServicePrincipal` for application identity); the only `User` assignments are emergency break-glass accounts.

## TC-SC-003 · CMK is enforced on ADLS, Synapse, Databricks
**Severity:** Critical · **Covers:** Key Vault key + `customer_managed_key_enabled` Terraform settings

- **Given** the prod resources are deployed
- **When** Azure CLI inspects `az storage account show` and Synapse / Databricks equivalents
- **Then** all three show `encryption.keySource = Microsoft.Keyvault` and reference the same `lake-cmk` key.

## TC-SC-004 · Key rotation does not break running workloads
**Severity:** High · **Covers:** Key Vault `RSA-HSM` rotation policy

- **Given** a running streaming job and an in-flight Synapse load
- **When** `lake-cmk` is rotated to a new version
- **Then** both workloads continue without restart; new files are encrypted with the new key version; old files remain readable via key history.

## TC-SC-005 · Row-level security in Synapse
**Severity:** Critical · **Covers:** RLS predicate function (design §6.6)

- **Given** AAD user `eng-blr2@chandan.local` is in `plant-engineer-BLR-2`
- **When** they query `dbo.fact_supplier_otd`
- **Then** they see only `plant_code = 'BLR-2'` rows; UNION across plants returns rows only for BLR-2; attempting to filter for HYD-1 returns zero rows.

## TC-SC-006 · Column-level mask on finance fields
**Severity:** High · **Covers:** Unity Catalog column masks (design §6.6)

- **Given** non-finance user querying `gold.fact_supplier_otd`
- **When** they SELECT `delivery_qty` (allowed) and `unit_price` (masked)
- **Then** `delivery_qty` shows real values; `unit_price` shows `NULL` or a hashed token; finance group sees real values for both.

## TC-SC-007 · Secret hygiene — no secrets in repo
**Severity:** Critical · **Covers:** gitleaks CI gate

- **Given** the full git history
- **When** `gitleaks detect --redact -v --log-opts="--all"` runs
- **Then** zero findings (after the first deployment of this CI; older repos may need a baseline).

## TC-SC-008 · OIDC federation — no static client secret
**Severity:** Critical · **Covers:** federated credential per env

- **Given** the production federated identity `uai-chandan-prod-gha`
- **When** Azure AD shows its credentials
- **Then** there are zero `clientSecret` values; only `federatedIdentityCredentials` with `subject` matching `repo:malappa2304/people10_usecase:environment:prod`.

## TC-SC-009 · CI workflow least-privilege
**Severity:** High · **Covers:** every `.github/workflows/*.yml`

- **Given** every workflow file
- **When** static-checked for `permissions:` blocks
- **Then** every job has an explicit `permissions:` declaring only what it needs (`contents: read` minimum; `id-token: write` only on Azure-touching jobs).

## TC-SC-010 · Network — Private Endpoint resolution in DNS
**Severity:** High · **Covers:** Private DNS zone configuration

- **Given** a Databricks cluster in the `snet-dbx-private` subnet
- **When** it resolves `chandanlake.dfs.core.windows.net`
- **Then** resolution returns a `10.40.x.x` private IP, not a public one.

## TC-SC-011 · Defender for Cloud posture ≥ 90/100
**Severity:** Medium · **Covers:** continuous posture management

- **Given** the prod subscription
- **When** Defender for Cloud secure score is read
- **Then** score ≥ 90; zero High recommendations open; Medium recommendations have remediation tickets.

## TC-SC-012 · Audit log immutability
**Severity:** High · **Covers:** Bronze immutability + Activity Logs in Log Analytics

- **Given** a prod-deployed environment
- **When** an attacker (red-team simulation) attempts to delete or modify an `audit.pipeline_run` row directly
- **Then** the action requires Storage Account Contributor + Delta Lake catalog rights; Defender raises a HIGH alert; no production identity holds those rights simultaneously.

## TC-SC-013 · Backup tampering protection
**Severity:** High · **Covers:** ADLS soft delete + versioning

- **Given** ADLS storage account
- **When** an admin attempts to delete a Bronze file
- **Then** soft-delete keeps the file recoverable for 30 days; versioning keeps prior versions on overwrites.

## TC-SC-014 · Break-glass procedure works
**Severity:** Medium · **Covers:** emergency access pattern

- **Given** the documented break-glass account
- **When** invoked under simulated incident conditions
- **Then** account can be activated in < 5 minutes via PIM JIT; activation generates an audit log entry; PIM reverts after 4 hours automatically.
