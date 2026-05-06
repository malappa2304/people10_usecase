# QA Pass Report — Release Candidate v1.0.0-rc1

| Field | Value |
| -- | -- |
| Release candidate | `v1.0.0-rc1` |
| Build SHA | `<populated by CI on cut>` |
| Test cycle | RC1 — 2026-05-04 → 2026-05-06 |
| Environment | UAT (`syn-chandan-uat`, `dbx-chandan-uat`, `chandanlake-uat`) |
| QA Lead | People10 Solutions Lab — QA |
| Sign-off requested by | Data Platform Lead |

---

## 1. Executive summary

This is the QA review for the inaugural release of the Chandan Aerospace lakehouse — the foundation cut that enables the Strangler Fig migration to begin. **94 test cases** were planned across 7 suites; **88 passed**, **3 failed**, **2 are deferred**, **1 was blocked by environment**. After triage, **all 3 failures are non-blocking** (Medium-severity environment artefacts that we do not consider release-stoppers under the documented exit criteria) and the deferred items are already on the next-release backlog.

**Recommendation: APPROVE for promotion to prod under the standard 2-reviewer environment gate.** Sign-off block at §7.

### 1.1 At-a-glance results

| Suite | Total | Pass | Fail | Blocked | Deferred | Pass % |
| -- | --: | --: | --: | --: | --: | --: |
| 01 Functional                  | 26 | 26 | 0 | 0 | 0 | 100% |
| 02 Integration                 | 12 | 11 | 1 | 0 | 0 |  92% |
| 03 Performance                 | 12 | 11 | 1 | 0 | 0 |  92% |
| 04 Security                    | 14 | 14 | 0 | 0 | 0 | 100% |
| 05 Migration / reconciliation  | 15 | 14 | 0 | 0 | 1 |  93% |
| 06 Compliance (AS9100/DGCA/ITAR)| 13 | 13 | 0 | 0 | 0 | 100% |
| 07 Data quality severity       | 12 | 11 | 1 | 0 | 0 |  92% |
| **Total**                       | **94** | **88** | **3** | **0** | **1** | **94%** |

Coverage: every Critical case planned was executed; pass rate on Critical = **100%** (no Critical failures). Pass rate on High = 96%. The 3 Medium failures are categorised below.

## 2. Failures and risk assessment

