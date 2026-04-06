param location string
param projectName string
param environment string
param cosmosEndpoint string
param cosmosAccountName string
param cosmosGremlinEndpoint string
param sqlDatabaseName string
param graphDatabaseName string
param graphName string
param openaiEndpoint string
param openaiAccountName string
param chatDeploymentName string
param embeddingDeploymentName string
param foundryAgentEndpoint string
@secure()
param foundryAgentApiKey string
param graphTenantId string
param graphClientId string
@secure()
param graphClientSecret string

var storageName = 'st${toLower(projectName)}${uniqueString(resourceGroup().id)}'
var planName = 'asp-${projectName}-${environment}'
var appName = 'func-${projectName}-${environment}-${uniqueString(resourceGroup().id)}'

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: cosmosAccountName
}

resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: openaiAccountName
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
}

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  kind: 'functionapp'
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true
  }
}

resource app 'Microsoft.Web/sites@2023-12-01' = {
  name: appName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storage.name};AccountKey=${storage.listKeys().keys[0].value};EndpointSuffix=core.windows.net'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'COSMOS_ENDPOINT'
          value: cosmosEndpoint
        }
        {
          name: 'COSMOS_KEY'
          value: cosmos.listKeys().primaryMasterKey
        }
        {
          name: 'COSMOS_DATABASE_NAME'
          value: sqlDatabaseName
        }
        {
          name: 'COSMOS_GREMLIN_ENDPOINT'
          value: cosmosGremlinEndpoint
        }
        {
          name: 'COSMOS_GREMLIN_DATABASE'
          value: graphDatabaseName
        }
        {
          name: 'COSMOS_GREMLIN_GRAPH'
          value: graphName
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: openaiEndpoint
        }
        {
          name: 'AZURE_OPENAI_KEY'
          value: openai.listKeys().key1
        }
        {
          name: 'AZURE_OPENAI_CHAT_DEPLOYMENT'
          value: chatDeploymentName
        }
        {
          name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT'
          value: embeddingDeploymentName
        }
        {
          name: 'FOUNDRY_AGENT_ENDPOINT'
          value: foundryAgentEndpoint
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

output functionAppName string = app.name
output functionAppUrl string = 'https://${app.properties.defaultHostName}'
output functionAppPrincipalId string = app.identity.principalId
