-- =============================================================================
-- dq_rules_seed.sql — config-driven DQ rules consumed by 05_dq_runner.py
-- and mirrored to audit.dq_rules in Delta. Three severity tiers.
-- =============================================================================

IF OBJECT_ID('dbo.dq_rules', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.dq_rules (
        rule_id      VARCHAR(40)  NOT NULL PRIMARY KEY,
        table_name   VARCHAR(120) NOT NULL,
        column_name  VARCHAR(80)  NULL,
        expression   VARCHAR(MAX) NOT NULL,
        severity     VARCHAR(12)  NOT NULL,    -- BLOCK | QUARANTINE | WARN
        description  VARCHAR(400) NOT NULL,
        is_enabled   BIT          NOT NULL DEFAULT 1,
        created_at   DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

INSERT INTO dbo.dq_rules (rule_id, table_name, column_name, expression, severity, description) VALUES
-- ===== silver.production_order =====
('po_001', 'silver.production_order', 'production_order_id', 'production_order_id IS NOT NULL',          'BLOCK',
 'Primary key must not be NULL — without this Gold cannot join.'),
('po_002', 'silver.production_order', 'plant_code',          'plant_code IN (SELECT plant_code FROM gold.dim_plant)',
                                                                                                          'QUARANTINE',
 'Unknown plant code — quarantine for master-data review.'),
('po_003', 'silver.production_order', 'quantity',            'quantity > 0',                              'QUARANTINE',
 'Non-positive quantity is suspicious — keep audit trail before re-emit.'),
('po_004', 'silver.production_order', 'posting_ts_utc',      'posting_ts_utc <= current_timestamp() + interval 7 days',
                                                                                                          'WARN',
 'Future-dated posting — likely SAP test material; surface as metric only.'),

-- ===== silver.supplier_dispatch =====
('sd_001', 'silver.supplier_dispatch', 'purchase_order_id',  'purchase_order_id IS NOT NULL',             'BLOCK',
 'Without PO id we cannot tie back to demand; pipeline must stop.'),
('sd_002', 'silver.supplier_dispatch', 'delivery_qty',       'delivery_qty >= 0',                          'QUARANTINE',
 'Negative delivery qty = correction posting; quarantine for accounting review.'),
('sd_003', 'silver.supplier_dispatch', NULL,                  'actual_delivery_ts_utc IS NULL OR actual_delivery_ts_utc >= expected_delivery_ts_utc - interval 60 days',
                                                                                                          'QUARANTINE',
 'Actual delivery more than 60 days before expected = data error or test row.'),

-- ===== gold.fact_supplier_otd (post-build sanity) =====
('otd_001', 'gold.fact_supplier_otd', 'otd_status',          'otd_status IN (''ON_TIME'',''LATE'',''PENDING'')',
                                                                                                          'BLOCK',
 'Status whitelist — protects downstream Power BI measures.'),
('otd_002', 'gold.fact_supplier_otd', 'supplier_id',         'supplier_id IN (SELECT supplier_id FROM gold.dim_supplier WHERE is_current = true)',
                                                                                                          'WARN',
 'Unknown supplier — surface metric to master-data team.'),

-- ===== silver.cnc_telemetry_1min =====
('cnc_001', 'silver.cnc_telemetry_1min', 'vibration_g_avg',  'vibration_g_avg < 5.0',                     'WARN',
 'Avg vibration > 5g across a minute is a candidate alarm — surface, do not block.'),
('cnc_002', 'silver.cnc_telemetry_1min', 'event_count',      'event_count > 0',                            'BLOCK',
 'Empty 1-min window means streaming pipeline lost a partition; page on-call.');
GO
