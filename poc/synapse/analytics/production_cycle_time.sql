-- =============================================================================
-- Production order cycle-time analysis.
-- Cycle time = completed - started, in seconds, materialised at Gold; we just
-- aggregate here. p50 / p95 / p99 give the operations team the distribution
-- shape the average alone hides.
-- =============================================================================

SELECT
    f.plant_code,
    p.plant_name,
    m.material_group,
    COUNT(*)                                                                AS orders,
    AVG(f.cycle_time_seconds / 60.0)                                        AS avg_cycle_minutes,
    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY f.cycle_time_seconds)
        OVER (PARTITION BY f.plant_code, m.material_group) / 60.0           AS p50_cycle_minutes,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY f.cycle_time_seconds)
        OVER (PARTITION BY f.plant_code, m.material_group) / 60.0           AS p95_cycle_minutes,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY f.cycle_time_seconds)
        OVER (PARTITION BY f.plant_code, m.material_group) / 60.0           AS p99_cycle_minutes
FROM dbo.fact_production_order   f
JOIN dbo.dim_material            m ON m.material_id = f.material_id AND m.is_current = 1
JOIN dbo.dim_plant               p ON p.plant_code  = f.plant_code
WHERE f.completed_ts_utc IS NOT NULL
  AND f.posting_ts_utc >= DATEADD(DAY, -30, SYSUTCDATETIME())
GROUP BY f.plant_code, p.plant_name, m.material_group, f.cycle_time_seconds
ORDER BY f.plant_code, m.material_group;
