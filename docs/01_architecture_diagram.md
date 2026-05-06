# Architecture Diagram — Chandan Aerospace Lakehouse on Azure

End-to-end view: sources on the left, medallion lakehouse in the centre, serving and AI/ML on the right, governance + security + observability cutting across. Legacy Informatica + Oracle DW are shown being **strangled** wave by wave (dashed boundary).

```mermaid
flowchart LR
    %% ============ SOURCES ============
    subgraph SRC["SOURCES (on-prem + cloud)"]
        direction TB
        SAP["SAP S/4HANA<br/>(ERP - on-prem)"]
        MES["Shop-floor MES<br/>(SQL Server - on-prem)"]
        TC["Siemens Teamcenter<br/>(PLM - on-prem)"]
        OPC["CNC machines<br/>OPC-UA<br/>12K events/sec"]
        SUP["Supplier portals<br/>SFTP / email / EDI"]
        QA["Lab QA<br/>Excel + LIMS"]
    end

    %% ============ LEGACY (BEING STRANGLED) ============
    subgraph LEGACY["LEGACY (strangled wave-by-wave, 18 months)"]
        direction TB
        INFA["Informatica PowerCenter<br/>200+ mappings"]
        ORA[("Oracle DW")]
        INFA --> ORA
    end

    %% ============ INGESTION ============
    subgraph INGEST["INGESTION LAYER"]
        direction TB
        SHIR["Self-Hosted IR<br/>(SHIR cluster, on-prem)"]
        ADF["Azure Data Factory<br/>master orchestrator<br/>(metadata-driven)"]
        EH["Azure Event Hubs<br/>Kafka API · 32 partitions<br/>plant_code+machine_id"]
        LA["Logic Apps<br/>(supplier email/SFTP)"]
    end

    %% ============ LAKEHOUSE ============
    subgraph LAKE["LAKEHOUSE — ADLS Gen2 (Central India, CMK, hierarchical NS)"]
        direction TB
        BR["BRONZE<br/>raw immutable<br/>Parquet/JSON<br/>partitioned by source/date<br/>7-yr retention"]
        SI["SILVER (Delta Lake)<br/>conformed, SCD2,<br/>ACID, time travel"]
        GO["GOLD (Delta Lake)<br/>fact_production_order<br/>fact_supplier_otd<br/>fact_quality_inspection<br/>fact_machine_telemetry"]
        BR --> SI --> GO
    end

    %% ============ COMPUTE ============
    subgraph COMPUTE["COMPUTE — Databricks (Unity Catalog)"]
        direction TB
        DBX_B["PySpark batch jobs<br/>Bronze→Silver"]
        DLT["Delta Live Tables<br/>Silver→Gold + expectations"]
        DBX_S["Structured Streaming<br/>RocksDB · 10-min watermark<br/>tiered SLAs (30s/5m/1h)"]
        DBX_ML["ML scoring jobs<br/>predictive maintenance"]
    end

    %% ============ SERVING ============
    subgraph SERVE["SERVING"]
        direction TB
        SYNS["Synapse Serverless<br/>(ad-hoc SQL on Delta)"]
        SYND["Synapse Dedicated<br/>(50+ concurrent · Power BI)"]
        PBI["Power BI<br/>executive dashboards<br/>+ supplier OTD real-time"]
        FS_OFF["Feature Store offline<br/>(Gold Delta + time travel)"]
        FS_ON["Feature Store online<br/>(Cosmos DB · sub-100ms)"]
        SYND --> PBI
        SYNS --> PBI
    end

    %% ============ GOVERNANCE / SECURITY / OBSERVABILITY ============
    subgraph GOV["GOVERNANCE & SECURITY (cross-cutting)"]
        direction TB
        UC["Unity Catalog<br/>fine-grained ACLs"]
        PUR["Microsoft Purview<br/>lineage · glossary · sensitivity"]
        KV["Azure Key Vault<br/>CMK · secrets"]
        PE["Private Endpoints<br/>(no public IPs)"]
        DEF["Defender for Cloud"]
    end

    subgraph OBS["OBSERVABILITY"]
        direction TB
        AM["Azure Monitor +<br/>Log Analytics"]
        AUD["Audit Delta table<br/>(pipeline_run, dq_results)"]
        ALERT["Action Groups →<br/>Teams / PagerDuty"]
        AM --> ALERT
        AUD --> ALERT
    end

    %% ============ EDGES ============
    SAP -->|SAP CDC| SHIR
    MES -->|JDBC + watermark| SHIR
    TC  -->|REST API| SHIR
    QA  -->|SFTP file| SHIR
    SUP -->|SFTP / EDI| LA
    OPC -->|MQTT/Kafka| EH

    SHIR --> ADF
    LA   --> ADF
    EH   --> DBX_S

    ADF -->|Copy + DBX activity| BR
    DBX_S -->|foreachBatch + MERGE| SI
    DBX_B --> SI
    DLT   --> GO
    DBX_ML --> GO

    GO -->|Copy/Polybase| SYND
    GO --> SYNS
    GO --> FS_OFF
    FS_OFF -->|materialise| FS_ON
    FS_ON --> DBX_ML

    %% legacy dual-run + strangle
    SAP -.->|legacy CDC<br/>parallel run| INFA
    MES -.-> INFA
    ORA -.->|reconciliation<br/>FULL OUTER JOIN<br/>hash compare| GO

    %% governance touches everything
    UC -.-> SI
    UC -.-> GO
    PUR -.-> BR
    PUR -.-> SI
    PUR -.-> GO
    KV -.-> LAKE
    PE -.-> LAKE
    PE -.-> COMPUTE
    PE -.-> SERVE
    DEF -.-> LAKE

    %% obs touches pipelines
    AM -.-> ADF
    AM -.-> COMPUTE
    AUD -.-> ADF
    AUD -.-> COMPUTE

    classDef legacy fill:#fde4e4,stroke:#c0392b,stroke-dasharray: 5 5,color:#333;
    classDef gold   fill:#fff3cd,stroke:#b8860b,color:#333;
    classDef secur  fill:#e8f0fe,stroke:#1a73e8,color:#333;
    class LEGACY,INFA,ORA legacy;
    class GO gold;
    class GOV,UC,PUR,KV,PE,DEF secur;
```

## Reading the diagram

- **Solid arrows** = production data path (steady state).
- **Dashed arrows** = transitional state — legacy systems still running in parallel during the 18-month Strangler Fig migration. Reconciliation arrow (Oracle DW ↔ Gold) is the *control gate* for each cutover.
- **Cross-cutting layers** (Governance, Security, Observability) are not in-line with the data path because every production component depends on them; in-line edges would obscure the read.
- Two ML edges matter: offline feature store reads Gold with time-travel for point-in-time training-set correctness; online store (Cosmos DB) is materialised for sub-100 ms inference and feeds back into Databricks ML scoring.
- Streaming and batch share the *same* Silver/Gold tables — that's the unification the brief asks for. There is no separate streaming warehouse.

## What the diagram deliberately *does not* show

- Branch-level ADF pipeline structure (parent + Lookup + ForEach + Switch) — covered in `02_design_document.md` §6 and `poc/adf/pipelines/master_orchestrator_pipeline.json`.
- Per-table SCD2 mechanics — covered in `poc/databricks/lib/scd_helpers.py`.
- DR topology (paired region) — covered in §9 of design doc with RTO/RPO.

The intent is one diagram a reviewer can hold in their head, not a 50-box BAU runbook.
