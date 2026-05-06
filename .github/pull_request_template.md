<!--
This is a merge request. Code only moves forward — feature/* → dev → test → prod.
Each transition is its own MR. See docs/05_promotion_runbook.md.

Conventional commits enforced — PR title MUST start with one of:
  feat: | fix: | docs: | refactor: | test: | chore: | ci: | infra: | deps:
followed by an optional scope.   e.g.   feat(adf): add supplier_file event trigger

For promotion MRs (dev → test, test → prod), title format:
  promote: dev → test (2026-05-08, wave 3 batch)
-->

## Summary

<!-- 1-3 sentences. What changed and why. Lead with business outcome where possible. -->

## Linked work

- Linear / Jira ticket: `XXX-1234`
- Wave / migration phase (if applicable): _e.g. Wave 3 — Manufacturing_

## Type of change

- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change (schema, API, contract)
- [ ] Infra (Terraform / Bicep)
- [ ] CI/CD pipeline
- [ ] Documentation only

## Pre-merge checklist

### Code quality
- [ ] CI green (lint, tests, IaC scan, security scan)
- [ ] Coverage delta ≥ 0% (no regression)
- [ ] mypy --strict clean for `poc/databricks/lib/`
- [ ] No new `# type: ignore` or `# noqa` without a justifying comment

### Schema & data contracts
- [ ] No breaking schema change to Silver/Gold tables, OR a paired up + down migration script is included under `poc/synapse/migrations/`
- [ ] If new Silver/Gold table — a DQ rule has been added to `dq_rules_seed.sql`
- [ ] If touching SCD2 dim — `effective_from` / `effective_to` semantics preserved

### Security
- [ ] No new public endpoints; new resources behind Private Endpoint
- [ ] No service principals — managed identity only
- [ ] No secrets in code; all references go via Key Vault
- [ ] gitleaks check passed

### Data residency / compliance
- [ ] All new resources pinned to `centralindia` if ITAR-adjacent
- [ ] Bronze retention ≥ 7 years for AS9100-relevant tables
- [ ] Lineage discoverable in Purview from new Gold table back to source

### Migration (if a Strangler Fig wave)
- [ ] Reconciliation entry added to `config/reconciliation_tolerance.yaml`
- [ ] Tolerance approved by data owner (linked here): _____
- [ ] Cutover gate verified: `within_tolerance = true` for ≥ 7 consecutive days

### CI/CD
- [ ] If touching workflows — tested on a feature branch with `workflow_dispatch`
- [ ] Environment scoping correct (no dev workflow with prod credentials)

## Risk & blast radius

<!-- Describe what breaks if this PR is wrong. One sentence. -->

## Rollback plan

<!-- One sentence — the on-call engineer at 03:00 reads this. -->

---

By opening this PR I confirm I have read [CONTRIBUTING.md](../CONTRIBUTING.md) and the
[CI/CD Strategy](../docs/04_cicd_strategy.md).
