# Demo walkthrough — 15-min live review script

What I'd actually type at the keyboard during the live demo. Not a polished script — the kind of cheat-sheet you keep open in a second monitor.

---

## Pre-flight checklist (do these 30 min before the call)

- [ ] `git pull --ff-only origin dev` — make sure I'm on the latest
- [ ] `az login --tenant chandan-tenant.onmicrosoft.com` (mock) — pre-warm
- [ ] Open these tabs, in this order:
  1. `docs/01_architecture_diagram.md` (the simple diagram — open Mermaid preview)
  2. `docs/02_design_document.md` — scrolled to §5 Migration Strategy
  3. `poc/databricks/notebooks/01_bronze_to_silver_production_order.py`
  4. `poc/databricks/pipelines/unified_medallion_dlt.py`
  5. `poc/databricks/lib/reconciliation.py`
  6. `qa/qa_pass_report.md` — scrolled to §1 executive summary
  7. The GitHub Actions tab for the repo (so they can see CI pass status)
- [ ] Close everything else. No Slack, no email, no other tabs.
- [ ] Water in reach. Phone on do-not-disturb but visible (not in pocket).
- [ ] Test screen-share: share the *application*, not the desktop. Avoids accidental notification leak.

## Minute 0 — 2 · Set the stakes (slide 2)

Don't open with the architecture. Open with the cost of *not* doing this.

> "Chandan loses ₹2-5 Cr per day every time a supplier disruption goes undetected for seven days. Their AS9100 audit prep eats six weeks of an analyst's time. Both of those numbers come from problems the current Informatica + Oracle stack literally can't solve. Today I'm going to show you what I'd build to fix that — and more importantly, how I'd migrate to it without losing a single production order along the way."

If they look engaged, move on. If someone interrupts here, lean in — they're the room.

## Minute 2 — 5 · Architecture (slide 4 + the diagram file)

Open `docs/01_architecture_diagram.md`. Three things to point at, in this order:

1. **The two source arrows ending at the same Bronze.** "Streaming and batch unified — one set of Silver and Gold tables serve everything downstream."
2. **The medallion: Bronze → Silver → Gold on Delta Lake.** "Delta is what makes this work. ACID concurrent writes for streaming + batch on the same table, time travel for replay and audit, MERGE for idempotent writes."
3. **The three consumption boxes on the right.** "Real-time, analytics, AI/ML — exactly the three things the brief asked for."

If they ask why not Iceberg: native Databricks integration + Unity Catalog + Synapse Serverless reads Delta directly. At 10× scale on a Trino-led stack I'd revisit. *Don't get pulled into a Delta-vs-Iceberg debate beyond this.*

## Minute 5 — 9 · Migration story (slide 5 + design doc §5)

This is where the engagement is won or lost. Open `docs/02_design_document.md` scrolled to §5.

Three things to land:

1. **20% scope cut before migration starts.** "I reverse-engineered the 200+ Informatica mappings in week 4 of phase 1. Found 38 dead and 12 duplicate-of-duplicate. Cut them before the migration. That alone saved roughly 4 months over the 18-month plan."
2. **Reconciliation is the cutover gate.** Open `poc/databricks/lib/reconciliation.py`. "Three variance types — missing-in-new, missing-in-legacy, value-mismatch. Per-pipeline tolerance from the data owner, not engineering. Cutover requires within-tolerance for ≥7 consecutive days. So cutover is *data-driven*, not calendar-driven."
3. **Sub-4-hour cumulative downtime over 18 months.** "Wave-by-wave cutover at the *report* boundary, not the *table* boundary. Reporting endpoints flip; underlying pipelines don't pause."

If asked "what could go wrong with this approach?" — be honest. The biggest risk is the data owner setting tolerance too loosely and shipping bad parity. That's why every tolerance has to be defended in writing in `config/reconciliation_tolerance.yaml`.

## Minute 9 — 11 · Hands-on (slide 11 + the notebook)

Open `poc/databricks/notebooks/01_bronze_to_silver_production_order.py`. Ninety-second walk:

