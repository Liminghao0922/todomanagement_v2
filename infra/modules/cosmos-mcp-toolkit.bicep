param location string
param projectName string
param cosmosAccountName string
param foundryEndpoint string
param tenantId string
param mcpImage string
param mcpClientId string
param mcpAudience string = ''
param containerAppName string = ''
param containerAppEnvironmentName string = ''
param logAnalyticsWorkspaceName string = ''
param cpu string = '0.5'
param memory string = '1Gi'
param registryServer string = ''
param useManagedIdentityForRegistry bool = false
param managedIdentityResourceId string
param managedIdentityClientId string
param managedIdentityPrincipalId string

// Container Apps names are limited to 32 characters.
var nameSuffix = take(uniqueString(resourceGroup().id), 6)
var shortProject = take(toLower(replace(replace(projectName, '-', ''), '_', '')), 12)
var effectiveContainerAppName = empty(containerAppName) ? 'mcp-${shortProject}-${nameSuffix}' : containerAppName
var effectiveEnvironmentName = empty(containerAppEnvironmentName) ? 'cae-${shortProject}-${nameSuffix}' : containerAppEnvironmentName
var effectiveWorkspaceName = empty(logAnalyticsWorkspaceName) ? 'log-${shortProject}-mcp-${nameSuffix}' : logAnalyticsWorkspaceName
var effectiveAudience = empty(mcpAudience) ? mcpClientId : mcpAudience

resource workspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: effectiveWorkspaceName
  location: location
  properties: {
    retentionInDays: 30
  }
}

resource managedEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: effectiveEnvironmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: workspace.properties.customerId
        sharedKey: workspace.listKeys().primarySharedKey
      }
    }
  }
}

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: effectiveContainerAppName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentityResourceId}': {}
    }
  }
  properties: {
    managedEnvironmentId: managedEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
      }
      registries: useManagedIdentityForRegistry && !empty(registryServer) ? [
        {
          server: registryServer
          identity: managedIdentityResourceId
        }
      ] : []
    }
    template: {
      containers: [
        {
          name: 'mcp-toolkit'
          image: mcpImage
          env: [
            {
              name: 'AZURE_CLIENT_ID'
              value: managedIdentityClientId
            }
            {
              name: 'AzureAd__ClientId'
              value: mcpClientId
            }
            {
              name: 'AzureAd__TenantId'
              value: tenantId
            }
            {
              name: 'AzureAd__Audience'
              value: effectiveAudience
            }
            {
              name: 'COSMOS_ENDPOINT'
              value: 'https://${cosmosAccountName}.documents.azure.com:443/'
            }
            {
              name: 'OPENAI_ENDPOINT'
              value: foundryEndpoint
            }
            {
              name: 'OPENAI_EMBEDDING_DEPLOYMENT'
              value: 'text-embedding-3-small'
            }
            {
              name: 'ASPNETCORE_ENVIRONMENT'
              value: 'Production'
            }
            {
              name: 'ASPNETCORE_URLS'
              value: 'http://+:8080'
            }
          ]
          resources: {
            cpu: json(cpu)
            memory: memory
          }
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: cosmosAccountName
}

resource cosmosSqlContributorRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, effectiveContainerAppName, 'mcp-sql-contributor')
  properties: {
    principalId: managedIdentityPrincipalId
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    scope: cosmosAccount.id
  }
}

resource cosmosAccountReaderRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(cosmosAccount.id, effectiveContainerAppName, 'mcp-account-reader')
  scope: cosmosAccount
  properties: {
    principalId: managedIdentityPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'fbdf93bf-df7d-467e-a4d2-9458aa1360c8')
  }
}

output containerAppName string = containerApp.name
output containerAppUrl string = 'https://${containerApp.properties.configuration.ingress.fqdn}'
output mcpEndpoint string = 'https://${containerApp.properties.configuration.ingress.fqdn}/mcp'
output environmentName string = managedEnvironment.name
output principalId string = managedIdentityPrincipalId
