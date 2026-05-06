-- =============================================================================
-- source_config_seed.sql — control-plane seed data for ADF master orchestrator.
-- Apply this against the Azure SQL control DB during Foundation phase.
-- =============================================================================

IF OBJECT_ID('dbo.source_config', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.source_config (
        source_id            INT          IDENTITY(1,1) PRIMARY KEY,
        source_system        VARCHAR(40)  NOT NULL,
        source_type          VARCHAR(20)  NOT NULL,    -- db_cdc | sftp_file | api_rest | stream
        entity               VARCHAR(80)  NOT NULL,
        ingestion_pattern    VARCHAR(40)  NOT NULL,    -- incremental | full | snapshot
        schedule_cron        VARCHAR(40)  NULL,        -- NULL for event-driven / streaming
        target_bronze_path   VARCHAR(200) NOT NULL,
        sla_minutes          INT          NOT NULL,    -- alert if not landed within this
        is_active            BIT          NOT NULL DEFAULT 1,
        created_at           DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME(),
        updated_at           DATETIME2(0) NOT NULL DEFAULT SYSUTCDATETIME()
    );
END;
GO

INSERT INTO dbo.source_config
    (source_system, source_type, entity, ingestion_pattern, schedule_cron, target_bronze_path, sla_minutes)
VALUES
    -- SAP S/4HANA (on-prem) — db_cdc via SAP CDC connector.
    ('SAP_S4HANA',  'db_cdc',   'production_order',           'incremental', '0 2 * * *', 'sap/production_order',         60),
    ('SAP_S4HANA',  'db_cdc',   'material_master',            'incremental', '0 2 * * *', 'sap/material_master',          60),
    ('SAP_S4HANA',  'db_cdc',   'purchase_order_requirements','incremental', '0 2 * * *', 'sap/po_requirements',          60),

    -- MES (on-prem SQL Server) — db_cdc via SHIR + watermarked JDBC.
    ('MES',         'db_cdc',   'work_order',                 'incremental', '*/30 * * * *', 'mes/work_order',            45),
    ('MES',         'db_cdc',   'quality_inspection',         'incremental', '*/30 * * * *', 'mes/quality_inspection',    45),

    -- Teamcenter PLM — api_rest.
    ('TEAMCENTER',  'api_rest', 'engineering_change',         'incremental', '0 */4 * * *', 'plm/engineering_change',     90),
    ('TEAMCENTER',  'api_rest', 'bom',                        'snapshot',    '0 1 * * *',   'plm/bom',                    90),

    -- Supplier portals — sftp_file (event-driven trigger covers urgent runs).
    ('SUP_TATA_AERO','sftp_file','supplier_dispatch',         'incremental', NULL,         'supplier/dispatch/tata',     30),
    ('SUP_MAHLE_IN','sftp_file', 'supplier_dispatch',         'incremental', NULL,         'supplier/dispatch/mahle',    30),
    ('SUP_HEXCEL_IN','sftp_file','supplier_dispatch',         'incremental', NULL,         'supplier/dispatch/hexcel',   30),

    -- CNC OPC-UA — stream (handled by Databricks Structured Streaming, not ADF).
    ('OPC_UA_HYD1', 'stream',   'cnc_telemetry',              'continuous',  NULL,         'iot/cnc_telemetry/hyd1',     5),
    ('OPC_UA_BLR2', 'stream',   'cnc_telemetry',              'continuous',  NULL,         'iot/cnc_telemetry/blr2',     5);
GO
