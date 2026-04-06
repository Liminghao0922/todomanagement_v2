targetScope = 'resourceGroup'

metadata description = 'Todo Management v3 infrastructure: Functions + SWA + Cosmos + Foundry-ready resources'

param location string = 'japaneast'
param environment string = 'dev'
param projectName string = 'todomanagement'
param foundryAgentEndpoint string = ''
@secure()
param foundryAgentApiKey string = ''
param graphTenantId string = ''
param graphClientId string = ''
@secure()
param graphClientSecret string = ''

module cosmos './modules/cosmos.bicep' = {
  name: 'cosmos-deployment'
  params: {
    location: location
    projectName: projectName
  }
}

module openai './modules/openai.bicep' = {
  name: 'openai-deployment'
  params: {
    location: location
    projectName: projectName
  }
}

module functions './modules/functions.bicep' = {
  name: 'functions-deployment'
  params: {
    location: location
    projectName: projectName
    environment: environment
    cosmosEndpoint: cosmos.outputs.cosmosEndpoint
    cosmosAccountName: cosmos.outputs.cosmosAccountName
    cosmosGremlinEndpoint: cosmos.outputs.cosmosGremlinEndpoint
    sqlDatabaseName: cosmos.outputs.sqlDatabaseName
    graphDatabaseName: cosmos.outputs.graphDatabaseName
    graphName: cosmos.outputs.graphName
    openaiEndpoint: openai.outputs.openaiEndpoint
    openaiAccountName: openai.outputs.openaiAccountName
    chatDeploymentName: openai.outputs.chatDeploymentName
    embeddingDeploymentName: openai.outputs.embeddingDeploymentName
    foundryAgentEndpoint: foundryAgentEndpoint
    foundryAgentApiKey: foundryAgentApiKey
    graphTenantId: graphTenantId
    graphClientId: graphClientId
    graphClientSecret: graphClientSecret
  }
}

module swa './modules/swa.bicep' = {
  name: 'swa-deployment'
  params: {
    location: location
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

module foundry './modules/foundry-handoff.bicep' = {
  name: 'foundry-handoff-deployment'
  params: {
    location: location
    projectName: projectName
  }
}

output cosmosEndpoint string = cosmos.outputs.cosmosEndpoint
output cosmosAccountName string = cosmos.outputs.cosmosAccountName
output cosmosGremlinEndpoint string = cosmos.outputs.cosmosGremlinEndpoint
output cosmosSqlDb string = cosmos.outputs.sqlDatabaseName
output cosmosGraphDb string = cosmos.outputs.graphDatabaseName
output cosmosGraphName string = cosmos.outputs.graphName

output functionAppName string = functions.outputs.functionAppName
output functionAppUrl string = functions.outputs.functionAppUrl

output staticWebAppName string = swa.outputs.swaName
output staticWebAppUrl string = swa.outputs.swaUrl

output appRegistrationClientId string = graphApp.outputs.appId
output tenantId string = graphApp.outputs.tenantId

output foundryResourceName string = foundry.outputs.foundryResourceName
output foundryResourceId string = foundry.outputs.foundryResourceId
output foundryNote string = foundry.outputs.foundryNote
