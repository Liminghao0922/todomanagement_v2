targetScope = 'resourceGroup'

metadata description = 'Todo Management v3 infrastructure: Functions + SWA + Cosmos + Foundry-ready resources'

param location string = 'japaneast'
param staticWebAppLocation string = 'eastasia'
param environment string = 'dev'
param projectName string = 'todomanagement'
param foundryAgentEndpoint string = ''
@secure()
param foundryAgentApiKey string = ''
param graphTenantId string = ''
param graphClientId string = ''
@secure()
param graphClientSecret string = ''
param deployCosmosMcpToolkit bool = true
param deployCosmosMcpAppRegistration bool = true
param cosmosMcpImage string = ''
param cosmosMcpImageRepository string = 'mcp-toolkit'
param cosmosMcpImageTag string = 'latest'
param cosmosMcpClientId string = ''
param cosmosMcpAudience string = ''
param cosmosMcpContainerAppName string = ''
param cosmosMcpContainerAppEnvironmentName string = ''
param cosmosMcpLogAnalyticsWorkspaceName string = ''
param cosmosMcpCpu string = '0.5'
param cosmosMcpMemory string = '1Gi'
param deployCosmosMcpAcr bool = true
param cosmosMcpAcrName string = ''
@allowed([
  'Basic'
  'Standard'
  'Premium'
])
param cosmosMcpAcrSku string = 'Basic'

var storageNameBase = toLower(replace(replace(projectName, '-', ''), '_', ''))
var functionStorageName = 'st${take(storageNameBase, 8)}${uniqueString(resourceGroup().id)}'
var functionDeploymentContainerName = 'function-releases'
var functionPlanName = 'asp-${projectName}-${environment}'
var functionAppName = 'func-${projectName}-${environment}-${uniqueString(resourceGroup().id)}'
var foundryAccountName = 'aifoundry-${toLower(projectName)}-${uniqueString(resourceGroup().id)}'
var foundryProjectName = 'proj-todomanagement'
var foundryProjectEndpointValue = empty(foundryAgentEndpoint) ? foundry.outputs.foundryProjectEndpoint : foundryAgentEndpoint
var mcpAcrEnabled = deployCosmosMcpToolkit && deployCosmosMcpAcr
var cosmosMcpAcrEffectiveName = empty(cosmosMcpAcrName) ? 'acr${take(storageNameBase, 10)}${take(uniqueString(resourceGroup().id), 6)}' : cosmosMcpAcrName
var cosmosMcpImageFromAcr = '${cosmosMcpAcrEffectiveName}.azurecr.io/${cosmosMcpImageRepository}:${cosmosMcpImageTag}'
var cosmosMcpImageEffective = !empty(cosmosMcpImage) ? cosmosMcpImage : (mcpAcrEnabled ? cosmosMcpImageFromAcr : '')
var cosmosMcpDeploymentImage = empty(cosmosMcpImage) && mcpAcrEnabled ? 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' : cosmosMcpImageEffective
var mcpAppRegistrationEnabled = deployCosmosMcpToolkit && deployCosmosMcpAppRegistration && empty(cosmosMcpClientId)
var cosmosMcpClientIdEffective = !empty(cosmosMcpClientId) ? cosmosMcpClientId : (mcpAppRegistrationEnabled ? mcpAppRegistration!.outputs.appId : '')
var mcpToolkitEnabled = deployCosmosMcpToolkit && !empty(cosmosMcpImageEffective) && (!empty(cosmosMcpClientId) || mcpAppRegistrationEnabled)
var cosmosMcpIdentityName = 'id-mcp-${take(storageNameBase, 12)}-${take(uniqueString(resourceGroup().id), 6)}'
var tenantIdValue = empty(graphTenantId) ? tenant().tenantId : graphTenantId

module cosmos './modules/cosmos.bicep' = {
  name: 'cosmos-deployment'
  params: {
    location: location
    projectName: projectName
  }
}

module foundry './modules/foundry-handoff.bicep' = {
  name: 'foundry-deployment'
  params: {
    location: location
    projectName: projectName
    foundryProjectName: foundryProjectName
  }
}

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryAccountName
}

resource foundryProject 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: foundryAccount
  name: foundryProjectName
}

resource functionStorage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: functionStorageName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowSharedKeyAccess: false
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
  }
}

resource functionStorageBlobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: functionStorage
  name: 'default'
}

resource functionDeploymentContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: functionStorageBlobService
  name: functionDeploymentContainerName
  properties: {
    publicAccess: 'None'
  }
}

