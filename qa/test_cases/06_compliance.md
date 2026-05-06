# Compliance Test Cases — AS9100, DGCA, ITAR-adjacent

These cases verify the controls that protect the Boeing/Airbus and Indian-defence-sector customer relationships. Failure on any **Critical** case here is grounds for blocking a release.

---

## TC-CP-001 · AS9100 — end-to-end lineage Power BI → source row
**Severity:** Critical · **Covers:** Microsoft Purview lineage export (design §6.6)

- **Given** an auditor picks a random Power BI tile cell — a single supplier OTD value for one date
- **When** they export Purview lineage filtered to that tile
- **Then** the lineage path Power BI → curated view → Synapse fact → Gold Delta → Silver Delta → Bronze raw → SAP source object is fully resolved; every hop has a row count and a transformation reference.

## TC-CP-002 · AS9100 — audit pack for a date range exports in < 10 min
**Severity:** High · **Covers:** Purview export tooling

- **Given** the auditor requests "all flagged production orders between 2025-Q4 and 2026-Q1, with full lineage"
- **When** the audit-pack script runs (Purview API + Synapse query)
- **Then** the export completes in ≤ 10 min; output is a single zip of CSV + lineage JSON; total prep time including QA review ≤ 4 days.

## TC-CP-003 · AS9100 — every Bronze write has an `ingest_run_id`
**Severity:** Critical · **Covers:** ADF Copy `additionalColumns` in `pl_sap_cdc`

- **Given** a Bronze SAP file
- **When** read with the explicit schema
- **Then** every row has a non-null `ingest_run_id` that resolves to an ADF pipeline run + a `audit.pipeline_run` row.

## TC-CP-004 · DGCA airworthiness — 7-year Bronze retention enforced
**Severity:** Critical · **Covers:** ADLS lifecycle policy (Terraform `azurerm_storage_management_policy.lifecycle`)

- **Given** a Bronze file aged 6 years 10 months
- **When** the lifecycle policy is queried
- **Then** the file is in Archive tier; deletion is scheduled for 7 years + 1 day after last modification, not before.

## TC-CP-005 · ITAR-adjacent — data residency pinned to Central India
**Severity:** Critical · **Covers:** Azure Policy + Terraform `location = "centralindia"`

- **Given** an attempt to provision a new Storage Account in a different region (`southindia`) for an ITAR-tagged resource group
- **When** the resource is deployed
- **Then** Azure Policy denies the deployment; the policy assignment is `Microsoft.Authorization/policyAssignments` with effect `deny`.

## TC-CP-006 · ITAR-adjacent — no cross-region replication enabled
**Severity:** Critical · **Covers:** ADLS replication settings on ITAR resource group

- **Given** the ITAR resource group's storage accounts
- **When** replication settings are inspected
- **Then** `account_replication_type = LRS` or `ZRS` only — never GRS / RA-GRS / GZRS that would copy to a paired region.

## TC-CP-007 · ITAR-adjacent — backup snapshots are in-region only
**Severity:** Critical · **Covers:** Recovery Services Vault region pinning

- **Given** a Recovery Services Vault for an ITAR-tagged workload
- **When** its location is read
- **Then** location = `centralindia`; vault redundancy mode = `LocallyRedundant`; no geo-restore enabled.

## TC-CP-008 · Civilian components — paired region replication is enabled
**Severity:** Medium · **Covers:** non-ITAR replication policy

- **Given** civilian-only resources (non-ITAR)
- **When** replication is inspected
- **Then** `account_replication_type = ZRS` (per Terraform `local.env == "prod"` setting); paired region (South India) receives async replication.

## TC-CP-009 · Sensitivity labels propagate from source to Gold
**Severity:** High · **Covers:** Microsoft Purview sensitivity classification

- **Given** SAP source `mara` columns are tagged `Confidential — Aerospace`
- **When** Gold table `gold.dim_material` is read in Purview
- **Then** the same sensitivity label is inherited; no downgrade through the pipeline.

## TC-CP-010 · Right-to-be-forgotten (employee data only) — supplier file purge
**Severity:** Medium · **Covers:** Bronze deletion override + Delta VACUUM

- **Given** an employee has exercised right-to-erasure on personal data tied to a supplier dispatch row
- **When** the deletion runbook is followed
- **Then** the row is purged from Bronze (override of the 7-yr retention by legal-approved exception); Silver and Gold are rebuilt; Delta `VACUUM RETAIN 0 HOURS` removes prior versions; audit row records the exception.

## TC-CP-011 · No PII in audit / dq_metrics tables
**Severity:** High · **Covers:** schema design

- **Given** `audit.pipeline_run`, `audit.dq_metrics`, `audit.reconciliation_results`
- **When** schemas are scanned
- **Then** no columns contain PII (no names, emails, IDs that resolve to a person); only synthetic ids (run_id, host) and metric values.

## TC-CP-012 · AS9100 — change record retention 90 days (CI workflow logs)
**Severity:** Medium · **Covers:** GitHub Actions retention

- **Given** the org repo settings
- **When** retention is inspected
- **Then** workflow logs are retained ≥ 90 days; release artefacts (SBOM, terraform plans) retained ≥ 14 days; both meet the AS9100 "change record" minimum.

## TC-CP-013 · Annual external audit dry-run
**Severity:** High · **Covers:** end-to-end audit readiness

- **Given** all controls above are in place for ≥ 30 days
- **When** an internal audit team performs an AS9100 dry-run
- **Then** zero major findings; ≤ 2 minor findings, each with a remediation owner; audit prep wall-clock time ≤ 4 days.
