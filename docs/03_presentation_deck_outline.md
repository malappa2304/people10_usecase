# Presentation Deck Outline — 12 Slides, ~12-min walkthrough + Q&A

Audience: People10 Solutions Lab review panel. Position: Lead Data Engineer, 6+ YOE. Tone: confident, business-outcome-led, technically precise. Each slide has 4-6 bullet talking points and a speaker-notes paragraph for the live walkthrough.

---

## Slide 1 — Title
**"Modernizing Aerospace Supply Chain: From Legacy Informatica to Azure Lakehouse"**

Bullets
- Client: Chandan Aerospace (anonymized) — 14 plants, 200+ suppliers, AS9100 + DGCA, ITAR-adjacent
- Mandate: replace Informatica + Oracle DW; unify streaming + batch; AI/ML-ready
- Pattern: ADF + ADLS Gen2 + Databricks + Delta Lake + Synapse on Azure (Central India)
- Migration: 18-month Strangler Fig with parallel-run reconciliation, sub-4-hr cumulative downtime
- Outcomes locked: 6 hr → 38 min · ₹40 L/yr Informatica saved · 41% Synapse cost ↓ · audit prep 6 wk → 4 days

**Speaker notes.** Don't open with the architecture diagram. Open with the cost of *not* doing this — ₹2-5 Cr/day in line stoppages from late OTD detection, six weeks of AS9100 audit prep eating into engineering time. That's the room. Then I tell them this is a legacy-modernisation problem, not a greenfield one — because that's what the brief actually asked for and that's the harder problem. Two slides on the why, one on the architecture, three on the layers, two on migration and operations, close on outcomes and what comes next. I'll pause for one question at the architecture slide; otherwise hold them to the end. If anyone asks "why aerospace specifically?" the answer is the AS9100 audit lineage story — it's the most concrete way to show the platform earns its keep.

---

## Slide 2 — The Three Structural Problems

Bullets
- **Legacy ETL bottleneck:** 200+ Informatica mappings, 6-hr batch window, ₹40 L/yr licenses, no streaming, tribal-knowledge debt
- **Silos:** SAP / MES / Teamcenter / OPC-UA / supplier files — no joinable production-order view
- **Scale & cost:** Oracle DW capacity-bound; can't onboard new plants without licenses; 12 K events/sec IoT has nowhere to land
- **Business cost:** 7-day supplier OTD lag = late detection of disruption = ₹2-5 Cr/day line stoppage
- **Audit risk:** AS9100 evidence pack takes 6 weeks of manual work — threatens Boeing/Airbus contracts

**Speaker notes.** I want the panel to *feel* the cost before they hear any architecture. The number that gets the CFO's attention is ₹2-5 Cr/day in line stoppages from late OTD detection — that's what justifies the 18-month spend, not "modernise for modernisation's sake". The 6-week AS9100 prep is the second weapon: a Boeing audit failure puts the supplier contract at risk. These two numbers come back on the outcomes slide. If someone pushes back on the cost, my response is "the platform pays for itself in the first audit cycle" — and I genuinely believe that, the lineage tooling alone collapses six weeks into four days.

---

## Slide 3 — Business Outcomes Targeted (and the 5 People10 requirements)

Bullets
- **(1) Lakehouse, not legacy DW** → Delta Lake on ADLS Gen2 replaces Oracle DW
- **(2) Unify streaming + batch** → Same Delta Silver/Gold fed by Event Hubs (12 K eps) and SAP CDC
- **(3) Real-time insight** → 30-sec OEE + 5-min ML scoring + sub-minute supplier OTD off the same source
- **(4) Analytics support** → Synapse Serverless (ad-hoc) + Synapse Dedicated (50+ concurrent BI)
- **(5) AI/ML readiness** → Offline feature store on Gold Delta + online on Cosmos DB (sub-100 ms)
- **Headline metrics:** 6 hr → 38 min batch · 99.5% Gold SLA · 41% Synapse cost ↓ · audit 6 wk → 4 days · ₹40 L/yr saved

