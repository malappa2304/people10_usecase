# TODO — what's next

Honest list of what I'd do with more time, in priority order. Not exhaustive — just what's actually next.

## If I had a few more days

1. **Cosmos DB online feature store IaC** — referenced in the design but not provisioned. ~1 day.
2. **Run the streaming notebook against real Event Hubs** — the code is right, but I haven't pushed real load through it. Need an Event Hubs namespace and a synthetic emitter. ~1.5 days.
3. **Apply the Synapse DDL end-to-end** — there's no Synapse pool in the take-home environment. ~half day given a pool.
4. **Networking module in Terraform** — VNet, subnets, Private Endpoints. ~½ day.

## Things I'm genuinely uncertain about

These I'd want to talk through with the team:

- Whether to **retire the imperative notebooks** entirely once DLT covers all the patterns, or keep both. The PoC keeps both deliberately to show pattern judgment, but in production the answer is probably "consolidate to DLT and keep PySpark only for the SAP edge cases".
- Whether **`apply_changes` in DLT** plays well with the explicit `PipelineRun` audit chassis or whether they should live on opposite sides of the codebase. I think the latter, but I haven't proven it.
- Whether **32 partitions on Event Hubs** is right at the cost we'd actually run at — the benchmark assumed peak load 24×7, real CNC machines are quieter at night.

## Rough edges I noticed but left

- The streaming notebook's `query.awaitTermination()` is commented out for local-dev convenience. In production it needs to be uncommented or the cluster job won't block correctly.
- The DLT pipeline reads `eh_bootstrap` from `spark.conf` — works fine when wired via `databricks.yml`, fails clearly with a missing-key error if someone runs the notebook standalone. Acceptable for a PoC; production would want a graceful fallback.

## Parked

- A real slide deck — would build from the design doc + architecture diagram on the day of the panel review. Low-leverage to invest in slides earlier.
- SHA-pinning every GitHub Action — supply-chain hardening that matters in production but isn't going to win me anything in a take-home review.