resource functionPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: functionPlanName
  location: location
  kind: 'functionapp'
  sku: {
    name: 'FC1'
    tier: 'FlexConsumption'
  }
  properties: {
    reserved: true
  }
}

resource functionApp 'Microsoft.Web/sites@2023-12-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: functionPlan.id
    httpsOnly: true
    functionAppConfig: {
      runtime: {
        name: 'python'
        version: '3.11'
      }
      scaleAndConcurrency: {
        instanceMemoryMB: 2048
        maximumInstanceCount: 100
      }
      deployment: {
        storage: {
          type: 'blobContainer'
          value: '${functionStorage.properties.primaryEndpoints.blob}${functionDeploymentContainerName}'
          authentication: {
            type: 'SystemAssignedIdentity'
          }
        }
      }
    }
    siteConfig: {
      appSettings: [
        {
          name: 'AzureWebJobsStorage__accountName'
          value: functionStorage.name
        }
        {
          name: 'AzureWebJobsStorage__credential'
          value: 'managedidentity'
        }
        {
          name: 'COSMOS_ENDPOINT'
          value: cosmos.outputs.cosmosEndpoint
        }
        {
          name: 'COSMOS_AUTH_MODE'
          value: 'aad'
        }
        {
          name: 'COSMOS_DATABASE_NAME'
          value: cosmos.outputs.sqlDatabaseName
        }
        {
          name: 'COSMOS_GREMLIN_ENDPOINT'
          value: cosmos.outputs.cosmosGremlinEndpoint
        }
        {
          name: 'COSMOS_GREMLIN_DATABASE'
          value: cosmos.outputs.graphDatabaseName
        }
        {
          name: 'COSMOS_GREMLIN_GRAPH'
          value: cosmos.outputs.graphName
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: foundry.outputs.foundryEndpoint
        }
        {
          name: 'AZURE_OPENAI_KEY'
          value: ''
        }
        {
          name: 'AZURE_OPENAI_CHAT_DEPLOYMENT'
          value: foundry.outputs.chatDeploymentName
        }
        {
          name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT'
          value: foundry.outputs.embeddingDeploymentName
        }
        {
          name: 'FOUNDRY_AGENT_ENDPOINT'
          value: foundryProjectEndpointValue
        }
        {
          name: 'FOUNDRY_PROJECT_ENDPOINT'
          value: foundryProjectEndpointValue
        }
        {
          name: 'FOUNDRY_EMBEDDING_DEPLOYMENT'
          value: foundry.outputs.embeddingDeploymentName
        }
        {
          name: 'FOUNDRY_AGENT_API_KEY'
          value: foundryAgentApiKey
        }
        {
          name: 'GRAPH_TENANT_ID'
          value: graphTenantId
        }
        {
          name: 'GRAPH_CLIENT_ID'
          value: graphClientId
        }
        {
          name: 'GRAPH_CLIENT_SECRET'
          value: graphClientSecret
        }
      ]
      ftpsState: 'Disabled'
      minTlsVersion: '1.2'
    }
  }
}

resource functionFoundryUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundryProject.id, functionApp.id, 'foundry-user')
  scope: foundryProject
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource functionStorageBlobRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionStorage.id, functionApp.id, 'function-storage-blob-data-owner')
  scope: functionStorage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b')
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource functionStorageQueueRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionStorage.id, functionApp.id, 'function-storage-queue-data-contributor')
  scope: functionStorage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '974c5e8b-45b9-4653-ba55-5f855dd0fb88')
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource functionStorageTableRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(functionStorage.id, functionApp.id, 'function-storage-table-data-contributor')
  scope: functionStorage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3')
    principalId: functionApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

module swa './modules/swa.bicep' = {
  name: 'swa-deployment'
  params: {
    location: staticWebAppLocation
    projectName: projectName
  }
}

module graphApp './modules/graph-app-registration.bicep' = {
  name: 'graph-app-registration'
  params: {
    projectName: projectName
    webAppUrl: swa.outputs.swaUrl
  }
}

