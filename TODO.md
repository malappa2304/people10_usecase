# TODO — what's next on this PoC

A working list. Not exhaustive, not pretty — just what's actually next if I get a week 2 on this work, in roughly the order I'd tackle it. I keep this file because the failure mode of a 3-day take-home is pretending it's done; this keeps me honest.

---

## Top-of-mind (would do next if I had more time)

1. **Cosmos DB online feature store IaC** — `~1 day`
   The pattern is in design-doc §6.5 and the architecture diagram, but the actual Terraform module isn't there. Not technically hard; just time. Blocked by nothing, deferred because the migration story was a higher-leverage thing to land in the available days.

2. **Run the streaming notebook against real Event Hubs** — `~1.5 days`
   The code is correct (I've eyeballed it many times), but I haven't actually pushed 12K events/sec through a real Event Hubs namespace. Need the namespace stood up and a synthetic OPC-UA emitter. The 12.6K eps in the QA report is from a smaller test extrapolated against the per-partition throughput — see the note in `qa/qa_pass_report.md`. Honest reframing: I'm confident it scales, I haven't *proven* it scales.

3. **Predictive-maintenance ML scoring notebook** — `~1 day`
   Would round out the AI/ML story end-to-end. Reads from the Gold telemetry rollup, applies a vibration-pattern model, writes predictions back to a Gold table. Doesn't need a real model — I'd use a placeholder so the *plumbing* is the thing on display.

4. **Purview lineage scan configuration** — `~half day`
   AS9100 audit lineage is the headline outcome but the actual scan cadence (6-hourly) is documented, not configured in IaC. Would add a Bicep module.

## Plumbing I'd tighten

- **Per-action SHA pinning in workflows** — `step-security/harden-runner` + pin every `uses:` to a SHA, not a tag. Standard supply-chain hardening; I called it out in `docs/04_cicd_strategy.md` §7 but didn't do it.
- **Real Synapse end-to-end run** — DDL + the load workflow exist, but no Synapse pool was available in the take-home environment to run them end-to-end. The smoke-query results in the QA report are from sqlcmd against a dev pool I had access to, not the prod-shape one.
- **Pinned Python dep file** — currently the pytest deps are inline in `ci.yml`. A `requirements.dev.txt` or `pyproject.toml` would be cleaner.

## Parked (probably not worth it for this PoC)

- **Lakebase / Databricks-managed Postgres** for serving low-latency analytics. Interesting but premature for this use case.
- **Microsoft Fabric / OneLake migration evaluation** — already in the 6-month roadmap (design-doc §11). Not a take-home item.
- **A real slide deck** — `docs/03_presentation_deck_outline.md` is what I'd present from. Building actual slides is a low-leverage use of the next day.

## Things I'm genuinely uncertain about

These would be on my agenda for the first conversation with the team if I joined:

- Whether **32 partitions** on Event Hubs is right at the cost we'd actually run at. The 32 came from a benchmark, but the benchmark assumed peak load 24×7. In reality CNC machines are quieter at night; 24 might be cheaper.
- Whether to **retire the imperative notebooks** entirely once DLT covers all the patterns. The PoC keeps both deliberately to show breadth, but in production the answer is probably "consolidate to DLT and keep PySpark only for the SAP edge cases".
- Whether **`apply_changes`** in DLT plays well with the `PipelineRun` audit chassis or whether they should live on opposite sides of the codebase. I think the latter, but I'd want to prove it.
- Whether the **0.5% reconciliation tolerance** is right for the production-order pipeline. It's a gut number; I'd want two weeks of legacy-only baseline data first.

## Bugs / rough edges I noticed but left

- The streaming notebook's `query.awaitTermination()` is commented out for the PoC's local-dev convenience. In production it has to be uncommented or the cluster job won't block correctly. Marked but not fixed.
- A few terraform variable descriptions still say "dev | uat | prod" in old comments — fixed in `main.tf` but might have missed a couple.
- The DLT pipeline references `eh_bootstrap` from `spark.conf` — works fine when wired via `databricks.yml`, but if someone runs the notebook standalone in a workspace they'll get a clear error rather than a graceful fallback. Acceptable for a PoC; production would want a fallback.

---

If you read this far, you're probably the kind of reviewer who'd actually open this file. Hi 👋. Ask me about item 4 in "uncertain about" — that's the one I most want a second opinion on.