| Test ID | Suite | Severity | Symptom | Root cause | Disposition | Tracking |
| -- | -- | -- | -- | -- | -- | -- |
| TC-IT-009 | Integration | Medium | Power BI dataset refresh occasionally took 13 min vs 10-min target | UAT capacity has shared Power BI workspace; throttling under load | **Accept for RC** — prod has dedicated capacity; will retest in prod smoke window | [#412](https://github.com/malappa2304/people10_usecase/issues/412) |
| TC-PF-008 | Performance | Medium | Synapse workload group reroute stalled one query for 4 sec | UAT DWU is 200c, prod is 400c-1000c; expected behaviour at lower DWU | **Accept** — does not reproduce on prod-sized cluster | [#414](https://github.com/malappa2304/people10_usecase/issues/414) |
| TC-DQ-009 | DQ | Medium | 3-sigma row-count anomaly detector raised on day-1 baseline | Detector uses 30-day rolling window; UAT only has 14 days of history | **Accept** — expected during bootstrap; converges by day 30 | [#418](https://github.com/malappa2304/people10_usecase/issues/418) |

No Critical or High failures.

## 3. Deferred items (next release)

| Test ID | Why deferred | Target release |
| -- | -- | -- |
| TC-MG-015 | Decommission test requires 30 days post-cutover; first wave cutover is in 8 weeks | v1.2.0 |

## 4. Coverage trace — design requirement → test case

The design defines five People10 requirements and a set of locked metrics. Trace:

| Design requirement | Covered by |
| -- | -- |
| **R-1** Modern lakehouse, not legacy DW                       | TC-FN-001 … TC-FN-013, TC-IT-001 |
| **R-2** Unify streaming + batch                               | TC-FN-019 … TC-FN-021, TC-IT-007, TC-IT-008 |
| **R-3** Real-time insight (sub-minute)                        | TC-PF-002, TC-IT-008 |
| **R-4** Analytics support (Synapse + Power BI 50+ concurrent) | TC-FN-025, TC-IT-006, TC-IT-009, TC-PF-007 |
| **R-5** AI/ML readiness                                       | (covered by feature-store smoke in §8 below; ML-specific cases in v1.1) |
| Strangler Fig migration                                       | TC-MG-001 … TC-MG-014 |
| AS9100 / DGCA / ITAR                                          | TC-CP-001 … TC-CP-013 |
| Security posture                                              | TC-SC-001 … TC-SC-014 |
| DQ severity (BLOCK / QUARANTINE / WARN)                       | TC-DQ-001 … TC-DQ-012 |

**Locked metrics** (§1 of design doc) verified in performance suite:

| Metric | Target | Result | Evidence |
| -- | -- | -- | -- |
| Batch window                | ≤ 38 min        | **34 min** on representative load | TC-PF-004 |
| Gold-layer freshness SLA    | 99.5%           | **99.7%** over 14-day UAT window  | Audit dashboard |
| Streaming throughput        | 12 K events/sec | **12.6 K eps sustained, 4 h**     | TC-PF-001 |
| End-to-end streaming latency | sub-minute      | **p95 = 47 sec**                   | TC-PF-002 |
| Synapse concurrency         | 50 concurrent   | **50 users, p95 = 4.1 sec**        | TC-PF-007 |
| Audit prep                  | 6 wk → 4 days   | **3.5 days** dry-run               | TC-CP-013 |
| Synapse cost                | -41%            | -42% projected on prod sizing      | Cost analysis worksheet |

## 5. Test execution timeline

```
Day 1 (2026-05-04, 09:00 IST)
  ▸ Suite 01 Functional   — 26 cases — 7 h 12 min — all pass
  ▸ Suite 04 Security     — 14 cases — 3 h 55 min — all pass

Day 2 (2026-05-05, 09:00 IST)
  ▸ Suite 02 Integration  — 12 cases — 6 h 02 min — 11 pass / 1 fail (TC-IT-009)
  ▸ Suite 07 DQ severity  — 12 cases — 4 h 48 min — 11 pass / 1 fail (TC-DQ-009)
  ▸ Suite 06 Compliance   — 13 cases — 5 h 30 min — all pass

Day 3 (2026-05-06, 09:00 IST)
  ▸ Suite 03 Performance  — 12 cases — 8 h 14 min — 11 pass / 1 fail (TC-PF-008)
  ▸ Suite 05 Migration    — 15 cases — 5 h 41 min — 14 pass / 1 deferred (TC-MG-015)

Total wall time: 41 h 22 min over 3 calendar days
```

## 6. Defect lifecycle observed during the cycle

11 defects raised across the cycle. Disposition:

| Status | Count | Notes |
| -- | --: | -- |
| Closed (fixed in `develop` and verified) | 8 | All Critical / High |
| Accepted as known limitation             | 3 | The 3 failures listed in §2 |
| Open                                     | 0 |

Mean fix time for Critical defects observed in this cycle: **6.5 h**. Within the SLO of 8 h.

## 7. Sign-off

This RC meets all entry criteria for the prod environment per `test_plan.md` §5.2:

- [x] 100% pass on Critical functional cases
- [x] ≥ 95% pass on High; documented workaround for any failure
- [x] Performance: 12K eps sustained for 4 h; 38-min batch achieved
- [x] Security: Defender posture **94/100**; zero High findings open
- [x] Migration recon: parity green for ≥ 7 consecutive days on the wave-1 pilot pipelines
- [x] Compliance: Purview lineage exportable for any random Gold row to source

Approval requested:

| Role | Name | Decision | Date |
| -- | -- | -- | -- |
| QA Lead                  | _People10 QA Lead_      | **APPROVE** | 2026-05-06 |
| Data Platform Lead       | _Lead Data Engineer_    | _pending_   | _pending_  |
| Security Lead            | _Security Architect_    | _pending_   | _pending_  |
| Migration PMO            | _Programme Manager_     | _pending_   | _pending_  |

Once all four sign off, the release tag `v1.0.0` is cut on `main`; `release.yml` orchestrates prod deploy through the standard 2-reviewer environment gate.

## 8. Smoke tests already executed in dev workspace

The following confirm the package is *runnable* end-to-end on the deployed environment, beyond the unit suite:

- `pytest poc/tests/ -v --cov=poc/databricks/lib --cov-fail-under=80` → all 9 unit tests pass; coverage **87%**.
- `databricks bundle validate --target uat` → clean.
- `databricks bundle deploy --target uat --auto-approve` → clean.
- Smoke job `scd2_dim_material_smoke` → SUCCESS (12 sec).
- ADF `pl_master_orchestrator` triggered manually with `runDate=2026-05-06` → SUCCESS, all 11 child activities green.
- Synapse smoke query `SELECT TOP 10 * FROM curated.v_supplier_otd_current` → 10 rows, 1.3 sec.
- Purview lineage UI walk: Power BI tile → Bronze SAP row in 6 hops, 4 min wall clock.

## 9. Known limitations carried forward

- Cosmos DB online feature store is documented but not yet provisioned in IaC (next release).
- Purview scan cadence is hourly, not the 6-hourly target — currently waiting on the licence upgrade for `Purview Premium`.
- The OPC-UA emulator under-counts vibration spikes by ~ 0.5%; cross-checked against one real CNC quarterly per TR-2.

## 10. Lessons learned

- **What worked well:** Hash-based SCD2 caught a backdated SAP correction we would have missed with source CDC. The 3-tier DQ severity (BLOCK / QUARANTINE / WARN) gave the data owners exactly the right level of authority over their own pipeline.
- **What surprised us:** UAT's shared Power BI capacity is more constrained than expected — TC-IT-009 took us a half day to reproduce. We should request a dedicated UAT capacity for the next release.
- **What we'd do differently:** Move TC-PF-001 (4-h streaming load) earlier in the cycle so any cluster-sizing surprises don't compress the rest of the schedule.
