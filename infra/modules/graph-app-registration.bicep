extension microsoftGraphV1

param projectName string
param webAppUrl string

var appName = 'app-${projectName}-${uniqueString(resourceGroup().id)}'

resource appRegistration 'Microsoft.Graph/applications@v1.0' = {
  uniqueName: appName
  displayName: appName
  signInAudience: 'AzureADMyOrg'
  requiredResourceAccess: [
    {
      resourceAppId: '00000003-0000-0000-c000-000000000000'
      resourceAccess: [
        {
          id: 'e1fe6dd8-ba31-4d61-89e7-88639da4683d'
          type: 'Scope'
        }
        {
          id: '465a38f9-76ea-45b9-9f34-9e8b0d4b0b42'
          type: 'Scope'
        }
      ]
    }
  ]
  spa: {
    redirectUris: [
      '${webAppUrl}/'
      'http://localhost:5173/'
    ]
  }
}

output appId string = appRegistration.appId
output tenantId string = subscription().tenantId
