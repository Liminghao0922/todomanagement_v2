param()

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "azd-common.ps1")

$context = Get-AzdDeploymentContext
Write-Host "[azd-deploy] Resource group: $($context.ResourceGroup)" -ForegroundColor Cyan

function Publish-CosmosMcpImage {
    param([Parameter(Mandatory)]$Context)

    if (-not $Context.CosmosMcpToolkitEnabled -or
        [string]::IsNullOrWhiteSpace($Context.CosmosMcpAcrName) -or
        [string]::IsNullOrWhiteSpace($Context.CosmosMcpContainerAppName) -or
        [string]::IsNullOrWhiteSpace($Context.CosmosMcpImage)) {
        return
    }

    $imageExists = az acr repository show-tags `
        --name $Context.CosmosMcpAcrName `
        --repository $Context.CosmosMcpImageRepository `
        --query "contains(@, '$($Context.CosmosMcpImageTag)')" `
        --output tsv 2>$null

    if ($imageExists -ne "true") {
        Write-Host "[azd-deploy] Building Cosmos MCP Toolkit image in ACR..." -ForegroundColor Yellow
        Push-Location $PSScriptRoot
        try {
            $queuedAt = [DateTimeOffset]::UtcNow
            az acr build `
                --registry $Context.CosmosMcpAcrName `
                --image "$($Context.CosmosMcpImageRepository):$($Context.CosmosMcpImageTag)" `
                --file "Dockerfile.mcp-toolkit" `
                --platform linux/amd64 `
                --no-wait `
                --no-logs `
                --output none `
                .
            if ($LASTEXITCODE -ne 0) {
                throw "Failed to queue the ACR build."
            }

            $runId = ""
            $lookupDeadline = [DateTimeOffset]::UtcNow.AddMinutes(2)
            do {
                $runs = az acr task list-runs `
                    --registry $Context.CosmosMcpAcrName `
                    --image "$($Context.CosmosMcpImageRepository):$($Context.CosmosMcpImageTag)" `
                    --top 5 `
                    --output json 2>$null | ConvertFrom-Json
                if ($LASTEXITCODE -eq 0) {
                    $run = $runs | Where-Object {
                        $_.createTime -and ([DateTimeOffset]::Parse("$($_.createTime)") -ge $queuedAt.AddSeconds(-5))
                    } | Sort-Object { [DateTimeOffset]::Parse("$($_.createTime)") } -Descending | Select-Object -First 1
                    if ($run) {
                        $runId = "$($run.runId)"
                    }
                }
                if ([string]::IsNullOrWhiteSpace($runId)) {
                    Start-Sleep -Seconds 5
                }
            } while ([string]::IsNullOrWhiteSpace($runId) -and [DateTimeOffset]::UtcNow -lt $lookupDeadline)

            if ([string]::IsNullOrWhiteSpace($runId)) {
                throw "The ACR build was queued, but its run ID could not be discovered."
            }

            $buildDeadline = [DateTimeOffset]::UtcNow.AddMinutes(20)
            do {
                $status = az acr task show-run `
                    --registry $Context.CosmosMcpAcrName `
                    --run-id $runId `
                    --query status `
                    --output tsv
                if ($LASTEXITCODE -ne 0) {
                    throw "Failed to read ACR build '$runId' status."
                }
                if ($status -in @("Failed", "Canceled", "Error", "Timeout")) {
                    throw "ACR build '$runId' ended with status '$status'."
                }
                if ($status -ne "Succeeded") {
                    Start-Sleep -Seconds 10
                }
            } while ($status -ne "Succeeded" -and [DateTimeOffset]::UtcNow -lt $buildDeadline)

            if ($status -ne "Succeeded") {
                throw "Timed out waiting for ACR build '$runId'."
            }
        }
        finally {
            Pop-Location
        }
    }

    Write-Host "[azd-deploy] Activating MCP image: $($Context.CosmosMcpImage)" -ForegroundColor Yellow
    az containerapp update `
        --resource-group $Context.ResourceGroup `
        --name $Context.CosmosMcpContainerAppName `
        --image $Context.CosmosMcpImage `
        --only-show-errors | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to activate the MCP Toolkit image."
    }
}

