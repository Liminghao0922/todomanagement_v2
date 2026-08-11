param location string
param projectName string
param foundryProjectName string

var foundryAccountName = 'aifoundry-${toLower(projectName)}-${uniqueString(resourceGroup().id)}'

resource aiServices 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: foundryAccountName
  location: location
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  sku: {
    name: 'S0'
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: foundryAccountName
    publicNetworkAccess: 'Enabled'
  }
}

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: aiServices
  name: 'text-embedding-3-small'
  sku: {
    name: 'Standard'
    capacity: 10
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-small'
      version: '1'
    }
  }
}

resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: aiServices
  name: 'gpt-5.4-mini'
  dependsOn: [
    embeddingDeployment
  ]
  sku: {
    name: 'GlobalStandard'
    capacity: 100
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-5.4-mini'
      version: '2026-03-17'
    }
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: aiServices
  name: foundryProjectName
  location: location
  dependsOn: [
    embeddingDeployment
    chatDeployment
  ]
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: foundryProjectName
    description: 'Default Foundry project for the Todo Management workshop.'
  }
}

output foundryResourceName string = aiServices.name
output foundryResourceId string = aiServices.id
output foundryEndpoint string = aiServices.properties.endpoint
output foundryProjectName string = project.name
output foundryProjectResourceId string = project.id
output foundryProjectEndpoint string = 'https://${aiServices.name}.services.ai.azure.com/api/projects/${project.name}'
output foundryAccountName string = aiServices.name
output chatDeploymentName string = chatDeployment.name
output embeddingDeploymentName string = embeddingDeployment.name
output foundryNote string = 'Foundry AI Services resource, default project, and model deployments are created by Bicep. Configure Agent/tools in Azure AI Foundry Web UI.'
