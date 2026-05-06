-- =============================================================================
-- Top 10 suppliers by volume per plant, last 90 days.
-- DENSE_RANK + PARTITION BY plant; ties get the same rank, no gaps.
-- =============================================================================

WITH ranked AS (
    SELECT
        f.plant_code,
        p.plant_name,
        f.supplier_id,
        s.supplier_name,
        SUM(f.delivery_qty)                                              AS total_qty,
        COUNT(*)                                                          AS total_orders,
        DENSE_RANK() OVER (PARTITION BY f.plant_code ORDER BY SUM(f.delivery_qty) DESC) AS rnk
    FROM dbo.fact_supplier_otd       f
    JOIN dbo.dim_supplier            s ON s.supplier_id = f.supplier_id AND s.is_current = 1
    JOIN dbo.dim_plant               p ON p.plant_code  = f.plant_code
    WHERE f.expected_date_utc >= DATEADD(DAY, -90, SYSUTCDATETIME())
      AND f.otd_status IN ('ON_TIME', 'LATE')
    GROUP BY f.plant_code, p.plant_name, f.supplier_id, s.supplier_name
)
SELECT plant_code, plant_name, supplier_id, supplier_name,
       total_qty, total_orders, rnk
FROM ranked
WHERE rnk <= 10
ORDER BY plant_code, rnk;
