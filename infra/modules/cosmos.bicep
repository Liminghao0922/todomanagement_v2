param location string
param projectName string

var accountName = 'cosmos${toLower(projectName)}${uniqueString(resourceGroup().id)}'

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: accountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless'
      }
      {
        name: 'EnableGremlin'
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    publicNetworkAccess: 'Enabled'
  }
}

resource sqlDb 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: cosmos
  name: 'todo-db'
  properties: {
    resource: {
      id: 'todo-db'
    }
  }
}

resource todos 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: sqlDb
  name: 'todos'
  properties: {
    resource: {
      id: 'todos'
      partitionKey: {
        paths: [
          '/owner_id'
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
      }
    }
  }
}

resource owners 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: sqlDb
  name: 'owners'
  properties: {
    resource: {
      id: 'owners'
      partitionKey: {
        paths: [
          '/id'
        ]
        kind: 'Hash'
      }
    }
  }
}

resource projects 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: sqlDb
  name: 'projects'
  properties: {
    resource: {
      id: 'projects'
      partitionKey: {
        paths: [
          '/owner_id'
        ]
        kind: 'Hash'
      }
    }
  }
}

resource gremlinDb 'Microsoft.DocumentDB/databaseAccounts/gremlinDatabases@2024-05-15' = {
  parent: cosmos
  name: 'todo-graph-db'
  properties: {
    resource: {
      id: 'todo-graph-db'
    }
  }
}

resource gremlinGraph 'Microsoft.DocumentDB/databaseAccounts/gremlinDatabases/graphs@2024-05-15' = {
  parent: gremlinDb
  name: 'todo-graph'
  properties: {
    resource: {
      id: 'todo-graph'
      partitionKey: {
        paths: [
          '/owner_id'
        ]
        kind: 'Hash'
      }
    }
  }
}

output cosmosAccountName string = cosmos.name
output cosmosEndpoint string = cosmos.properties.documentEndpoint
output cosmosGremlinEndpoint string = 'wss://${cosmos.name}.gremlin.cosmos.azure.com:443/'
output sqlDatabaseName string = sqlDb.name
output graphDatabaseName string = gremlinDb.name
output graphName string = gremlinGraph.name
