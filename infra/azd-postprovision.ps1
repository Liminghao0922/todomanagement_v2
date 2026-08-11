param()

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "azd-common.ps1")

$context = Get-AzdDeploymentContext
Write-Host "[azd-postprovision] Resource group: $($context.ResourceGroup)" -ForegroundColor Cyan

function Assert-GraphAccess {
    $output = az ad signed-in-user show --query id --output tsv 2>&1
    if ($LASTEXITCODE -eq 0) {
        return
    }

    $detail = ($output | Out-String).Trim()
    if ($detail -match 'Continuous access evaluation|InteractionRequired|AADSTS') {
        throw "Microsoft Graph access requires re-authentication. Run 'az login --scope https://graph.microsoft.com/.default' and retry. Details: $detail"
    }
    throw "Could not call Microsoft Graph as the signed-in user. Details: $detail"
}

function Set-McpApplicationConfiguration {
    param([Parameter(Mandatory)]$Context)

    if ([string]::IsNullOrWhiteSpace($Context.CosmosMcpClientId) -or
        [string]::IsNullOrWhiteSpace($Context.CosmosMcpContainerAppUrl)) {
        return
    }

    Write-Host "[azd-postprovision] Configuring MCP API permissions and redirect URIs..." -ForegroundColor Yellow
    $appObjectId = az ad app show --id $Context.CosmosMcpClientId --query id --output tsv
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($appObjectId)) {
        throw "Could not resolve MCP app registration object ID."
    }

    $appUrl = "https://graph.microsoft.com/v1.0/applications/$appObjectId"
    $app = az rest --method get --url $appUrl --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read MCP app registration."
    }

    $existingScope = $app.api.oauth2PermissionScopes |
        Where-Object { $_.value -eq "access_as_user" } |
        Select-Object -First 1
    $scopeId = if ($existingScope) { "$($existingScope.id)" } else { [guid]::NewGuid().ToString() }
    $scope = @{
        adminConsentDescription = "Allow access to the Cosmos DB MCP Toolkit API on behalf of the signed-in user."
        adminConsentDisplayName = "Access Cosmos DB MCP Toolkit API"
        id = $scopeId
        isEnabled = $true
        type = "User"
        userConsentDescription = "Allow access to the Cosmos DB MCP Toolkit API on your behalf."
        userConsentDisplayName = "Access Cosmos DB MCP Toolkit API"
        value = "access_as_user"
    }

    $baseUrl = $Context.CosmosMcpContainerAppUrl.TrimEnd('/')
    $body = @{
        identifierUris = @("api://$($Context.CosmosMcpClientId)")
        spa = @{ redirectUris = @("$baseUrl/", "$baseUrl/signin-oidc") }
        web = @{
            implicitGrantSettings = @{
                enableIdTokenIssuance = $true
                enableAccessTokenIssuance = $true
            }
        }
        api = @{
            requestedAccessTokenVersion = 2
            oauth2PermissionScopes = @($scope)
        }
        requiredResourceAccess = @(
            @{
                resourceAppId = $Context.CosmosMcpClientId
                resourceAccess = @(@{ id = $scopeId; type = "Scope" })
            },
            @{
                resourceAppId = "00000003-0000-0000-c000-000000000000"
                resourceAccess = @(@{ id = "e1fe6dd8-ba31-4d61-89e7-88639da4683d"; type = "Scope" })
            }
        )
    }

    $bodyFile = Write-JsonFile $body "mcp-app"
    try {
        az rest --method patch --url $appUrl --headers "Content-Type=application/json" --body "@$bodyFile" --only-show-errors | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to configure the MCP delegated permission scope."
        }

        $body.api.preAuthorizedApplications = @(
            @{
                appId = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"
                delegatedPermissionIds = @($scopeId)
            }
        )
        $body | ConvertTo-Json -Depth 20 | Set-Content -Path $bodyFile -Encoding utf8
        az rest --method patch --url $appUrl --headers "Content-Type=application/json" --body "@$bodyFile" --only-show-errors | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to preauthorize Azure CLI for the MCP delegated permission scope."
        }
    }
    finally {
        Remove-Item $bodyFile -ErrorAction SilentlyContinue
    }
}

function Set-AppRoleAssignment {
    param(
        [Parameter(Mandatory)] [string]$ResourceServicePrincipalId,
        [Parameter(Mandatory)] [string]$PrincipalId,
        [Parameter(Mandatory)] [string]$AppRoleId
    )

    $assignments = az rest `
        --method get `
        --url "https://graph.microsoft.com/v1.0/servicePrincipals/$ResourceServicePrincipalId/appRoleAssignedTo" `
        --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "Could not list MCP application role assignments."
    }

    $exists = @($assignments.value | Where-Object {
        $_.principalId -eq $PrincipalId -and $_.appRoleId -eq $AppRoleId
    }).Count -gt 0
    if ($exists) {
        return
    }

    $bodyFile = Write-JsonFile @{
        principalId = $PrincipalId
        resourceId = $ResourceServicePrincipalId
        appRoleId = $AppRoleId
    } "mcp-role"
    try {
        az rest `
            --method post `
            --url "https://graph.microsoft.com/v1.0/servicePrincipals/$ResourceServicePrincipalId/appRoleAssignedTo" `
            --headers "Content-Type=application/json" `
            --body "@$bodyFile" `
            --only-show-errors | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to assign MCP Tool Executor to principal '$PrincipalId'."
        }
    }
    finally {
        Remove-Item $bodyFile -ErrorAction SilentlyContinue
    }
}

