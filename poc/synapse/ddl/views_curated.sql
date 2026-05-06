-- =============================================================================
-- Curated views — semantic layer over the fact + dim tables.
-- These are what Power BI binds to. Keeping the BI layer view-driven means we
-- can refactor underlying physical models without breaking any report.
-- =============================================================================

IF OBJECT_ID('curated.v_supplier_otd_current', 'V') IS NOT NULL
    DROP VIEW curated.v_supplier_otd_current;
GO

CREATE VIEW curated.v_supplier_otd_current
AS
SELECT
    f.supplier_id,
    s.supplier_name,
    s.supplier_country,
    f.plant_code,
    p.plant_name,
    f.material_id,
    m.material_description,
    f.purchase_order_id,
    f.expected_date_utc,
    f.actual_delivery_ts_utc,
    f.delivery_qty,
    f.required_qty,
    f.otd_status,
    f.delay_seconds
FROM dbo.fact_supplier_otd          f
JOIN dbo.dim_supplier               s ON s.supplier_id = f.supplier_id AND s.is_current = 1
LEFT JOIN dbo.dim_plant             p ON p.plant_code  = f.plant_code
LEFT JOIN dbo.dim_material          m ON m.material_id = f.material_id AND m.is_current = 1;
GO


-- Materialised aggregate refreshed by the post-load stored procedure.
IF OBJECT_ID('curated.mv_supplier_otd_daily', 'U') IS NOT NULL
    DROP TABLE curated.mv_supplier_otd_daily;
GO

CREATE TABLE curated.mv_supplier_otd_daily
(
    supplier_id        VARCHAR(40) NOT NULL,
    plant_code         VARCHAR(10) NOT NULL,
    expected_date      DATE        NOT NULL,
    total_orders       BIGINT      NOT NULL,
    on_time_orders     BIGINT      NOT NULL,
    otd_pct            DECIMAL(5,2) NOT NULL,
    avg_delay_seconds  BIGINT      NULL,
    refreshed_at_utc   DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
)
WITH ( DISTRIBUTION = HASH(supplier_id), CLUSTERED COLUMNSTORE INDEX );
GO

-- Stored procedure called by the ADF post-load step.
IF OBJECT_ID('dbo.usp_refresh_supplier_otd_view', 'P') IS NOT NULL
    DROP PROCEDURE dbo.usp_refresh_supplier_otd_view;
GO

CREATE PROCEDURE dbo.usp_refresh_supplier_otd_view
AS
BEGIN
    SET NOCOUNT ON;

    TRUNCATE TABLE curated.mv_supplier_otd_daily;

    INSERT INTO curated.mv_supplier_otd_daily
        (supplier_id, plant_code, expected_date, total_orders, on_time_orders,
         otd_pct, avg_delay_seconds)
    SELECT
        supplier_id,
        plant_code,
        CAST(expected_date_utc AS DATE),
        COUNT(*),
        SUM(CASE WHEN otd_status = 'ON_TIME' THEN 1 ELSE 0 END),
        CAST(100.0 * SUM(CASE WHEN otd_status = 'ON_TIME' THEN 1 ELSE 0 END)
             / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)),
        AVG(delay_seconds)
    FROM dbo.fact_supplier_otd
    WHERE otd_status IN ('ON_TIME', 'LATE')
    GROUP BY supplier_id, plant_code, CAST(expected_date_utc AS DATE);
END;
GO
