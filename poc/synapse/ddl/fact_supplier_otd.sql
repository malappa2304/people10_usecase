-- =============================================================================
-- fact_supplier_otd
-- =============================================================================
-- Distribution: HASH on supplier_id — top-N supplier queries are the hot path
--   and supplier_id has reasonable cardinality. (We salted on the join side
--   where one supplier carries 40% of rows; see Databricks Gold build.)
-- Index:        Clustered Columnstore.
-- Partitioning: monthly on expected_date_utc.
-- =============================================================================

IF OBJECT_ID('dbo.fact_supplier_otd', 'U') IS NOT NULL
    DROP TABLE dbo.fact_supplier_otd;
GO

CREATE TABLE dbo.fact_supplier_otd
(
    supplier_id             VARCHAR(40)   NOT NULL,
    plant_code              VARCHAR(10)   NOT NULL,
    material_id             VARCHAR(40)   NOT NULL,
    purchase_order_id       VARCHAR(40)   NOT NULL,
    expected_date_utc       DATETIME2(0)  NOT NULL,
    actual_delivery_ts_utc  DATETIME2(0)  NULL,
    delivery_qty            DECIMAL(18,3) NULL,
    required_qty            DECIMAL(18,3) NULL,
    otd_status              VARCHAR(16)   NOT NULL,    -- ON_TIME | LATE | PENDING
    delay_seconds           BIGINT        NULL,
    silver_loaded_at_utc    DATETIME2(0)  NOT NULL,
    synapse_loaded_at_utc   DATETIME2(0)  NOT NULL DEFAULT SYSUTCDATETIME()
)
WITH
(
    DISTRIBUTION = HASH(supplier_id),
    CLUSTERED COLUMNSTORE INDEX,
    PARTITION
    (
        expected_date_utc RANGE RIGHT FOR VALUES
        ('2024-01-01', '2024-04-01', '2024-07-01', '2024-10-01',
         '2025-01-01', '2025-04-01', '2025-07-01', '2025-10-01',
         '2026-01-01')
    )
);
GO

CREATE STATISTICS stats_fact_otd_plant ON dbo.fact_supplier_otd(plant_code);
CREATE STATISTICS stats_fact_otd_status ON dbo.fact_supplier_otd(otd_status);
GO
