# GitHub Variables Setup Script
# This script sets up the required GitHub Variables for Container App deployment

Write-Host "Github Variables Setup" -ForegroundColor Cyan
Write-Host "=====================" -ForegroundColor Cyan
Write-Host ""

# Get deployment outputs
Write-Host "Reading deployment outputs..." -ForegroundColor Yellow
$outputs = az deployment group show `
  --name main `
  --resource-group "rg-todomanagement-dev" `
  --query "properties.outputs" `
  --output json | ConvertFrom-Json

$acrName = $outputs.containerRegistryName.value
$uaiResourceId = $outputs.userAssignedIdentityId.value
$uaiClientId = $outputs.userAssignedIdentityClientId.value
$uaiName = $outputs.userAssignedIdentityName.value
$postgresServer = $outputs.postgresqlServerName.value
$postgresDb = $outputs.databaseName.value
$postgresUser = "your-entra-id-user@postgres"  # Placeholder
$apiProxyTarget = if ($outputs.containerAppApiUrl) { $outputs.containerAppApiUrl.value } else { "https://todomanagement-api.<region>.azurecontainerapps.io" }

Write-Host ""
Write-Host "Required GitHub Variables (use 'gh variable set' to add them):" -ForegroundColor Green
Write-Host ""
Write-Host "1. ACR_NAME"
Write-Host "   Value: $acrName"
Write-Host ""
Write-Host "2. RESOURCE_GROUP"
Write-Host "   Value: rg-todomanagement-dev"
Write-Host ""
Write-Host "3. POSTGRES_SERVER"
Write-Host "   Value: $postgresServer"
Write-Host ""
Write-Host "4. POSTGRES_DB"
Write-Host "   Value: $postgresDb"
Write-Host ""
Write-Host "5. POSTGRES_USER"
Write-Host "   Value: $postgresUser (or update with your Entra ID user)"
Write-Host ""
Write-Host "6. USER_ASSIGNED_IDENTITY_CLIENT_ID"
Write-Host "   Value: $uaiClientId"
Write-Host ""
Write-Host "7. USER_ASSIGNED_IDENTITY_RESOURCE_ID"
Write-Host "   Value: $uaiResourceId"
Write-Host ""
Write-Host "8. USER_ASSIGNED_IDENTITY_NAME"
Write-Host "   Value: $uaiName"
Write-Host ""
Write-Host "9. API_PROXY_TARGET"
Write-Host "   Value: $apiProxyTarget"
Write-Host "   (Web Container App will proxy /api to this internal API URL)"
Write-Host ""
Write-Host "10. AZURE_CLIENT_ID"
Write-Host "   Value: (from your Entra ID app registration)"
Write-Host ""
Write-Host "11. AZURE_TENANT_ID"
Write-Host "   Value: (your Azure tenant ID)"
Write-Host ""
Write-Host "12. AZURE_REDIRECT_URI"
Write-Host "    Value: https://todomanagement-web.<region>.azurecontainerapps.io"
Write-Host "    (Set after Web Container App is deployed)"
Write-Host ""
Write-Host "Quick setup with gh CLI:" -ForegroundColor Green
Write-Host ""
Write-Host "gh variable set ACR_NAME --body ""$acrName"""
Write-Host "gh variable set RESOURCE_GROUP --body ""rg-todomanagement-dev"""
Write-Host "gh variable set POSTGRES_SERVER --body ""$postgresServer"""
Write-Host "gh variable set POSTGRES_DB --body ""$postgresDb"""
Write-Host "gh variable set USER_ASSIGNED_IDENTITY_CLIENT_ID --body ""$uaiClientId"""
Write-Host "gh variable set USER_ASSIGNED_IDENTITY_RESOURCE_ID --body ""$uaiResourceId"""
Write-Host "gh variable set API_PROXY_TARGET --body ""$apiProxyTarget"""
Write-Host ""
