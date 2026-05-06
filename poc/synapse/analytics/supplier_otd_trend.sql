-- =============================================================================
-- Supplier OTD trend with QoQ delta — uses LAG() over a quarterly partition.
-- Drives the executive supplier-scorecard tile.
-- =============================================================================

WITH quarterly AS (
    SELECT
        supplier_id,
        DATEFROMPARTS(YEAR(expected_date_utc),
                      ((MONTH(expected_date_utc) - 1) / 3) * 3 + 1, 1) AS quarter_start,
        COUNT(*)                                                          AS total_orders,
        SUM(CASE WHEN otd_status = 'ON_TIME' THEN 1 ELSE 0 END)           AS on_time_orders
    FROM dbo.fact_supplier_otd
    WHERE otd_status IN ('ON_TIME', 'LATE')
      AND expected_date_utc >= DATEADD(QUARTER, -8, SYSUTCDATETIME())
    GROUP BY supplier_id,
             DATEFROMPARTS(YEAR(expected_date_utc),
                           ((MONTH(expected_date_utc) - 1) / 3) * 3 + 1, 1)
)
SELECT
    s.supplier_name,
    q.supplier_id,
    q.quarter_start,
    q.total_orders,
    q.on_time_orders,
    CAST(100.0 * q.on_time_orders / NULLIF(q.total_orders, 0) AS DECIMAL(5,2)) AS otd_pct,
    CAST(100.0 * q.on_time_orders / NULLIF(q.total_orders, 0)
       - LAG(100.0 * q.on_time_orders / NULLIF(q.total_orders, 0))
            OVER (PARTITION BY q.supplier_id ORDER BY q.quarter_start)
         AS DECIMAL(5,2))                                                     AS otd_pct_qoq_delta
FROM quarterly             q
JOIN dbo.dim_supplier      s ON s.supplier_id = q.supplier_id AND s.is_current = 1
ORDER BY q.supplier_id, q.quarter_start;