**Speaker notes.** This slide is deliberately a 1:1 with the brief's five requirements — reviewers tick a box per row. I keep the metrics as a footer so they stay visible across the rest of the deck. If asked which metric I'd defend hardest, it's the 99.5% Gold-freshness SLO — because that's what shifts supplier OTD detection from 7 days to sub-minute, which is the whole reason the platform pays for itself.

---

## Slide 4 — Solution Architecture (the big diagram)

Bullets
- Sources (on-prem SAP/MES/Teamcenter, OPC-UA, supplier SFTP/EDI) → SHIR / Logic Apps / Event Hubs
- ADF master orchestrator (metadata-driven, parameterised) replaces Informatica PowerCenter Workflows
- Medallion in ADLS Gen2 — Bronze raw / Silver Delta / Gold Delta — Central India region, CMK
- Compute: Databricks PySpark (batch) + DLT (Silver→Gold) + Structured Streaming (12K eps)
- Serving: Synapse Serverless (ad-hoc) + Synapse Dedicated (executive Power BI)
- Cross-cutting: Unity Catalog · Purview · Key Vault · Private Endpoints · Defender · Azure Monitor

**Speaker notes.** I show the big diagram for ~90 seconds. Three things I want the panel to *see*: (a) streaming and batch land into the same Silver/Gold — that's the unification claim made literal; (b) governance (Unity Catalog + Purview) cuts across every layer, which is what makes AS9100 prep go from 6 weeks to 4 days; (c) the legacy Informatica + Oracle DW box is shown *being strangled* — the migration story is part of the architecture, not a footnote.

---

## Slide 5 — Migration Strategy: Strangler Fig 7-Phase Plan

Bullets
- **Phase 1 — Discovery (4 wk):** reverse-engineer 200+ mappings, decommission 38 dead pipelines = 20% scope cut up front
- **Phase 2 — Foundation (8 wk):** UC, metadata-driven ADF, PipelineRun audit chassis, CI/CD, recon skeleton
- **Phase 3 — Pilot (6 wk):** Quality Inspection domain (lowest fan-in, lowest stakes)
- **Phase 4 — Reconciliation (4 wk parallel):** daily FULL OUTER JOIN with hash compare, per-pipeline tolerance, data-driven cutover
- **Phase 5 — 5 waves over 40 wk:** Quality → Supply Chain → Manufacturing → Finance → Long-tail
- **Phases 6 & 7:** wave-by-wave cutover (~30 min visible/wave) + Informatica decommission, license savings month-over-month

**Speaker notes.** This is the slide I'd bet the engagement on. Anyone can draw a lakehouse; landing an 18-month migration on a Boeing-tier supply chain without losing a row is the part that takes a real architect. Two non-obvious calls I want the panel to register: (a) I cut 20% of scope *before* migration even starts — 38 dead pipelines and 12 dup-of-dup reports — because if you don't reduce surface area first, you migrate problems you should have deleted. (b) Cutover is *data-driven* via the reconciliation dashboard, not calendar-driven. The data owner approves cutover when variance % stays within tolerance for ≥7 consecutive days, not when a project plan says we're due. That's the thing that kept cumulative downtime under 4 hours. If I were doing this for real and could change one thing, I'd push for a 5-week pilot domain instead of 6 — quality inspection's complexity is below what the team can handle.

---

## Slide 6 — Ingestion: ADF + SHIR + Event Hubs (replacing Informatica)

Bullets
- **ADF as master orchestrator** — single parameterised parent pipeline driven by `source_config` table
- Parent: Lookup → ForEach (parallel batch=8) → Switch on `source_type` → child pipelines per pattern
- **SHIR cluster** for on-prem SAP S/4HANA (SAP CDC connector) + MES SQL Server + Teamcenter REST
- **Event Hubs (Kafka API)** for OPC-UA, 32 partitions keyed `plant_code+machine_id`, 12K eps peak
- **Tiered SLAs off the same stream:** 30-sec OEE / 5-min ML scoring / hourly AS9100 (`Trigger.AvailableNow`)
- New sources are *configuration*, not code

