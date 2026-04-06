param location string
param projectName string

var swaName = 'swa-${projectName}-${uniqueString(resourceGroup().id)}'

resource swa 'Microsoft.Web/staticSites@2023-01-01' = {
  name: swaName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {}
}

output swaName string = swa.name
output swaUrl string = 'https://${swa.properties.defaultHostname}'
