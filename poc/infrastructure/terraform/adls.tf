###############################################################################
# adls.tf — ADLS Gen2 lake with hierarchical namespace, CMK, lifecycle.
###############################################################################

resource "azurerm_storage_account" "lake" {
  name                          = "chandanlake${local.env}"
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = azurerm_resource_group.rg.location
  account_tier                  = "Standard"
  account_replication_type      = local.env == "prod" ? "ZRS" : "LRS"
  account_kind                  = "StorageV2"
  is_hns_enabled                = true              # ADLS Gen2 hierarchical NS
  min_tls_version               = "TLS1_2"
  public_network_access_enabled = false             # Private Endpoint only
  shared_access_key_enabled     = false             # AAD only
  default_to_oauth_authentication = true

  identity {
    type = "SystemAssigned"
  }

  blob_properties {
    versioning_enabled       = true
    change_feed_enabled      = true                 # CDF for DR replication
    last_access_time_enabled = true                 # required for lifecycle
    delete_retention_policy { days = 30 }
  }

  tags = local.common_tags
}

# CMK from Key Vault — required by data residency policy.
resource "azurerm_storage_account_customer_managed_key" "lake" {
  storage_account_id = azurerm_storage_account.lake.id
  key_vault_id       = azurerm_key_vault.kv.id
  key_name           = azurerm_key_vault_key.lake.name
  user_assigned_identity_id = azurerm_user_assigned_identity.lake_cmk.id
}

resource "azurerm_user_assigned_identity" "lake_cmk" {
  name                = "uai-${local.base}-lake-cmk"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  tags                = local.common_tags
}

resource "azurerm_key_vault_key" "lake" {
  name         = "lake-cmk"
  key_vault_id = azurerm_key_vault.kv.id
  key_type     = "RSA-HSM"
  key_size     = 2048
  key_opts     = ["wrapKey", "unwrapKey"]
}

# Bronze / Silver / Gold + landing + checkpoints + staging.
resource "azurerm_storage_container" "containers" {
  for_each              = toset(["bronze", "silver", "gold", "landing", "checkpoints", "staging"])
  name                  = each.key
  storage_account_name  = azurerm_storage_account.lake.name
  container_access_type = "private"
}

# Lifecycle: Bronze Hot 30d → Cool 90d → Archive (7-yr AS9100 retention).
resource "azurerm_storage_management_policy" "lifecycle" {
  storage_account_id = azurerm_storage_account.lake.id

  rule {
    name    = "bronze-tiering"
    enabled = true
    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["bronze/"]
    }
    actions {
      base_blob {
        tier_to_cool_after_days_since_last_access_greater_than    = 30
        tier_to_archive_after_days_since_last_access_greater_than = 90
        delete_after_days_since_modification_greater_than         = 2555     # 7 years
      }
    }
  }

  rule {
    name    = "silver-tiering"
    enabled = true
    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["silver/"]
    }
    actions {
      base_blob {
        tier_to_cool_after_days_since_last_access_greater_than = 90
      }
    }
  }
}
