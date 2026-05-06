###############################################################################
# databricks.tf — Databricks workspace + Unity Catalog binding + cluster pools.
###############################################################################

resource "azurerm_databricks_workspace" "dbx" {
  name                = "dbx-${local.base}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "premium"   # required for UC, Photon, RBAC

  custom_parameters {
    no_public_ip                                         = true
    virtual_network_id                                   = azurerm_virtual_network.vnet.id
    public_subnet_name                                   = azurerm_subnet.dbx_public.name
    private_subnet_name                                  = azurerm_subnet.dbx_private.name
    public_subnet_network_security_group_association_id  = azurerm_subnet_network_security_group_association.dbx_public.id
    private_subnet_network_security_group_association_id = azurerm_subnet_network_security_group_association.dbx_private.id
  }

  # CMK with the same Key Vault key — single source of truth for crypto.
  customer_managed_key_enabled = true

  tags = local.common_tags
}

# Unity Catalog metastore — one per region; we attach the workspace to it.
# (Provider config for the databricks workspace is in a separate aliased
#  block in CI; omitted here for skeleton brevity.)
resource "databricks_metastore" "central_india" {
  name          = "uc-central-india"
  storage_root  = "abfss://uc-metastore@${azurerm_storage_account.lake.name}.dfs.core.windows.net/"
  region        = local.loc
  force_destroy = false
}

resource "databricks_metastore_assignment" "this" {
  workspace_id         = azurerm_databricks_workspace.dbx.workspace_id
  metastore_id         = databricks_metastore.central_india.id
  default_catalog_name = "chandan_${local.env}"
}

# Cluster pool for batch jobs — spot workers for non-critical, on-demand for recon.
resource "databricks_instance_pool" "batch" {
  instance_pool_name = "batch-pool-${local.env}"
  min_idle_instances = 0
  max_capacity       = 32
  node_type_id       = "Standard_DS4_v2"

  azure_attributes {
    availability       = "SPOT_AZURE"
    spot_bid_max_price = -1   # accept current spot price
    first_on_demand    = 1
  }

  idle_instance_autotermination_minutes = 10
}