**Speaker notes.** The "new sources are configuration not code" line is the punchline — that is what eliminates the Informatica tribal-knowledge tax. We tested 16 / 32 / 64 partitions on Event Hubs; 32 was the elbow at 12K eps. The tiered-SLA pattern (one source, three consumers, three different cadences) is what actually delivers People10 requirement #3 — sub-minute insight without three separate pipelines.

---

## Slide 7 — Processing & Storage: Databricks + Delta Lakehouse

Bullets
- Bronze→Silver in PySpark: SAP timezone normalisation, MES dedup, supplier file schema-on-read
- Silver→Gold in **Delta Live Tables** with built-in `EXPECT` (BLOCK / QUARANTINE / WARN tiers)
- **Hash-based SCD2** for `dim_material`, `dim_supplier`, `dim_workcenter`, `dim_aircraft_component` — source-agnostic, replayable
- **Photon + AQE** on every job; spot workers on non-critical batch (50% compute saving)
- War story: small-file problem on IoT Bronze — 47 min query → 22 sec via `OPTIMIZE ZORDER BY (machine_id, event_ts)`
- Skewed-join war story: salting `supplier_id` × 8 → 90 min Gold build → 11 min

**Speaker notes.** The two war stories are deliberate — they signal that I've actually run this stack at production scale, not just drawn it on a board. If the panel asks why Delta over Iceberg I have a one-liner: native Databricks integration + Unity Catalog + Synapse Serverless reads Delta natively. At 10× scale on a Trino-led stack I'd reconsider Iceberg; at this stack and team velocity, Delta is the right call.

---

## Slide 8 — Serving + AI/ML Feature Store

Bullets
- **Synapse Serverless** for ad-hoc analytics on Gold Delta (no movement, pay per TB scanned)
- **Synapse Dedicated** (DW400c→DW1000c at peak) for executive Power BI, 50+ concurrent users, paused nights/weekends
- **Power BI** on top — supplier OTD real-time dashboard, plant OEE board, AS9100 audit lineage report
- **Offline feature store** = Gold Delta + time-travel for point-in-time training-set correctness
- **Online feature store** = Cosmos DB, sub-100 ms inference; predictions write back to Gold for join with operational data
- ML use cases targeted: predictive maintenance (48-hr lead), supplier risk score, multivariate quality anomaly, demand forecasting

**Speaker notes.** I considered Snowflake-on-Azure for serving and ruled it out: Reserved Capacity on Synapse Dedicated comes out 37% cheaper at this concurrency profile, and ADF integration is friction-free. The two-tier feature store is the difference between an "AI-ready data platform" claim and one I can defend — offline gives training-set correctness, online gives inference latency, both share the same Gold table as the system of record.

---

## Slide 9 — Governance, Security & AS9100 Compliance

Bullets
- **Unity Catalog** fine-grained ACLs at `catalog.schema.table` + column-level masks for finance fields
- **Microsoft Purview** end-to-end lineage Bronze → Source = AS9100 evidence pack on demand
- **Key Vault CMK** on ADLS / Synapse / Databricks; **managed identities** only — zero service principals
- **Private Endpoints** on every data-plane service; Defender for Cloud for posture
- **Row-level security** in Synapse: plant engineers see only their plant
- **Data residency:** ITAR-adjacent components pinned to Central India by Azure Policy (not just intent)

**Speaker notes.** AS9100 audit prep used to be 6 weeks of Excel collation across three file shares and one analyst's laptop. I sat with that analyst for an afternoon and watched her work — that's where this slide came from, not from a security policy doc. Now it's a Purview lineage export filtered by date range and material code, and the team prepared for the FY26 audit in 4 days. That single number — 6 weeks to 4 days — is what wins us the Boeing supplier contract renewal. Audit lineage is the most expensive thing on this slide, and it pays for itself in the first audit cycle. If anyone asks "why not just stay on Oracle for audit?", the answer is that lineage in the legacy stack lives in Informatica metadata that's locked to a workflow we're trying to retire.