- Top: explicit `SAP_SCHEMA`. "Schema-on-read at scale is how you get burned by SAP. I learned this the hard way." (the timezone war story is in the design doc; reference it but don't tell the full story unless asked)
- Middle: `to_utc_timestamp(F.col("posting_ts_local"), F.col("plant_timezone"))`. "Plant-local timestamps with the timezone column carried through — fixes a bug where the same `posting_date` showed up as IST or UTC depending on which SAP instance, and our material ledger reconciliation was off by 5h30m for two days."
- Bottom: SHA-256 row hash. "This is what drives both SCD2 and the reconciliation framework. Same primitive, two consumers."

Then briefly switch to `poc/databricks/pipelines/unified_medallion_dlt.py`:

- Point at `bronze_cnc_telemetry` (streaming Kafka source) **and** `bronze_sap_production_order` (batch Auto Loader source) — *both* using `@dlt.table`. "Same decorator. Streaming and batch are the same thing in DLT — that's the unification claim made literal."

## Minute 11 — 13 · Production readiness (CI/CD + QA)

Switch to the GitHub Actions tab. Show that CI is green.

Open `qa/qa_pass_report.md`. Read out the §1 summary: 88/94 passed, zero Critical/High failures, APPROVE recommendation.

Then say one honest thing — point at the caveat in §2 of the report: "The streaming-throughput test was extrapolated from a 1-hour run, not the full 4-hour target. I'm calling that out because in a real engagement I'd re-run it on a higher-tier cluster before shipping. I want you to see what's a measured number and what's an honest extrapolation."

This is the moment you signal that you don't smooth over rough edges. Reviewers love this.

## Minute 13 — 15 · Q&A bait

Close with one sentence:

> "The deepest part of this design is the per-pipeline reconciliation tolerance gate. That's where I most want a hard question."

Then stop talking.

## Likely questions and one-line answers

| Q | A |
| -- | -- |
| Why Delta over Iceberg? | Native Databricks, Unity Catalog, Synapse Serverless reads it directly. At 10× scale on Trino I'd reconsider. |
| Why ADF, not Airflow? | SAP CDC connector is first-class on ADF, SHIR for on-prem SAP. Airflow we'd self-host; team velocity wins. |
| Why Synapse Dedicated, not Snowflake? | Reserved Capacity is 37% cheaper at this concurrency profile and ADF integration is friction-free. |
| Why both DLT and imperative notebooks? | Use DLT for unified streaming+batch flows; use imperative for the SAP edge cases that need full PySpark and the audit chassis. Decision rule in design doc §6.2. |
| Why Strangler Fig, not big-bang? | Aerospace tolerates zero data loss. Parallel-run reconciliation is the only way to *prove* parity before retiring the legacy. |
| What would you do differently? | Pilot on supply chain instead of quality inspection. Quality is the safe choice; supply chain is the useful one. |
| What's mocked vs production-ready? | Cosmos DB online feature store, full Synapse end-to-end run, and Purview scan configuration. Listed in `poc/README.md` and `TODO.md`. |
| What if tolerance is set too loose? | Data owner has to defend each tolerance in writing in `config/reconciliation_tolerance.yaml`. It's the procedural, not technical, control. |
| How would this scale to US/EU? | Multi-region UC metastore + Delta Sharing across regions, no data movement across borders. In the 24-month roadmap. |

## Things to NOT do during the demo

- Don't show the full design doc top-to-bottom. They've read it.
- Don't read the locked metrics aloud. They saw them on the slides.
- Don't apologise for what's mocked. Just call it out and move on.
- Don't volunteer war stories unless asked. They sound rehearsed when offered.
- Don't get pulled into a "you should have used X instead" rabbit hole. Acknowledge briefly, return to the main thread.

## If something breaks during the demo

- **Notebook won't open / DLT pipeline view broken** — switch to the rendered file on GitHub. The link is in the architecture diagram doc.
- **GitHub goes down (it does)** — pull up the local checkout and walk through the file in VS Code.
- **You forget the answer to a question** — "Honest answer: I don't know off the top of my head, let me check after the call." Better than guessing.

---

Last thing: breathe. The work is good. They've already read the doc. The demo is the conversation, not the content.
