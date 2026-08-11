$ErrorActionPreference = "Stop"

function Get-DeploymentOutputValue {
    param(
        [Parameter(Mandatory)] [psobject]$Outputs,
        [Parameter(Mandatory)] [string]$Name,
        [object]$DefaultValue = $null,
        [switch]$Required
    )

    if ($Outputs.PSObject.Properties.Name -contains $Name) {
        return $Outputs.$Name.value
    }
    if ($Required) {
        throw "Deployment output '$Name' is required."
    }
    return $DefaultValue
}

function Get-AzdDeploymentContext {
    param([string]$ResourceGroup = $env:AZURE_RESOURCE_GROUP)

    if ([string]::IsNullOrWhiteSpace($ResourceGroup)) {
        $ResourceGroup = azd env get-value AZURE_RESOURCE_GROUP 2>$null
    }
    if ([string]::IsNullOrWhiteSpace($ResourceGroup)) {
        throw "AZURE_RESOURCE_GROUP is not set. Run this script through azd."
    }

    $deploymentNames = az deployment group list `
        --resource-group $ResourceGroup `
        --query "sort_by([].{name:name,timestamp:properties.timestamp}, &timestamp)[::-1].name" `
        --output json | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to list deployments in resource group '$ResourceGroup'."
    }

    $deploymentName = $null
    $outputs = $null
    foreach ($candidate in $deploymentNames) {
        $candidateOutputs = az deployment group show `
            --resource-group $ResourceGroup `
            --name $candidate `
            --query properties.outputs `
            --output json 2>$null | ConvertFrom-Json
        if ($LASTEXITCODE -eq 0 -and
            $candidateOutputs.PSObject.Properties.Name -contains 'functionAppName' -and
            $candidateOutputs.PSObject.Properties.Name -contains 'foundryProjectResourceId') {
            $deploymentName = $candidate
            $outputs = $candidateOutputs
            break
        }
    }

    if (-not $deploymentName -or -not $outputs) {
        throw "Could not find a root deployment with application outputs in '$ResourceGroup'."
    }

    return [pscustomobject]@{
        RepoRoot = Split-Path -Parent $PSScriptRoot
        ResourceGroup = $ResourceGroup
        DeploymentName = $deploymentName
        FunctionAppName = Get-DeploymentOutputValue $outputs 'functionAppName' -Required
        FunctionAppUrl = Get-DeploymentOutputValue $outputs 'functionAppUrl' -Required
        StaticWebAppName = Get-DeploymentOutputValue $outputs 'staticWebAppName' -Required
        StaticWebAppUrl = Get-DeploymentOutputValue $outputs 'staticWebAppUrl' -Required
        ClientId = Get-DeploymentOutputValue $outputs 'appRegistrationClientId' -Required
        TenantId = Get-DeploymentOutputValue $outputs 'tenantId' -Required
        FoundryResourceName = Get-DeploymentOutputValue $outputs 'foundryResourceName' -Required
        FoundryProjectName = Get-DeploymentOutputValue $outputs 'foundryProjectName' -Required
        FoundryProjectResourceId = Get-DeploymentOutputValue $outputs 'foundryProjectResourceId' -Required
        FoundryProjectEndpoint = Get-DeploymentOutputValue $outputs 'foundryProjectEndpoint' -Required
        CosmosAccountName = Get-DeploymentOutputValue $outputs 'cosmosAccountName' -Required
        CosmosMcpToolkitEnabled = [bool](Get-DeploymentOutputValue $outputs 'cosmosMcpToolkitEnabled' $false)
        CosmosMcpEndpoint = "$(Get-DeploymentOutputValue $outputs 'cosmosMcpEndpoint' '')"
        CosmosMcpClientId = "$(Get-DeploymentOutputValue $outputs 'cosmosMcpClientId' '')"
        CosmosMcpContainerAppUrl = "$(Get-DeploymentOutputValue $outputs 'cosmosMcpContainerAppUrl' '')"
        CosmosMcpContainerAppName = "$(Get-DeploymentOutputValue $outputs 'cosmosMcpContainerAppName' '')"
        CosmosMcpAcrName = "$(Get-DeploymentOutputValue $outputs 'cosmosMcpAcrName' '')"
        CosmosMcpImage = "$(Get-DeploymentOutputValue $outputs 'cosmosMcpImage' '')"
        CosmosMcpImageRepository = "$(Get-DeploymentOutputValue $outputs 'cosmosMcpImageRepository' 'mcp-toolkit')"
        CosmosMcpImageTag = "$(Get-DeploymentOutputValue $outputs 'cosmosMcpImageTag' 'latest')"
    }
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory)] [object]$Value,
        [Parameter(Mandatory)] [string]$Prefix,
        [int]$Depth = 20
    )

    $path = Join-Path $env:TEMP ("$Prefix-$([guid]::NewGuid()).json")
    $Value | ConvertTo-Json -Depth $Depth | Set-Content -Path $path -Encoding utf8
    return $path
}