resource cosmosMcpAcr 'Microsoft.ContainerRegistry/registries@2023-07-01' = if (mcpAcrEnabled) {
  name: cosmosMcpAcrEffectiveName
  location: location
  sku: {
    name: cosmosMcpAcrSku
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

resource cosmosMcpIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = if (mcpToolkitEnabled) {
  name: cosmosMcpIdentityName
  location: location
}

resource cosmosMcpAcrPullRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (mcpToolkitEnabled && mcpAcrEnabled) {
  name: guid(resourceGroup().id, cosmosMcpAcrEffectiveName, cosmosMcpIdentityName, 'mcp-acr-pull')
  scope: cosmosMcpAcr!
  properties: {
    principalId: cosmosMcpIdentity!.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  }
}

module mcpAppRegistration './modules/mcp-app-registration.bicep' = if (mcpAppRegistrationEnabled) {
  name: 'mcp-app-registration'
  params: {
    projectName: projectName
    environment: environment
  }
}

module cosmosMcpToolkit './modules/cosmos-mcp-toolkit.bicep' = if (mcpToolkitEnabled) {
  name: 'cosmos-mcp-toolkit-deployment'
  params: {
    location: location
    projectName: projectName
    cosmosAccountName: cosmos.outputs.cosmosAccountName
    foundryEndpoint: foundry.outputs.foundryEndpoint
    tenantId: tenantIdValue
    mcpImage: cosmosMcpDeploymentImage
    mcpClientId: cosmosMcpClientIdEffective
    mcpAudience: cosmosMcpAudience
    containerAppName: cosmosMcpContainerAppName
    containerAppEnvironmentName: cosmosMcpContainerAppEnvironmentName
    logAnalyticsWorkspaceName: cosmosMcpLogAnalyticsWorkspaceName
    cpu: cosmosMcpCpu
    memory: cosmosMcpMemory
    registryServer: mcpAcrEnabled ? cosmosMcpAcr!.properties.loginServer : ''
    useManagedIdentityForRegistry: mcpAcrEnabled
    managedIdentityResourceId: cosmosMcpIdentity!.id
    managedIdentityClientId: cosmosMcpIdentity!.properties.clientId
    managedIdentityPrincipalId: cosmosMcpIdentity!.properties.principalId
  }
  dependsOn: [
    cosmosMcpAcrPullRoleAssignment
  ]
}

output cosmosEndpoint string = cosmos.outputs.cosmosEndpoint
output cosmosAccountName string = cosmos.outputs.cosmosAccountName
output cosmosGremlinEndpoint string = cosmos.outputs.cosmosGremlinEndpoint
output cosmosSqlDb string = cosmos.outputs.sqlDatabaseName
output cosmosGraphDb string = cosmos.outputs.graphDatabaseName
output cosmosGraphName string = cosmos.outputs.graphName

output functionAppName string = functionApp.name
output functionAppUrl string = 'https://${functionApp.properties.defaultHostName}'

output staticWebAppName string = swa.outputs.swaName
output staticWebAppUrl string = swa.outputs.swaUrl

output appRegistrationClientId string = graphApp.outputs.appId
output tenantId string = graphApp.outputs.tenantId

output foundryResourceName string = foundry.outputs.foundryResourceName
output foundryResourceId string = foundry.outputs.foundryResourceId
output foundryProjectName string = foundry.outputs.foundryProjectName
output foundryProjectResourceId string = foundry.outputs.foundryProjectResourceId
output foundryProjectEndpoint string = foundry.outputs.foundryProjectEndpoint
output foundryNote string = foundry.outputs.foundryNote
output cosmosMcpToolkitEnabled bool = mcpToolkitEnabled
output cosmosMcpClientId string = cosmosMcpClientIdEffective
output cosmosMcpAppRegistrationCreated bool = mcpAppRegistrationEnabled
output cosmosMcpImage string = mcpToolkitEnabled ? cosmosMcpImageEffective : ''
output cosmosMcpImageRepository string = mcpToolkitEnabled ? cosmosMcpImageRepository : ''
output cosmosMcpImageTag string = mcpToolkitEnabled ? cosmosMcpImageTag : ''
output cosmosMcpContainerAppName string = mcpToolkitEnabled ? cosmosMcpToolkit!.outputs.containerAppName : ''
output cosmosMcpContainerAppUrl string = mcpToolkitEnabled ? cosmosMcpToolkit!.outputs.containerAppUrl : ''
output cosmosMcpEndpoint string = mcpToolkitEnabled ? cosmosMcpToolkit!.outputs.mcpEndpoint : ''
output cosmosMcpAcrEnabled bool = mcpAcrEnabled
output cosmosMcpAcrName string = mcpAcrEnabled ? cosmosMcpAcr!.name : ''
output cosmosMcpAcrLoginServer string = mcpAcrEnabled ? cosmosMcpAcr!.properties.loginServer : ''
