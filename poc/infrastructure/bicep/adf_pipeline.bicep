// =============================================================================
// adf_pipeline.bicep — ADF resource + master orchestrator deployment.
//
// Why Bicep here, when Terraform handles foundation
// -------------------------------------------------
// ADF authoring tools (UI + Git integration) round-trip natively to ADF JSON
// and to Bicep, but not to Terraform's HCL. Keeping ADF on Bicep means the
// data engineering team can author in the ADF Studio UI, commit, and have CI
// promote without a translation layer. (Terraform azurerm_data_factory_*
// resources do exist but rebuild every pipeline on every plan change in
// our experience, which is annoying for a 50-pipeline factory.)
// =============================================================================

@description('Environment name: dev | uat | prod')
param environment string

@description('Location — must be Central India for ITAR-adjacent residency')
param location string = 'centralindia'

@description('Key Vault resource id for managed-identity secret access')
param keyVaultId string

@description('Databricks workspace resource id')
param databricksWorkspaceId string

var adfName = 'adf-chandan-${environment}'

resource adf 'Microsoft.DataFactory/factories@2018-06-01' = {
  name: adfName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    publicNetworkAccess: 'Disabled'        // PE only
    encryption: {
      vaultBaseUrl: reference(keyVaultId, '2023-07-01').vaultUri
      keyName:      'lake-cmk'
      // identity: managed identity grants for unwrapKey are set by the foundation TF.
    }
  }
  tags: {
    project: 'chandan-aerospace-lakehouse'
    environment: environment
  }
}

// Linked services + datasets + pipelines + triggers are deployed via
// `az datafactory create` from the JSON files under poc/adf/. Bicep only
// owns the factory resource itself + diagnostic settings.

resource adfDiag 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  scope: adf
  name: 'diag-${adfName}'
  properties: {
    workspaceId: '/subscriptions/<sub-id>/resourceGroups/rg-chandan-${environment}/providers/Microsoft.OperationalInsights/workspaces/law-chandan-${environment}'
    logs: [
      { categoryGroup: 'allLogs', enabled: true }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true }
    ]
  }
}

output adfId string = adf.id
output adfPrincipalId string = adf.identity.principalId
