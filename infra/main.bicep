// TailorMade Azure resources (placeholder).
// Resources to add, in deploy order:
//   1. Storage account          - blobs (raw-crawls, resumes) + queue (jobs-to-process)
//   2. Log Analytics + Application Insights
//   3. Key Vault                - Adzuna key, SQL connection string, OpenAI key
//   4. Azure SQL server + database (free offer, serverless)
//   5. SignalR Service (Free, serverless mode)
//   6. Function App (worker, Python, Flex Consumption) with managed identity
//   7. Static Web App (Free) for frontend/ + api/
//   8. Azure OpenAI account + gpt-4o-mini deployment

targetScope = 'resourceGroup'

@description('Short name used as a prefix for every resource')
param appName string = 'tailormade'

param location string = resourceGroup().location

var suffix = uniqueString(resourceGroup().id)

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: toLower('${appName}${take(suffix, 8)}')
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

output storageAccountName string = storage.name
