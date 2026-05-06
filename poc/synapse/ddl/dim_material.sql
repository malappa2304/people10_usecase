-- =============================================================================
-- dim_material — SCD2 dimension
-- =============================================================================
-- Distribution: REPLICATE — small dimension (~50K rows), broadcasted on every
--   join. Replicate beats round-robin and hash for tables under ~2GB.
-- Index:        Clustered Columnstore.
-- =============================================================================

IF OBJECT_ID('dbo.dim_material', 'U') IS NOT NULL
    DROP TABLE dbo.dim_material;
GO

CREATE TABLE dbo.dim_material
(
    material_sk             BIGINT        IDENTITY(1,1) NOT NULL,
    material_id             VARCHAR(40)   NOT NULL,
    material_description    VARCHAR(200)  NULL,
    material_group          VARCHAR(40)   NULL,
    uom                     VARCHAR(8)    NULL,
    spec_revision           VARCHAR(20)   NULL,
    criticality_class       VARCHAR(20)   NULL,        -- CLASS_A / CLASS_B / CLASS_C
    is_aerospace_grade      BIT           NULL,
    supplier_default_id     VARCHAR(40)   NULL,
    row_hash                CHAR(64)      NOT NULL,
    effective_from_utc      DATETIME2(0)  NOT NULL,
    effective_to_utc        DATETIME2(0)  NULL,
    is_current              BIT           NOT NULL
)
WITH
(
    DISTRIBUTION = REPLICATE,
    CLUSTERED COLUMNSTORE INDEX
);
GO

CREATE STATISTICS stats_dim_mat_id    ON dbo.dim_material(material_id);
CREATE STATISTICS stats_dim_mat_curr  ON dbo.dim_material(is_current);
GO