function Set-McpPrincipalsAndConnection {
    param([Parameter(Mandatory)]$Context)

    if ([string]::IsNullOrWhiteSpace($Context.CosmosMcpClientId) -or
        [string]::IsNullOrWhiteSpace($Context.CosmosMcpEndpoint)) {
        return
    }

    $servicePrincipalId = az ad sp show --id $Context.CosmosMcpClientId --query id --output tsv
    $executorRoleId = az ad app show `
        --id $Context.CosmosMcpClientId `
        --query "appRoles[?value=='Mcp.Tool.Executor'].id | [0]" `
        --output tsv
    if ([string]::IsNullOrWhiteSpace($servicePrincipalId) -or [string]::IsNullOrWhiteSpace($executorRoleId)) {
        throw "Could not resolve the MCP service principal or executor role."
    }

    $currentUserId = az ad signed-in-user show --query id --output tsv
    if (-not [string]::IsNullOrWhiteSpace($currentUserId)) {
        Set-AppRoleAssignment $servicePrincipalId $currentUserId $executorRoleId
    }

    $project = az rest `
        --method get `
        --url "https://management.azure.com$($Context.FoundryProjectResourceId)?api-version=2025-06-01" `
        --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace("$($project.identity.principalId)")) {
        throw "Could not resolve the Foundry project managed identity."
    }
    Set-AppRoleAssignment $servicePrincipalId "$($project.identity.principalId)" $executorRoleId

    Write-Host "[azd-postprovision] Configuring Foundry RemoteTool connection..." -ForegroundColor Yellow
    $connectionBody = @{
        properties = @{
            authType = "ProjectManagedIdentity"
            category = "RemoteTool"
            target = $Context.CosmosMcpEndpoint
            audience = $Context.CosmosMcpClientId
            credentials = @{}
            metadata = @{ Audience = $Context.CosmosMcpClientId }
        }
    }
    $connectionFile = Write-JsonFile $connectionBody "foundry-mcp-connection"
    try {
        az rest `
            --method put `
            --url "https://management.azure.com$($Context.FoundryProjectResourceId)/connections/AzureCosmosDB?api-version=2025-06-01" `
            --headers "Content-Type=application/json" `
            --body "@$connectionFile" `
            --only-show-errors | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to configure the Foundry RemoteTool connection."
        }
    }
    finally {
        Remove-Item $connectionFile -ErrorAction SilentlyContinue
    }
}

function Grant-DeployerFoundryManager {
    param([Parameter(Mandatory)]$Context)

    $currentUserId = az ad signed-in-user show --query id --output tsv
    if ([string]::IsNullOrWhiteSpace($currentUserId)) {
        return
    }

    $assignment = az role assignment list `
        --assignee-object-id $currentUserId `
        --scope $Context.FoundryProjectResourceId `
        --role "Foundry Project Manager" `
        --query "[0].id" `
        --output tsv
    if ([string]::IsNullOrWhiteSpace($assignment)) {
        az role assignment create `
            --assignee-object-id $currentUserId `
            --assignee-principal-type User `
            --role "Foundry Project Manager" `
            --scope $Context.FoundryProjectResourceId `
            --only-show-errors | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to grant Foundry Project Manager to the deploying user."
        }
    }
}

function Grant-FunctionCosmosContributor {
    param([Parameter(Mandatory)]$Context)

    Write-Host "[azd-postprovision] Configuring Function Cosmos SQL RBAC..." -ForegroundColor Yellow
    $principalId = az functionapp identity show `
        --name $Context.FunctionAppName `
        --resource-group $Context.ResourceGroup `
        --query principalId `
        --output tsv
    $roleId = '00000000-0000-0000-0000-000000000002'
    $assignments = az cosmosdb sql role assignment list `
        --resource-group $Context.ResourceGroup `
        --account-name $Context.CosmosAccountName `
        --query "[?principalId=='$principalId' && contains(roleDefinitionId, '$roleId')]" `
        --output json | ConvertFrom-Json
    if (-not $assignments -or $assignments.Count -eq 0) {
        $accountId = az cosmosdb show `
            --name $Context.CosmosAccountName `
            --resource-group $Context.ResourceGroup `
            --query id `
            --output tsv
        az cosmosdb sql role assignment create `
            --account-name $Context.CosmosAccountName `
            --resource-group $Context.ResourceGroup `
            --role-definition-id $roleId `
            --scope $accountId `
            --principal-id $principalId `
            --only-show-errors | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to grant Cosmos SQL Data Contributor to the Function identity."
        }
    }
}

Assert-GraphAccess
Set-McpApplicationConfiguration $context
Set-McpPrincipalsAndConnection $context
Grant-DeployerFoundryManager $context
Grant-FunctionCosmosContributor $context

Write-Host "[azd-postprovision] Infrastructure configuration complete." -ForegroundColor Green
Write-Host "Run 'azd deploy' to publish application components." -ForegroundColor Green