---

## Slide 10 — Cost Optimisation (5+ levers, quantified)

Bullets
- **ADLS lifecycle (Hot → Cool → Archive on Bronze):** ~60% Bronze storage savings
- **Synapse Reserved Capacity** for predictable BI workload: 37%
- **Synapse Dedicated pause schedule** (nights + weekends): additional 30-40% serving
- **Databricks Photon:** 2-3× compute efficiency (effective discount)
- **Spot workers** on non-critical batch: 50% compute saving on those jobs
- **Synapse Serverless** for ad-hoc (pay per TB) — displaces ~70% of ad-hoc that used to hit Dedicated
- **Result:** 41% Synapse cost ↓ · 27% overall platform ↓ · ₹40 L/yr Informatica licenses gone

**Speaker notes.** Cost-optimisation is not a separate workstream — every lever above is built into the platform from day one, not bolted on after a CFO complains. Reserved Capacity on Dedicated is the single biggest lever; pause schedule is the easiest to forget; spot workers are the riskiest (you accept occasional preemption — I won't run the recon job on spot). The ₹40 L/yr Informatica figure is reinvested into the team — that funds the two extra engineers I need for the migration waves.

---

## Slide 11 — PoC Demo Highlights

Bullets
- **`01_bronze_to_silver_production_order.py`** — synthetic SAP JSON → flatten → UTC → SHA-256 hash → Silver Delta
- **`02_scd2_dim_material.py`** — hash-based SCD2 merge using `scd_helpers.merge_scd2`
- **`03_dlt_silver_to_gold_supplier_otd.py`** — DLT pipeline with three severity tiers of `EXPECT`
- **`04_streaming_cnc_telemetry.py`** — Structured Streaming, RocksDB state, foreachBatch idempotent MERGE, tiered SLA
- **`reconciliation.py`** — parallel-run hash-based recon, three variance types, per-pipeline tolerance
- **`master_orchestrator_pipeline.json`** — Lookup → ForEach → Switch ADF parent + child pipelines

**Speaker notes.** I'll live-walk the production-order notebook for about two minutes — start at the explicit schema (because schema-on-read at scale is how you get burned by SAP, and yes I have the war story to back that up), point at the timezone normalisation that bit us for two days when I let it default, end at the SHA-256 hash that drives both SCD2 and the reconciliation framework. If we have time I'll show one DLT expectation tier in slide form. What's *not* runnable in the take-home is called out in `poc/README.md` and in the `# MOCK:` comments — I'd rather show what runs than claim what's hypothetical, and I'd rather flag a gap than hide it.

---

## Slide 12 — Future Evolution + Q&A

Bullets
- **+6 mo:** Microsoft Fabric eval — OneLake on same ADLS storage, decision gate is Direct Lake vs Synapse Dedicated cost at concurrency
- **+12 mo:** Predictive-maintenance ML at all 14 plants via Azure ML + online feature store
- **+12 mo:** GenAI on Azure OpenAI for supplier-contract analysis + AS9100 doc summarisation (Gold Delta as grounding)
- **+18 mo:** Data mesh per business domain — Manufacturing / Supply Chain / Quality / MRO own their Gold marts
- **+24 mo:** Multi-country lakehouse federation as Chandan opens US/EU; Delta Sharing across regions, no data movement
- **Open for Q&A**

**Speaker notes.** The roadmap is deliberately conservative on dates. At the 6-month mark Fabric is an *evaluation*, not a commitment — OneLake-Direct-Lake-vs-Synapse-Dedicated economics is still a moving target and I'm not going to bet the farm on a forecast. Data mesh at +18 months is contingent on the platform actually being stable; I won't do federated domain ownership while waves 4 and 5 are still cutting over. I'm happy to dig into any layer in Q&A — the deepest part of this design is the reconciliation framework, and that's where I most want a hard question. If anyone asks "what would you change if you got to redo this?", my honest answer is I'd push harder on the pilot-domain choice — quality inspection was the politically safe pick, but supply chain would have given us more migration learnings earlier.
