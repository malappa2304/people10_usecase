###############################################################################
# main.tf — root module for Chandan Aerospace Azure platform
#
# Layout
#   main.tf         — providers, locals, resource group, tagging
#   networking.tf   — vnet, subnets, NSGs, Private DNS, Private Endpoints
#   adls.tf         — ADLS Gen2 storage + containers + lifecycle
#   databricks.tf   — Databricks workspace + Unity Catalog metastore binding
#   synapse.tf      — Synapse workspace + Dedicated + Serverless
#   monitoring.tf   — Log Analytics + Action Groups + diagnostic settings
#
# State is held in an Azure Storage backend (configured via tfvars in CI).
# Foundation phase deploys this; per-domain pipeline code lives in Bicep + DAB.
###############################################################################

terraform {
  required_version = ">= 1.6.0"
  required_providers {
    azurerm    = { source = "hashicorp/azurerm",    version = "~> 3.110" }
    databricks = { source = "databricks/databricks", version = "~> 1.45" }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
  }
}

locals {
  env  = var.environment           # dev | uat | prod
  loc  = "centralindia"            # ITAR-adjacent residency requirement
  base = "chandan-${local.env}"

  common_tags = {
    project        = "chandan-aerospace-lakehouse"
    owner          = "data-platform-team"
    environment    = local.env
    cost_center    = "CC-DATA-001"
    data_class     = "AS9100-ITAR-Adjacent"
    residency      = "Central India only"
    managed_by     = "terraform"
  }
}

variable "environment" {
  description = "dev | uat | prod"
  type        = string
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${local.base}"
  location = local.loc
  tags     = local.common_tags
}

# Key Vault — CMK for ADLS, Synapse, Databricks; secrets for SAP/SFTP creds.
resource "azurerm_key_vault" "kv" {
  name                       = "kv-${local.base}-${random_id.kv.hex}"
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "premium"   # Premium needed for HSM-backed keys
  purge_protection_enabled   = true
  soft_delete_retention_days = 90
  enable_rbac_authorization  = true
  public_network_access_enabled = false    # PE only

  tags = local.common_tags
}

resource "random_id" "kv" {
  byte_length = 3
}

data "azurerm_client_config" "current" {}
