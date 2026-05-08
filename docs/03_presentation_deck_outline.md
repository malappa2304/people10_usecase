# Presentation outline — 10 minutes + Q&A

A concise speaking outline for the panel review. Eight slides, two minutes per slide on average, ending with Q&A.

---

## Slide 1 — Title and framing
**Cloud-Native Data Platform on Azure — People10 Technologies**

- 3-day brief: design + working prototype on one cloud
- Cloud chosen: **Azure** (ADLS Gen2 · Databricks · Delta Lake · Synapse)
- Use case domain: manufacturing supply chain (chosen because it produces realistic streaming + batch data flows)

*Speaker notes:* Be upfront — this is a take-home in 3 days, the manufacturing context is something I picked for realism, not a real engagement.

## Slide 2 — The problem the brief asks us to solve

- Modern data platforms must **unify streaming + batch**
- Enable **real-time insights**
- Support **analytics**
- Prepare data for **AI/ML**
- Replace **legacy ETL + siloed systems**

## Slide 3 — Architecture (the diagram)

Show `docs/01_architecture_diagram.md`. Three things to point at:

1. Streaming and batch arrows both terminate at the **same Bronze** — that's the unification claim made literal in the storage layer.
2. **Databricks medallion on Delta Lake** in the centre — Bronze → Silver → Gold.
3. **Three consumption boxes** on the right — real-time, analytics, AI/ML — one per ask in the brief.

## Slide 4 — Why Delta Lake makes the medallion work

- Concurrent streaming + batch writes on the same table (ACID)
- Time travel for replay and audit
- `MERGE` and `apply_changes` for idempotent SCD2
- Open format — Synapse Serverless reads Delta natively

If asked Delta vs Iceberg: native Databricks + UC + Synapse. At 10× scale on a Trino-led stack I'd reconsider.

## Slide 5 — The PoC: one DLT pipeline, both arrows

Open `poc/databricks/pipelines/unified_medallion_dlt.py` and walk:

- `bronze_cnc_telemetry` — streaming Kafka source, `@dlt.table`
- `bronze_sap_production_order` — batch Auto Loader source, **same `@dlt.table` decorator**
- Three expectation tiers inline: `expect_or_fail` / `expect_or_drop` / `expect`
- SCD2 via `apply_changes`
- Gold materialised view joins streaming-derived rollups with batch-derived dimensions

This single file is the answer to the brief's core question.

## Slide 6 — Two-pattern processing (and why)

- **Declarative DLT** for unified streaming + batch flows
- **Imperative PySpark** with the `PipelineRun` audit chassis for the SAP edge cases

Decision rule: *can this be expressed as `@dlt.table` + `expect`s + `apply_changes`?* If yes, write DLT. If no, write a notebook.

This is a deliberate choice for the PoC — shows pattern judgment, not just one default. In production I'd probably consolidate to DLT once the team has internalised the framework.

## Slide 7 — Production readiness

- **Lineage** — Unity Catalog + Purview for AS9100-style audit trails
- **Security** — managed identities, CMK from Key Vault, Private Endpoints, RLS in Synapse
- **CI/CD** — GitHub Actions with ruff + pytest (coverage gate ≥80%) + terraform validate + checkov + gitleaks
- **Cost levers** — ADLS lifecycle, Synapse pause schedule, Photon, spot workers, Serverless for ad-hoc

## Slide 8 — Trade-offs and what I'd do next

Open the design-doc decision table and `TODO.md`. Three points:

1. The dual DLT + imperative pattern is a *deliberate* choice; I'd consolidate to DLT in production once the team is comfortable.
2. Honest gaps — Cosmos online feature store, full networking, real Synapse end-to-end, Purview scan config. Listed in `TODO.md`.
3. Things I'm uncertain about and would discuss with the team — also in `TODO.md`.

## Q&A

I'd most welcome a question on **why I kept both DLT and imperative notebooks** — that's the part I'm most curious to get a second opinion on.
