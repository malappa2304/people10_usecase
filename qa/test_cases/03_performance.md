# Performance Test Cases

Targets are the locked metrics in §1 of the design doc. Run pre-cutover and weekly on prod against synthetic load.

---

## TC-PF-001 · Streaming throughput — 12K events/sec sustained
**Severity:** Critical · **Target:** 12,000 events/sec for ≥ 4 hours, no driver restarts

- **Given** OPC-UA emitter producing 12,000 events/sec across 32 partitions, keyed by `plant_code+machine_id`
- **When** notebook 04 (streaming) runs with 30-sec trigger
- **Then** `bytesPerSecond`, `inputRowsPerSecond` ≥ target for ≥ 4 h continuously; no offsets-out-of-bounds warnings; processing time per micro-batch < 25 sec (< trigger interval).

## TC-PF-002 · Streaming end-to-end latency — sub-minute
**Severity:** Critical · **Target:** p95 latency from Event Hubs ingest to Silver visibility ≤ 60 sec

- **Given** synthetic events tagged with `produced_ts`
- **When** measured at Silver query time as `now() - produced_ts`
- **Then** p50 ≤ 35 sec, p95 ≤ 60 sec, p99 ≤ 90 sec.

## TC-PF-003 · Streaming watermark — 10-min recovery from input gap
**Severity:** High · **Target:** Stream resumes cleanly when Event Hubs has a 10-min producer outage

- **Given** stream is healthy
- **When** the OPC-UA emitter is paused for 10 min, then resumes
- **Then** the stream remains running; no late-event drops above the watermark; aggregations recover within 2 trigger intervals.

## TC-PF-004 · Batch window — 38-min target on 2.4 TB/day raw → 600 GB curated
**Severity:** Critical · **Target:** End-to-end batch (Bronze → Silver → Gold → Synapse) ≤ 38 min

- **Given** a synthetic 2.4 TB Bronze load representative of one day
- **When** the daily orchestrator runs
- **Then** total elapsed (ADF parent start to Synapse load complete) ≤ 38 min on the prod cluster sizing.

## TC-PF-005 · Skew handling — `supplier_id` salting reduces Gold build time
**Severity:** High · **Target:** Gold supplier OTD build < 15 min on skewed data

- **Given** a synthetic dataset where one supplier carries 40% of rows (war story replication)
- **When** the Gold build runs with `supplier_id` salting
- **Then** elapsed time ≤ 15 min; skew metric in Spark UI shows partitions roughly balanced (max/min ratio < 3).

## TC-PF-006 · Small-file remediation — `OPTIMIZE ZORDER` on IoT Bronze
**Severity:** High · **Target:** Query latency on Bronze CNC after OPTIMIZE ≤ 30 sec

- **Given** a Bronze table with > 100K small files
- **When** `OPTIMIZE bronze.cnc_telemetry ZORDER BY (machine_id, event_ts)` runs nightly
- **Then** the next-morning representative query (1-day window for one machine) completes in ≤ 30 sec (versus 47 min un-OPTIMIZED in the war-story baseline).

## TC-PF-007 · Synapse Dedicated — 50 concurrent BI users
**Severity:** Critical · **Target:** p95 query time ≤ 5 sec on the executive dashboard at 50 concurrency

- **Given** JMeter simulates 50 concurrent users running the supplier OTD trend, top-suppliers-by-plant, and quality defect-rate queries
- **When** Synapse Dedicated is at DW400c
- **Then** p95 query time ≤ 5 sec, p99 ≤ 15 sec; no "resource governor" rejections.

## TC-PF-008 · Synapse Dedicated scale-up under burst load
**Severity:** Medium · **Target:** Workload group reroutes long-running queries to a higher-DWU class without page error

- **Given** Synapse at DW400c; a query exceeds its workload-group memory grant
- **When** the burst hits
- **Then** the query is queued, not failed; SLA-tier query (executive) is not delayed.

## TC-PF-009 · Synapse Serverless — TB-scanned cost control
**Severity:** High · **Target:** A representative ad-hoc workload scans ≤ 50 GB per query against partitioned Gold Delta

- **Given** the supplier_otd_trend query running with a 90-day filter on `expected_date_utc`
- **When** the partition pruning is correct
- **Then** Serverless `Data Processed` per query ≤ 50 GB; same query without filter would scan ~ 2 TB (control case).

## TC-PF-010 · Cluster cost — spot worker preemption tolerated on non-critical batch
**Severity:** Medium · **Target:** Job tolerates ≥ 20% worker preemption with ≤ 15% wall-clock impact

- **Given** the Gold supplier OTD build is running on a cluster with 80% spot workers
- **When** Azure preempts 25% of workers mid-job
- **Then** the job completes successfully; total elapsed is ≤ 15% over the all-on-demand baseline.

## TC-PF-011 · Recon framework — completes within 90 min for the 5 wave-3 pipelines
**Severity:** High · **Target:** Daily recon for one full wave's pipelines completes by 03:30 UTC

- **Given** 5 pipelines in wave 3 (Manufacturing); each has ~ 20M rows / day
- **When** `reconcile()` runs sequentially
- **Then** total wall time ≤ 90 min; `audit.reconciliation_results` rows present for all 5 by 03:30 UTC.

## TC-PF-012 · Memory — RocksDB state store under 4-hour load
**Severity:** Critical · **Target:** Streaming driver heap stable below 80% for the full 4-hour load test

- **Given** TC-PF-001 environment
- **When** monitoring `JVM_HEAP_USED` over 4 h
- **Then** heap stays below 80% throughout; no GC pauses > 2 sec; no OOM kills.
