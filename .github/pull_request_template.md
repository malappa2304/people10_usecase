<!--
PR title is enforced as Conventional Commits via the `pr-title` CI job.
Use one of: feat / fix / docs / refactor / test / chore / ci / perf / build / revert
e.g.   `feat(databricks): add unified DLT pipeline for streaming + batch`
-->

## What

<!-- One paragraph describing the change. -->

## Why

<!-- Link to ticket / issue. State the problem this solves. -->

## Scope

- [ ] Touches code under `poc/databricks/` (notebooks, lib, or pipelines)
- [ ] Touches Terraform under `poc/infrastructure/terraform/`
- [ ] Touches Synapse SQL under `poc/synapse/`
- [ ] Docs only

## Verification

- [ ] CI green (lint + tests + tf-validate + secret-scan + pip-audit)
- [ ] Coverage ≥ 80% on `poc/databricks/lib/` (no regression)
- [ ] Tested locally where applicable: `make ci-local`
- [ ] No new secrets committed (gitleaks will block; double-checked locally)

## Notes for reviewer

<!-- Anything you specifically want eyes on. -->
