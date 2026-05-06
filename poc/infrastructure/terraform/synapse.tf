###############################################################################
# synapse.tf — Synapse workspace + Dedicated SQL pool + Serverless config.
###############################################################################

resource "azurerm_synapse_workspace" "syn" {
  name                                 = "syn-${local.base}"
  resource_group_name                  = azurerm_resource_group.rg.name
  location                             = azurerm_resource_group.rg.location
  storage_data_lake_gen2_filesystem_id = "${azurerm_storage_account.lake.id}/blobServices/default/containers/gold"

  sql_administrator_login              = "synadmin"
  sql_administrator_login_password     = azurerm_key_vault_secret.syn_admin_pwd.value

  managed_virtual_network_enabled = true
  public_network_access_enabled   = false
  data_exfiltration_protection_enabled = true

  identity {
    type = "SystemAssigned"
  }

  customer_managed_key {
    key_versionless_id = azurerm_key_vault_key.lake.versionless_id
  }

  tags = local.common_tags
}

resource "random_password" "syn_admin" {
  length  = 32
  special = true
}

resource "azurerm_key_vault_secret" "syn_admin_pwd" {
  name         = "synapse-admin-password"
  value        = random_password.syn_admin.result
  key_vault_id = azurerm_key_vault.kv.id
}

# Dedicated pool for executive Power BI workload — DW400c base, scaled to 1000c at peak.
resource "azurerm_synapse_sql_pool" "dedicated" {
  name                 = "dwexec"
  synapse_workspace_id = azurerm_synapse_workspace.syn.id
  sku_name             = "DW400c"
  storage_account_type = "GRS"
  create_mode          = "Default"
  data_encrypted       = true

  tags = local.common_tags
}

# Pause schedule (off Sat-Sun, 22:00-06:00 weekdays) is enforced via an Azure
# Automation runbook; the resource block here is the Auto-pause linked logic
# app trigger. (Logic App resource omitted in skeleton.)
output "synapse_dedicated_pause_schedule_note" {
  value       = "Auto-pause runbook deploys via separate Bicep — see infrastructure/bicep/synapse_auto_pause.bicep"
  description = "30-40% serving cost saving; documented separately per cost-optimisation lever #3."
}
