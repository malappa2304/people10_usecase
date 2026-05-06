-- =============================================================================
-- Cross-plant quality defect rate by material — drives the Quality dashboard
-- on the Power BI executive page. Defect rate = inspections_failed / total_inspections.
-- =============================================================================

WITH inspections AS (
    SELECT
        i.plant_code,
        i.material_id,
        COUNT(*)                                                          AS total_inspections,
        SUM(CASE WHEN i.inspection_result = 'FAIL' THEN 1 ELSE 0 END)     AS failed_inspections
    FROM dbo.fact_quality_inspection  i
    WHERE i.inspection_ts_utc >= DATEADD(DAY, -90, SYSUTCDATETIME())
    GROUP BY i.plant_code, i.material_id
)
SELECT
    p.plant_code,
    p.plant_name,
    m.material_id,
    m.material_description,
    m.criticality_class,
    i.total_inspections,
    i.failed_inspections,
    CAST(100.0 * i.failed_inspections / NULLIF(i.total_inspections, 0)
         AS DECIMAL(5,2))                                                  AS defect_rate_pct,
    -- flag for review: aerospace-grade material with >0.5% defect rate
    CASE
        WHEN m.is_aerospace_grade = 1
         AND 100.0 * i.failed_inspections / NULLIF(i.total_inspections, 0) > 0.5
        THEN 'REVIEW_REQUIRED'
        ELSE 'OK'
    END                                                                    AS review_flag
FROM inspections             i
JOIN dbo.dim_plant           p ON p.plant_code  = i.plant_code
JOIN dbo.dim_material        m ON m.material_id = i.material_id AND m.is_current = 1
ORDER BY defect_rate_pct DESC;
