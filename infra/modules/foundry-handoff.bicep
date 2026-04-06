param location string
param projectName string

resource aiServices 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: 'aifoundry-${toLower(projectName)}-${uniqueString(resourceGroup().id)}'
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

output foundryResourceName string = aiServices.name
output foundryResourceId string = aiServices.id
output foundryNote string = 'Create the Foundry project in Azure AI Foundry Web UI and attach built-in Graph/Cosmos tools plus Function custom tools.'
