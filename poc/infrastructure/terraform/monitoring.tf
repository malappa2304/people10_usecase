###############################################################################
# monitoring.tf — Log Analytics + Action Groups + diagnostic settings.
###############################################################################

resource "azurerm_log_analytics_workspace" "law" {
  name                = "law-${local.base}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "PerGB2018"
  retention_in_days   = 90
  tags                = local.common_tags
}

# Diagnostics on storage / synapse / databricks → Log Analytics.
resource "azurerm_monitor_diagnostic_setting" "lake" {
  name                       = "diag-lake"
  target_resource_id         = azurerm_storage_account.lake.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id

  metric { category = "Transaction" }
}

resource "azurerm_monitor_diagnostic_setting" "syn" {
  name                       = "diag-syn"
  target_resource_id         = azurerm_synapse_workspace.syn.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id

  enabled_log { category_group = "audit" }
  enabled_log { category_group = "allLogs" }
}

# Action groups — one per severity, routed to Teams (P3/P4) or PagerDuty (P1/P2).
resource "azurerm_monitor_action_group" "p1_p2" {
  name                = "ag-${local.base}-p1p2"
  resource_group_name = azurerm_resource_group.rg.name
  short_name          = "p1p2"

  webhook_receiver {
    name                    = "pagerduty"
    service_uri             = "https://events.pagerduty.com/integration/CHANDAN_SVC/enqueue"
    use_common_alert_schema = true
  }

  email_receiver {
    name          = "data-platform-oncall"
    email_address = "data-oncall@chandan.example.com"
  }

  tags = local.common_tags
}

resource "azurerm_monitor_action_group" "p3_p4" {
  name                = "ag-${local.base}-p3p4"
  resource_group_name = azurerm_resource_group.rg.name
  short_name          = "p3p4"

  webhook_receiver {
    name                    = "teams"
    service_uri             = "https://outlook.office.com/webhook/teams-data-platform"  # MOCK
    use_common_alert_schema = true
  }

  tags = local.common_tags
}

# Example metric alert — Synapse DWU at 80%+ for 15 minutes (capacity warning).
resource "azurerm_monitor_metric_alert" "syn_dwu" {
  name                = "alert-${local.base}-syn-dwu"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_synapse_sql_pool.dedicated.id]
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.Synapse/workspaces/sqlPools"
    metric_name      = "DWUUsedPercent"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80
  }

  action { action_group_id = azurerm_monitor_action_group.p3_p4.id }
}
