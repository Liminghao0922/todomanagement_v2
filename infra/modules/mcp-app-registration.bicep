extension microsoftGraphV1

param projectName string
param environment string

var appName = 'app-${projectName}-${environment}-mcp-${uniqueString(resourceGroup().id)}'

resource mcpApp 'Microsoft.Graph/applications@v1.0' = {
  uniqueName: appName
  displayName: appName
  signInAudience: 'AzureADMyOrg'
  appRoles: [
    {
      // Deterministic id so redeploys update the same role instead of creating a duplicate.
      id: guid(appName, 'Mcp.Tool.Executor')
      allowedMemberTypes: [
        'User'
        'Application'
      ]
      displayName: 'MCP Tool Executor'
      description: 'Execute Cosmos DB MCP tools'
      value: 'Mcp.Tool.Executor'
      isEnabled: true
    }
  ]
}

resource mcpServicePrincipal 'Microsoft.Graph/servicePrincipals@v1.0' = {
  appId: mcpApp.appId
}

output appId string = mcpApp.appId
output servicePrincipalId string = mcpServicePrincipal.id
output appDisplayName string = mcpApp.displayName
