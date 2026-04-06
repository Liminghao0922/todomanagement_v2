// Module: Configure User Assigned Identity as PostgreSQL Entra Admin
// This module is separate because Bicep BCP120 prevents using runtime principalId
// directly as a resource name in the parent template. By passing it as a parameter,
// the constraint is satisfied within the module scope.

param postgresServerName string
param principalId string   // UAI Object ID (OID) - the actual Entra object ID
param principalName string  // UAI display name
param tenantId string

resource postgresqlServer 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' existing = {
  name: postgresServerName
}

resource postgresAdmin 'Microsoft.DBforPostgreSQL/flexibleServers/administrators@2024-08-01' = {
  parent: postgresqlServer
  name: principalId
  properties: {
    principalType: 'ServicePrincipal'
    tenantId: tenantId
    principalName: principalName
  }
}
