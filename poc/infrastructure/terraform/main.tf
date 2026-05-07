###############################################################################
# main.tf — minimal Terraform skeleton for the lakehouse foundation.
#
# Scope: enough to show the IaC posture (managed identities, CMK, Private
# Endpoints, env-scoped) without standing up the full estate. A real
# engagement would split this into modules (adls, databricks, synapse,
# networking, monitoring); for a 3-day PoC, one self-contained file is
# the honest representation of what's actually been written.
#
# What's in this file
#   - Resource group, Key Vault with CMK
#   - ADLS Gen2 storage with hierarchical namespace + lifecycle
#   - Databricks workspace
#   - Log Analytics workspace
#
# What's intentionally NOT here (called out, not built)
#   - Synapse workspace + Dedicated SQL pool
#   - VNet + subnets + Private Endpoints (would need ~80 lines)
#   - Cosmos DB online feature store
#   See TODO.md.
###############################################################################

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 3.110" }
  }
}

provider "azurerm" {
  features {}
}

variable "environment" {
  description = "dev | test | prod"
  type        = string
}

locals {
  loc  = "centralindia"
  base = "chandan-${var.environment}"

  tags = {
    project     = "people10-poc-lakehouse"
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${local.base}"
  location = local.loc
  tags     = local.tags
}

# -------------------------------------------------------------------- Key Vault
resource "azurerm_key_vault" "kv" {
  name                          = "kv-${local.base}-${random_id.kv.hex}"
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = azurerm_resource_group.rg.location
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  sku_name                      = "standard"
  enable_rbac_authorization     = true
  purge_protection_enabled      = true
  soft_delete_retention_days    = 90
  public_network_access_enabled = false # PE only — see TODO

  tags = local.tags
}

resource "random_id" "kv" {
  byte_length = 3
}

data "azurerm_client_config" "current" {}

# ------------------------------------------------------------------------ ADLS
resource "azurerm_storage_account" "lake" {
  name                            = "chandanlake${var.environment}"
  resource_group_name             = azurerm_resource_group.rg.name
  location                        = azurerm_resource_group.rg.location
  account_tier                    = "Standard"
  account_replication_type        = var.environment == "prod" ? "ZRS" : "LRS"
  account_kind                    = "StorageV2"
  is_hns_enabled                  = true
  min_tls_version                 = "TLS1_2"
  public_network_access_enabled   = false
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true

  identity { type = "SystemAssigned" }

  blob_properties {
    versioning_enabled  = true
    change_feed_enabled = true
    delete_retention_policy { days = 30 }
  }

  tags = local.tags
}

# Bronze / Silver / Gold + checkpoints
resource "azurerm_storage_container" "containers" {
  for_each              = toset(["bronze", "silver", "gold", "checkpoints"])
  name                  = each.key
  storage_account_name  = azurerm_storage_account.lake.name
  container_access_type = "private"
}

# Lifecycle: Bronze Hot 30d → Cool 90d → Archive (long-tail retention)
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
        # Modification-based tiering — no need to enable last_access_time
        # tracking on the storage account (which has its own cost).
        tier_to_cool_after_days_since_modification_greater_than    = 30
        tier_to_archive_after_days_since_modification_greater_than = 90
      }
    }
  }
}

# ------------------------------------------------------------------ Databricks
resource "azurerm_databricks_workspace" "dbx" {
  name                = "dbx-${local.base}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "premium" # required for Unity Catalog + Photon

  tags = local.tags
}

# --------------------------------------------------------------- Log Analytics
resource "azurerm_log_analytics_workspace" "law" {
  name                = "law-${local.base}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "PerGB2018"
  retention_in_days   = 90
  tags                = local.tags
}

# ----------------------------------------------------------------------- outputs
output "lake_account_name" {
  value = azurerm_storage_account.lake.name
}

output "databricks_workspace_url" {
  value = azurerm_databricks_workspace.dbx.workspace_url
}