function Get-AgentConfiguration {
    param([Parameter(Mandatory)] [string]$Path)

    $configuration = [ordered]@{
        Name = "todomanagement-agent"
        Model = "gpt-5.4-mini"
        Description = ""
        Instructions = "You are a helpful assistant."
    }
    if (-not (Test-Path $Path)) {
        return [pscustomobject]$configuration
    }

    $file = Get-Content -Path $Path -Raw | ConvertFrom-Json
    if (-not [string]::IsNullOrWhiteSpace($file.name)) { $configuration.Name = $file.name.Trim() }
    if (-not [string]::IsNullOrWhiteSpace($file.model)) { $configuration.Model = $file.model.Trim() }
    if (-not [string]::IsNullOrWhiteSpace($file.description)) { $configuration.Description = $file.description.Trim() }
    if ($file.instructions -is [System.Array]) {
        $configuration.Instructions = (($file.instructions | ForEach-Object { "$($_.Trim())" }) -join "`n").Trim()
    }
    elseif ($file.instructions) {
        $configuration.Instructions = "$($file.instructions)".Trim()
    }
    return [pscustomobject]$configuration
}

function Publish-FoundryAgent {
    param(
        [Parameter(Mandatory)]$Context,
        [Parameter(Mandatory)]$Configuration
    )

    Write-Host "[azd-deploy] Creating or updating Foundry agent '$($Configuration.Name)'..." -ForegroundColor Yellow
    $baseUrl = $Context.FoundryProjectEndpoint.TrimEnd('/') + "/agents"
    $apiVersion = "2025-05-15-preview"
    $lookupDeadline = [DateTimeOffset]::UtcNow.AddMinutes(10)
    do {
        $lookupOutput = az rest `
            --resource "https://ai.azure.com" `
            --method get `
            --url "$baseUrl/$($Configuration.Name)?api-version=$apiVersion" `
            --output json 2>&1
        $agentExists = $LASTEXITCODE -eq 0
        if ($agentExists) {
            break
        }

        $lookupDetail = ($lookupOutput | Out-String).Trim()
        $agentMissing = $lookupDetail -match "(?i)agent.*(not found|does not exist|doesn't exist)"
        if ($agentMissing) {
            break
        }

        $projectPending = $lookupDetail -match '(?i)project not found'
        if (-not $projectPending) {
            throw "Could not query Foundry agent '$($Configuration.Name)'. Details: $lookupDetail"
        }
        if ([DateTimeOffset]::UtcNow -lt $lookupDeadline) {
            Start-Sleep -Seconds 15
        }
    } while ([DateTimeOffset]::UtcNow -lt $lookupDeadline)

    if (-not $agentExists -and -not $agentMissing) {
        throw "Foundry project '$($Context.FoundryProjectEndpoint)' was not discoverable within 10 minutes. Last error: $lookupDetail"
    }

    $definition = @{
        kind = "prompt"
        model = $Configuration.Model
        instructions = $Configuration.Instructions
    }
    if (-not [string]::IsNullOrWhiteSpace($Context.CosmosMcpEndpoint)) {
        $definition.tools = @(
            @{
                type = "mcp"
                server_label = "AzureCosmosDB"
                server_url = $Context.CosmosMcpEndpoint
                project_connection_id = "AzureCosmosDB"
                headers = @{}
                require_approval = "never"
            }
        )
    }

    $body = @{ definition = $definition }
    if (-not [string]::IsNullOrWhiteSpace($Configuration.Description)) {
        $body.description = $Configuration.Description
    }
    if (-not $agentExists) {
        $body.name = $Configuration.Name
    }

    $bodyFile = Write-JsonFile $body "foundry-agent" 30
    try {
        $url = if ($agentExists) {
            "$baseUrl/$($Configuration.Name)/versions?api-version=$apiVersion"
        }
        else {
            "$baseUrl`?api-version=$apiVersion"
        }
        $deadline = [DateTimeOffset]::UtcNow.AddMinutes(10)
        $lastError = ""
        do {
            $output = az rest `
                --resource "https://ai.azure.com" `
                --method post `
                --url $url `
                --headers "Content-Type=application/json" `
                --body "@$bodyFile" `
                --output json 2>&1
            $published = $LASTEXITCODE -eq 0
            if (-not $published) {
                $lastError = ($output | Out-String).Trim()
                $retryable = $lastError -match '(?i)(408|429|5\d\d|timeout|temporar|connection reset|service unavailable)'
                if (-not $retryable) {
                    throw "Failed to publish Foundry agent '$($Configuration.Name)'. Details: $lastError"
                }
                Start-Sleep -Seconds 15
            }
        } while (-not $published -and [DateTimeOffset]::UtcNow -lt $deadline)

        if (-not $published) {
            throw "Foundry agent '$($Configuration.Name)' could not be published within 10 minutes. Last error: $lastError"
        }
        return $output | ConvertFrom-Json
    }
    finally {
        Remove-Item $bodyFile -ErrorAction SilentlyContinue
    }
}

