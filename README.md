# People10 PoC — Cloud-Native Data Platform on Azure

A 3-day take-home for the People10 Solutions Lab brief. End-to-end design + working prototype on Azure (ADLS Gen2 · Databricks · Delta Lake · Synapse) showing how a modern lakehouse unifies streaming and batch, supports analytics, and prepares data for AI/ML.

— Malappa

---

## How to read this in 20 minutes

1. **[`docs/01_architecture_diagram.md`](docs/01_architecture_diagram.md)** — one diagram, 1 minute.
2. **[`docs/02_design_document.md`](docs/02_design_document.md)** — design covering the brief's 7 key areas, ~10 minutes.
3. **[`poc/databricks/pipelines/unified_medallion_dlt.py`](poc/databricks/pipelines/unified_medallion_dlt.py)** — the central demo, ~5 minutes. One DLT pipeline ingests **streaming** (Event Hubs) **and** **batch** (Auto Loader) into the same medallion. This is the unification claim made literal.
4. **[`TODO.md`](TODO.md)** — what I'd do next if I had more time, and what I'm uncertain about.

If you only have 5 minutes: read the diagram and the design-doc executive summary.

## What the brief asked for, and where it's covered

| Brief — Key Areas to Cover | Where in this repo |
| -- | -- |
| Batch & streaming ingestion | Design doc §3 · DLT pipeline `unified_medallion_dlt.py` · Streaming notebook `04_streaming_cnc_telemetry.py` |
| Data processing & transformation | Design doc §4 · 3 notebooks under `poc/databricks/notebooks/` · Reusable lib in `poc/databricks/lib/` |
| Storage architecture | Design doc §5 · Terraform `main.tf` · Synapse DDL under `poc/synapse/ddl/` |
| Cloud-native services & scalability | Design doc §6 |
| Data quality, governance & security | Design doc §7 · DLT expectations inline in the pipeline |
| CI/CD, monitoring & cost optimization | Design doc §8 · `.github/workflows/ci.yml` · `Makefile` |
| Trade-offs & future evolution | Design doc §9 + §10 |

## Repo layout

```
people10_usecase/
├── README.md                   # this file
├── TODO.md                     # what's next + things I'm uncertain about
├── Makefile                    # make test / lint / smoke / ci-local
├── databricks.yml              # Databricks Asset Bundle
├── .env.example                # local dev env-var template
├── docs/
│   ├── 01_architecture_diagram.md
│   ├── 02_design_document.md
│   └── 03_presentation_deck_outline.md
├── poc/
│   ├── README.md               # how to run locally
│   ├── databricks/
│   │   ├── pipelines/          # DLT — unified streaming + batch
│   │   ├── notebooks/          # imperative PySpark with audit chassis
│   │   └── lib/                # reusable: PipelineRun, SCD2, recon, readers
│   ├── synapse/                # DDL + analytics SQL samples
│   ├── infrastructure/terraform/   # one self-contained main.tf
│   ├── tests/                  # pytest + chispa unit tests
│   ├── sample_data/            # synthetic JSON / CSV
│   └── config/                 # source_config seed
└── .github/workflows/ci.yml    # PR validation
```

## Running it locally

```bash
make test         # pytest with coverage gate (≥80%)
make lint         # ruff + format check
make ci-local     # everything CI runs, locally
```

For Databricks: open the notebooks in Databricks Community Edition, upload the sample data to `dbfs:/FileStore/people10/`, run the notebooks in order. Detailed instructions in [`poc/README.md`](poc/README.md).

## Honest scope (what this is and isn't)

This is what 3 focused days produces. Some things are working code; some are designed-but-not-provisioned. Calling out the line:

**Working and runnable:**
- All 3 notebooks under `poc/databricks/notebooks/` run on Databricks Community Edition with the supplied sample data
- The DLT pipeline `unified_medallion_dlt.py` is wired into the Databricks Asset Bundle
- `pytest` suite passes with ≥80% coverage on the production library
- CI workflow runs lint + tests + Terraform validate

**Designed, not provisioned:**
- Synapse Dedicated pool — DDL is written, not run end-to-end (no Synapse pool in the take-home env)
- Cosmos DB online feature store — pattern is in design doc §6, IaC isn't there
- Microsoft Purview — referenced for lineage, scan config not wired
- Most Terraform modules — `main.tf` has the foundation; networking + Synapse + monitoring would each be ~50 lines I haven't written

The TODO list in `TODO.md` is the honest "what's next" — read it alongside this README.

## Things I'd like to talk about in the review

The most interesting question, in my opinion, is **why I kept *both* a DLT pipeline and imperative PySpark notebooks** when DLT can do most of what the notebooks do. The answer is in design doc §4. I'd genuinely like a second opinion on whether to retire the imperative notebooks in production, or keep both as a deliberate dual-pattern.
