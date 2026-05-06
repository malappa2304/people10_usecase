-- =============================================================================
-- fact_production_order — Synapse Dedicated SQL pool
-- =============================================================================
-- Distribution: HASH on production_order_id — most queries filter or join on it.
-- Index:        Clustered Columnstore, the default for dedicated DW fact tables.
-- Partitioning: monthly on posting_ts_utc — aligns with the AS9100 audit window.
-- =============================================================================

IF OBJECT_ID('dbo.fact_production_order', 'U') IS NOT NULL
    DROP TABLE dbo.fact_production_order;
GO

CREATE TABLE dbo.fact_production_order
(
    production_order_id     VARCHAR(40)   NOT NULL,
    plant_code              VARCHAR(10)   NOT NULL,
    material_id             VARCHAR(40)   NOT NULL,
    customer_id             VARCHAR(40)   NULL,
    quantity                DECIMAL(18,3) NULL,
    uom                     VARCHAR(8)    NULL,
    posting_ts_utc          DATETIME2(0)  NOT NULL,
    started_ts_utc          DATETIME2(0)  NULL,
    completed_ts_utc        DATETIME2(0)  NULL,
    cycle_time_seconds      BIGINT        NULL,
    status                  VARCHAR(16)   NOT NULL,
    item_count              INT           NULL,
    row_hash                CHAR(64)      NOT NULL,
    silver_loaded_at_utc    DATETIME2(0)  NOT NULL,
    synapse_loaded_at_utc   DATETIME2(0)  NOT NULL DEFAULT SYSUTCDATETIME()
)
WITH
(
    DISTRIBUTION = HASH(production_order_id),
    CLUSTERED COLUMNSTORE INDEX,
    PARTITION
    (
        posting_ts_utc RANGE RIGHT FOR VALUES
        ('2024-01-01', '2024-04-01', '2024-07-01', '2024-10-01',
         '2025-01-01', '2025-04-01', '2025-07-01', '2025-10-01',
         '2026-01-01')
    )
);
GO

-- Stats — the columnstore stats are auto, but plant/customer/material drive most filters.
CREATE STATISTICS stats_fact_po_plant   ON dbo.fact_production_order(plant_code);
CREATE STATISTICS stats_fact_po_mat     ON dbo.fact_production_order(material_id);
CREATE STATISTICS stats_fact_po_cust    ON dbo.fact_production_order(customer_id);
CREATE STATISTICS stats_fact_po_status  ON dbo.fact_production_order(status);
GO