function Set-FunctionRuntimeSettings {
    param(
        [Parameter(Mandatory)]$Context,
        [Parameter(Mandatory)]$Configuration
    )

    Write-Host "[azd-deploy] Updating Function App runtime settings..." -ForegroundColor Yellow
    $settings = @(
        "COSMOS_AUTH_MODE=aad",
        "FOUNDRY_PROJECT_ENDPOINT=$($Context.FoundryProjectEndpoint)",
        "FOUNDRY_AGENT_ENDPOINT=$($Context.FoundryProjectEndpoint)",
        "FOUNDRY_AGENT_NAME=$($Configuration.Name)",
        "FOUNDRY_AGENT_MODEL=$($Configuration.Model)"
    )
    az functionapp config appsettings set `
        --name $Context.FunctionAppName `
        --resource-group $Context.ResourceGroup `
        --settings $settings `
        --only-show-errors | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to update Function App runtime settings."
    }

    az functionapp config appsettings delete `
        --name $Context.FunctionAppName `
        --resource-group $Context.ResourceGroup `
        --setting-names COSMOS_KEY FOUNDRY_AGENT_VERSION FOUNDRY_ASSISTANT_ID `
        --only-show-errors | Out-Null
}

function Publish-FunctionApplication {
    param([Parameter(Mandatory)]$Context)

    Write-Host "[azd-deploy] Publishing Functions API..." -ForegroundColor Yellow
    $sourcePath = Join-Path $Context.RepoRoot "src/api"
    $packagePath = Join-Path $env:TEMP ("todomanagement-functions-$([guid]::NewGuid()).zip")
    try {
        Compress-Archive -Path @(
            (Join-Path $sourcePath "function_app.py"),
            (Join-Path $sourcePath "host.json"),
            (Join-Path $sourcePath "requirements.txt"),
            (Join-Path $sourcePath "functions"),
            (Join-Path $sourcePath "services")
        ) -DestinationPath $packagePath -CompressionLevel Optimal

        az functionapp deployment source config-zip `
            --name $Context.FunctionAppName `
            --resource-group $Context.ResourceGroup `
            --src $packagePath `
            --build-remote true `
            --timeout 1800 `
            --only-show-errors | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Function OneDeploy failed. Verify deployment-storage private connectivity and publish again."
        }

        $indexDeadline = [DateTimeOffset]::UtcNow.AddMinutes(5)
        do {
            $functionCount = @(az functionapp function list `
                --name $Context.FunctionAppName `
                --resource-group $Context.ResourceGroup `
                --output json | ConvertFrom-Json).Count
            if ($functionCount -eq 0 -and [DateTimeOffset]::UtcNow -lt $indexDeadline) {
                Start-Sleep -Seconds 10
            }
        } while ($functionCount -eq 0 -and [DateTimeOffset]::UtcNow -lt $indexDeadline)

        if ($functionCount -eq 0) {
            throw "Function deployment completed, but no functions were indexed. Check Python import and startup errors."
        }
    }
    finally {
        Remove-Item $packagePath -ErrorAction SilentlyContinue
    }
}

function Publish-StaticWebApplication {
    param([Parameter(Mandatory)]$Context)

    Write-Host "[azd-deploy] Building and deploying Static Web App..." -ForegroundColor Yellow
    Push-Location (Join-Path $Context.RepoRoot "src/web")
    try {
        $env:VITE_AZURE_CLIENT_ID = $Context.ClientId
        $env:VITE_AZURE_AUTHORITY = "https://login.microsoftonline.com/$($Context.TenantId)"
        $env:VITE_AZURE_REDIRECT_URI = $Context.StaticWebAppUrl
        npm ci
        if ($LASTEXITCODE -ne 0) { throw "npm ci failed." }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
        Copy-Item staticwebapp.config.json dist\staticwebapp.config.json -Force

        $token = az staticwebapp secrets list `
            --name $Context.StaticWebAppName `
            --resource-group $Context.ResourceGroup `
            --query "properties.apiKey" `
            --output tsv
        if ([string]::IsNullOrWhiteSpace($token)) {
            throw "Could not retrieve the Static Web Apps deployment token."
        }
        npx --yes @azure/static-web-apps-cli@latest deploy .\dist --env production --deployment-token $token
        if ($LASTEXITCODE -ne 0) { throw "Static Web App deployment failed." }
    }
    finally {
        Remove-Item Env:VITE_AZURE_CLIENT_ID -ErrorAction SilentlyContinue
        Remove-Item Env:VITE_AZURE_AUTHORITY -ErrorAction SilentlyContinue
        Remove-Item Env:VITE_AZURE_REDIRECT_URI -ErrorAction SilentlyContinue
        Pop-Location
    }
}

function Set-StaticWebAppBackend {
    param([Parameter(Mandatory)]$Context)

    Write-Host "[azd-deploy] Linking Static Web App to Function App..." -ForegroundColor Yellow
    $function = az functionapp show `
        --name $Context.FunctionAppName `
        --resource-group $Context.ResourceGroup `
        --output json | ConvertFrom-Json
    az staticwebapp backends link `
        --name $Context.StaticWebAppName `
        --resource-group $Context.ResourceGroup `
        --backend-resource-id $function.id `
        --backend-region $function.location `
        --only-show-errors | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Automatic SWA API link failed; link '$($Context.FunctionAppName)' manually."
    }
}

function Test-DeploymentHealth {
    param([Parameter(Mandatory)]$Context)

    Write-Host "[azd-deploy] Validating health endpoints..." -ForegroundColor Yellow
    foreach ($url in @("$($Context.FunctionAppUrl)/api/health", "$($Context.StaticWebAppUrl)/api/health")) {
        try {
            Invoke-RestMethod $url -TimeoutSec 60 | ConvertTo-Json -Depth 5
        }
        catch {
            Write-Warning "Health endpoint did not respond: $url"
        }
    }
}

$configuration = Get-AgentConfiguration (Join-Path $context.RepoRoot "foundry-agent-config.json")
Publish-CosmosMcpImage $context
$null = Publish-FoundryAgent $context $configuration
Set-FunctionRuntimeSettings $context $configuration
Publish-FunctionApplication $context
Publish-StaticWebApplication $context
Set-StaticWebAppBackend $context
Test-DeploymentHealth $context

Write-Host "[azd-deploy] Application deployment complete." -ForegroundColor Green
Write-Host "Todo app URL: $($context.StaticWebAppUrl)" -ForegroundColor Green
Write-Host "Function URL: $($context.FunctionAppUrl)" -ForegroundColor Green
Write-Host "Foundry project endpoint: $($context.FoundryProjectEndpoint)" -ForegroundColor Green
if ($context.CosmosMcpToolkitEnabled) {
    Write-Host "Cosmos MCP endpoint: $($context.CosmosMcpEndpoint)" -ForegroundColor Green
}
