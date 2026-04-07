# 部署验证脚本 - v3 架构 (Functions + SWA + Cosmos + OpenAI/Foundry)

param(
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,

    [Parameter(Mandatory = $false)]
    [string]$SubscriptionId
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Green
Write-Host "Azure Infrastructure Validation (v3)" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

if ($SubscriptionId) {
    az account set --subscription $SubscriptionId
}

$subscription = az account show | ConvertFrom-Json
Write-Host "Subscription: $($subscription.name)" -ForegroundColor Cyan
Write-Host "Resource Group: $ResourceGroupName" -ForegroundColor Cyan
Write-Host ""

# Check resource group
Write-Host "检查资源组..." -ForegroundColor Yellow
$rg = az group show --name $ResourceGroupName 2>$null
if (!$rg) {
    Write-Host "✗ 错误: 资源组不存在" -ForegroundColor Red
    exit 1
}
Write-Host "✓ 资源组存在" -ForegroundColor Green

# Cosmos DB
Write-Host ""
Write-Host "检查 Azure Cosmos DB..." -ForegroundColor Yellow
$cosmosAccounts = az cosmosdb list --resource-group $ResourceGroupName | ConvertFrom-Json
if (!$cosmosAccounts -or $cosmosAccounts.Count -eq 0) {
    Write-Host "✗ 警告: 未找到 Cosmos DB 账户" -ForegroundColor Yellow
} else {
    $cosmos = $cosmosAccounts[0]
    Write-Host "✓ Cosmos DB found: $($cosmos.name)" -ForegroundColor Green
    Write-Host "  Endpoint: $($cosmos.documentEndpoint)"
    Write-Host "  Kind: $($cosmos.kind)"

    $sqlDbs = az cosmosdb sql database list --account-name $cosmos.name --resource-group $ResourceGroupName | ConvertFrom-Json
    if ($sqlDbs -and $sqlDbs.Count -gt 0) {
        Write-Host "  SQL Databases:" -ForegroundColor Cyan
        foreach ($db in $sqlDbs) {
            Write-Host "    - $($db.name)"
        }
    }

    $graphDbs = az cosmosdb gremlin database list --account-name $cosmos.name --resource-group $ResourceGroupName | ConvertFrom-Json
    if ($graphDbs -and $graphDbs.Count -gt 0) {
        Write-Host "  Gremlin Databases:" -ForegroundColor Cyan
        foreach ($gdb in $graphDbs) {
            Write-Host "    - $($gdb.name)"
        }
    }
}

# Function App
Write-Host ""
Write-Host "检查 Azure Functions..." -ForegroundColor Yellow
$functionApps = az functionapp list --resource-group $ResourceGroupName | ConvertFrom-Json
if (!$functionApps -or $functionApps.Count -eq 0) {
    Write-Host "✗ 警告: 未找到 Function App" -ForegroundColor Yellow
} else {
    $func = $functionApps[0]
    Write-Host "✓ Function App found: $($func.name)" -ForegroundColor Green
    Write-Host "  Runtime: $($func.kind)"
    Write-Host "  State: $($func.state)"
    Write-Host "  Host: https://$($func.defaultHostName)"

    $healthUrl = "https://$($func.defaultHostName)/api/health"
    try {
        $healthResponse = Invoke-RestMethod -Method Get -Uri $healthUrl -TimeoutSec 15
        Write-Host "  ✓ Health endpoint reachable: $healthUrl" -ForegroundColor Green
        if ($healthResponse.status) {
            Write-Host "  Health status: $($healthResponse.status)"
        }
    } catch {
        Write-Host "  ⚠ Health endpoint check failed: $healthUrl" -ForegroundColor Yellow
    }
}

# Static Web App
Write-Host ""
Write-Host "检查 Azure Static Web Apps..." -ForegroundColor Yellow
$staticWebApps = az staticwebapp list --resource-group $ResourceGroupName | ConvertFrom-Json
if (!$staticWebApps -or $staticWebApps.Count -eq 0) {
    Write-Host "✗ 警告: 未找到 Static Web App" -ForegroundColor Yellow
} else {
    $swa = $staticWebApps[0]
    Write-Host "✓ Static Web App found: $($swa.name)" -ForegroundColor Green
    if ($swa.defaultHostname) {
        Write-Host "  URL: https://$($swa.defaultHostname)"
    }
    Write-Host "  SKU: $($swa.sku.name)"
}

# Azure OpenAI / AI Services (Foundry handoff resource)
Write-Host ""
Write-Host "检查 Azure OpenAI / AI Services..." -ForegroundColor Yellow
$cognitiveAccounts = az cognitiveservices account list --resource-group $ResourceGroupName | ConvertFrom-Json
if (!$cognitiveAccounts -or $cognitiveAccounts.Count -eq 0) {
    Write-Host "✗ 警告: 未找到 Cognitive Services 资源" -ForegroundColor Yellow
} else {
    foreach ($account in $cognitiveAccounts) {
        Write-Host "✓ Cognitive resource: $($account.name)" -ForegroundColor Green
        Write-Host "  Kind: $($account.kind)"
        Write-Host "  Endpoint: $($account.properties.endpoint)"
    }
}

# Entra app registrations cannot be fully validated by RG scope, so we only provide a reminder.
Write-Host ""
Write-Host "提示: Entra App Registration 请在 Portal 中确认 Redirect URI 与 API 权限。" -ForegroundColor Cyan

# Deployment status
Write-Host ""
Write-Host "检查最后的部署状态..." -ForegroundColor Yellow
$deployments = az deployment group list --resource-group $ResourceGroupName --query "[0]" | ConvertFrom-Json
if ($deployments) {
    Write-Host "✓ 最后部署时间: $($deployments.properties.timestamp)" -ForegroundColor Green
    Write-Host "  部署名称: $($deployments.name)"
    Write-Host "  部署状态: $($deployments.properties.provisioningState)"

    if ($deployments.properties.provisioningState -eq "Succeeded") {
        Write-Host "  ✓ 部署成功" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ 部署状态: $($deployments.properties.provisioningState)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "验证总结" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

$resourceCounts = [ordered]@{
    "Cosmos DB Accounts" = ($cosmosAccounts.Count ?? 0)
    "Function Apps" = ($functionApps.Count ?? 0)
    "Static Web Apps" = ($staticWebApps.Count ?? 0)
    "Cognitive Services" = ($cognitiveAccounts.Count ?? 0)
}

foreach ($resource in $resourceCounts.GetEnumerator()) {
    Write-Host "$($resource.Key): $($resource.Value)" -ForegroundColor Cyan
}

$summary = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    subscriptionId = $subscription.id
    subscriptionName = $subscription.name
    resourceGroup = $ResourceGroupName
    resources = $resourceCounts
    deploymentStatus = $deployments.properties.provisioningState
}

$summary | ConvertTo-Json | Out-File -FilePath "validation-report.json" -Encoding UTF8
Write-Host ""
Write-Host "✓ 验证报告已保存到: validation-report.json" -ForegroundColor Green
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "后续步骤" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "1. 运行 Function 与 SWA 的端到端联调"
Write-Host "2. 在 Foundry 中完成 Agent 与工具绑定"
Write-Host "3. 验证日历扫描定时任务与自动建 Todo 流程"
Write-Host ""
