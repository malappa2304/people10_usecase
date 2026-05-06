# Promotion Runbook — `dev → test → prod` via Merge Requests

A change moves through three environments. Each transition is a **merge request** (GitHub pull request). This runbook shows the day-to-day mechanics; the strategy and gates live in [`04_cicd_strategy.md`](04_cicd_strategy.md).

---

## 0. Ground rules

- **Forward only.** Code never moves sideways or backward. No cherry-picking across environments.
- **MR is the gate.** Merging an MR triggers the deploy. No manual "deploy to test" buttons.
- **Rollback is an MR.** A bad change is reverted via a `revert` MR, not by reaching into the env.
- **Never merge your own MR for prod.** Two reviewers required by branch protection.

## 1. Start of work — feature branch

```bash
git checkout dev
git pull --ff-only
git checkout -b feature/wave3-supplier-otd-fix
# … hack hack hack …
git push -u origin feature/wave3-supplier-otd-fix
```

Open an MR `feature/wave3-supplier-otd-fix → dev`.

CI runs automatically. The required check is the **`CI summary`** job. Iterate until green.

Get a reviewer ack from the right CODEOWNERS group (auto-suggested by GitHub).

**Merge.** GitHub fast-forwards `dev`; `cd-*.yml` workflows fire and deploy to **DEV**.

## 2. dev → test

After the change has cooked on DEV (functional smoke + DLT expectations green for at least one full daily cycle), promote to TEST:

```bash
git checkout test
git pull --ff-only
git checkout -b promote/dev-to-test-2026-05-08
git merge --ff-only origin/dev   # or `git reset --hard origin/dev` if test is behind
git push -u origin promote/dev-to-test-2026-05-08
```

Open an MR `promote/dev-to-test-2026-05-08 → test`.

Required reviewers: data-platform-lead **and** qa-team (CODEOWNERS enforces this for `qa/` paths; for non-QA paths qa-team should still be requested when promoting because they own the test environment posture).

The MR description must include:
- Range of commits being promoted (`git log origin/test..origin/dev --oneline`)
- Linear/Jira tickets covered
- A pointer to the most recent `qa/qa_pass_report.md` revision on `dev` (or a reason why a fresh QA cycle is or isn't needed)

CI runs again on this MR; the `CI summary` check must be green. The `cd-databricks.yml` and `cd-adf.yml` etc. on push to `test` will deploy to **TEST**.

If QA has not yet certified `dev`, do not open this MR. Run the QA cycle on DEV first.

### 2.1 Common foot-gun — test is behind dev for a long time

If many features have piled up on `dev` and `test` is far behind, promote in **slices**, not in one giant MR. Cut a `promote/...` branch for each logically isolated change set; merge each one separately. This keeps QA scope manageable.

## 3. test → prod (tagged release)

Only happens after:
- All Critical and High QA cases pass on TEST (see `qa/qa_pass_report.md`)
- For migration-wave cutovers: `audit.reconciliation_results.within_tolerance = true` for ≥ 7 consecutive days for the affected pipelines (≥ 14 days for SCD2 dimensions)
- Two CODEOWNERS reviewers available (data-platform-lead + security-team; add migration-pmo for wave cutovers)

```bash
git checkout prod
git pull --ff-only
git checkout -b promote/test-to-prod-v1.4.0
git merge --ff-only origin/test
git push -u origin promote/test-to-prod-v1.4.0
```

Open an MR `promote/test-to-prod-v1.4.0 → prod`.

Description must contain:
- Release tag intended (`v1.4.0`)
- Final QA pass report SHA / link
- Reconciliation status for any pipelines in the change set
- Rollback plan in one sentence

After merge, on `prod`:

```bash
git checkout prod
git pull --ff-only
git tag -s v1.4.0 -m 'Wave 3 — Manufacturing'
git push origin v1.4.0
```

`release.yml` fires on the tag:
1. Generates auto-changelog from conventional commits
2. Generates SBOM (CycloneDX)
3. Cuts a GitHub Release with both as assets
4. Dispatches `cd-infra.yml`, `cd-databricks.yml`, `cd-adf.yml`, `cd-synapse.yml` against the **PROD** environment
5. Each prod CD workflow gates on the GitHub Environment "prod" — 2 reviewers approve, 10-min wait timer, then apply

Total wall-clock from tag push to prod-deploy-complete is typically 25–40 min depending on what changed. The wait timer is intentional — it gives a reviewer time to abort if a problem surfaces between approval and apply.

## 4. Hotfix path

```
hotfix/<topic> ──MR──▶ prod                 (2 reviewers, fast-track)
                  │
                  └────MR (back-port)──▶ dev   (mandatory same-day)
```

A genuine prod hotfix bypasses TEST only when:
- A P1 incident is actively in flight, AND
- The change is < 50 lines, AND
- Migration PMO is paged before the MR is opened

The back-port MR to `dev` is **mandatory**. Don't allow `prod` and `dev` to diverge.

## 5. Rollback (a.k.a. "the change is hurting prod, get it out")

```bash
git checkout prod
git pull --ff-only
git revert --no-edit <bad-sha>
git push origin HEAD:rollback/v1.4.0-revert
```

Open MR `rollback/v1.4.0-revert → prod` with **`urgent`** label. Two reviewers, expedited. After merge, tag `v1.4.1` and let `release.yml` carry it through.

If the revert itself is risky (data migration involved), prefer a *forward fix* — MR with the corrective change, not a revert. The decision-maker for "revert vs forward fix" is the on-call data platform lead.

## 6. Visual cheat sheet

```
┌──────────────────────────────────────────────────────────────────┐
│  feature/<topic>                                                 │
│         │                                                         │
│         │  MR · CI green · 1 reviewer                            │
│         ▼                                                         │
│       dev ─────────────► DEV env  (auto on merge)                │
│         │                                                         │
│         │  MR · CI green · 1 reviewer + QA · slice if backlog    │
│         ▼                                                         │
│       test ────────────► TEST env (auto on merge)                │
│         │                                                         │
│         │  MR · 2 reviewers · QA pass report linked              │
│         │  · reconciliation green (migration waves)              │
│         ▼                                                         │
│       prod                                                        │
│         │                                                         │
│         │  signed tag v*.*.* triggers release.yml                │
│         ▼                                                         │
│       PROD env (2-reviewer environment gate + 10-min timer)      │
└──────────────────────────────────────────────────────────────────┘
```

## 7. Frequently asked

> **Do I need to open an MR to promote a doc-only change to prod?**
> Yes. The MR is the audit record AS9100 cares about — every change to the production estate has a reviewed approval trail.

> **What if `dev` and `test` diverge because someone hot-fixed test?**
> Don't hot-fix `test`. Hot-fix `prod` only (per §4) and back-port to `dev`. If `test` somehow ends up ahead of `dev`, open an MR `test → dev` to sync.

> **Can I auto-merge dependabot PRs?**
> Only into `dev`. They must go through the normal MR flow into `test` and `prod`.

> **What if the QA pass report fails on TEST?**
> Open an MR with the fix into `dev`, re-promote `dev → test` once green. Do not patch `test` directly.
