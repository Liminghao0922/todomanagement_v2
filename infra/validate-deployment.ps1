# 部署验证脚本 - 验证所有资源已正确部署

param(
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory = $false)]
    [string]$SubscriptionId
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Green
Write-Host "Azure Infrastructure Validation" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Set subscription if provided
if ($SubscriptionId) {
    az account set --subscription $SubscriptionId
}

$subscription = az account show | ConvertFrom-Json
Write-Host "Subscription: $($subscription.name)" -ForegroundColor Cyan
Write-Host "Resource Group: $ResourceGroupName" -ForegroundColor Cyan
Write-Host ""

# Check if resource group exists
Write-Host "检查资源组..." -ForegroundColor Yellow
$rg = az group show --name $ResourceGroupName 2>$null
if (!$rg) {
    Write-Host "✗ 错误: 资源组不存在" -ForegroundColor Red
    exit 1
}
Write-Host "✓ 资源组存在" -ForegroundColor Green

# Check Virtual Network
Write-Host ""
Write-Host "检查Virtual Network..." -ForegroundColor Yellow
$vnets = az network vnet list --resource-group $ResourceGroupName | ConvertFrom-Json
if ($vnets.Count -eq 0) {
    Write-Host "✗ 警告: 未找到Virtual Network" -ForegroundColor Yellow
} else {
    Write-Host "✓ Virtual Network found: $($vnets[0].name)" -ForegroundColor Green
    Write-Host "  地址范围: $($vnets[0].addressSpace.addressPrefixes[0])"
    Write-Host "  子网数量: $($vnets[0].subnets.Count)"
}

# Check PostgreSQL Server
Write-Host ""
Write-Host "检查PostgreSQL Flexible Server..." -ForegroundColor Yellow
$pgServers = az postgres flexible-server list --resource-group $ResourceGroupName | ConvertFrom-Json
if ($pgServers.Count -eq 0) {
    Write-Host "✗ 警告: 未找到PostgreSQL服务器" -ForegroundColor Yellow
} else {
    $pgServer = $pgServers[0]
    Write-Host "✓ PostgreSQL Server found: $($pgServer.name)" -ForegroundColor Green
    Write-Host "  版本: $($pgServer.version)"
    Write-Host "  SKU: $($pgServer.sku.name)"
    Write-Host "  状态: $($pgServer.state)"
    Write-Host "  完全限定域名: $($pgServer.fullyQualifiedDomainName)"
    
    # Check Entra ID Authentication
    Write-Host "  检查Entra ID认证配置..." -ForegroundColor Cyan
    $authConfig = $pgServer.authConfig
    if ($authConfig.activeDirectoryAuth -eq "Enabled") {
        Write-Host "  ✓ Entra ID认证: 已启用" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Entra ID认证: 未启用" -ForegroundColor Red
    }
    
    # Check Databases
    Write-Host "  数据库:" -ForegroundColor Cyan
    $databases = az postgres flexible-server db list --server-name $pgServer.name --resource-group $ResourceGroupName | ConvertFrom-Json
    foreach ($db in $databases) {
        Write-Host "    - $($db.name)"
    }
}

# Check Azure Container Registry
Write-Host ""
Write-Host "检查Azure Container Registry..." -ForegroundColor Yellow
$registries = az acr list --resource-group $ResourceGroupName | ConvertFrom-Json
if ($registries.Count -eq 0) {
    Write-Host "✗ 警告: 未找到Container Registry" -ForegroundColor Yellow
} else {
    $registry = $registries[0]
    Write-Host "✓ Container Registry found: $($registry.name)" -ForegroundColor Green
    Write-Host "  登录服务器: $($registry.loginServer)"
    Write-Host "  SKU: $($registry.sku.name)"
    Write-Host "  资源ID: $($registry.id)"
}

# Check Container App Environment
Write-Host ""
Write-Host "检查Container App Environment..." -ForegroundColor Yellow
$caEnvs = az containerapp env list --resource-group $ResourceGroupName | ConvertFrom-Json
if ($caEnvs.Count -eq 0) {
    Write-Host "✗ 警告: 未找到Container App Environment" -ForegroundColor Yellow
} else {
    $caEnv = $caEnvs[0]
    Write-Host "✓ Container App Environment found: $($caEnv.name)" -ForegroundColor Green
    Write-Host "  资源ID: $($caEnv.id)"
    Write-Host "  静态IP: $($caEnv.properties.staticIp)"
}

# Check Managed Identities
Write-Host ""
Write-Host "检查托管身份..." -ForegroundColor Yellow
$identities = az identity list --resource-group $ResourceGroupName | ConvertFrom-Json
if ($identities.Count -eq 0) {
    Write-Host "✗ 警告: 未找到托管身份" -ForegroundColor Yellow
} else {
    foreach ($identity in $identities) {
        Write-Host "✓ 托管身份: $($identity.name)" -ForegroundColor Green
        Write-Host "  客户端ID: $($identity.clientId)"
        Write-Host "  主体ID: $($identity.principalId)"
    }
}

# Check Private DNS Zones
Write-Host ""
Write-Host "检查私有DNS区域..." -ForegroundColor Yellow
$dnsZones = az network private-dns zone list --resource-group $ResourceGroupName | ConvertFrom-Json
if ($dnsZones.Count -eq 0) {
    Write-Host "✗ 警告: 未找到私有DNS区域" -ForegroundColor Yellow
} else {
    Write-Host "✓ 私有DNS区域找到:" -ForegroundColor Green
    foreach ($zone in $dnsZones) {
        Write-Host "  - $($zone.name)"
    }
}

# Check RBAC Role Assignments
Write-Host ""
Write-Host "检查RBAC角色分配..." -ForegroundColor Yellow
$roleAssignments = az role assignment list --resource-group $ResourceGroupName | ConvertFrom-Json
if ($roleAssignments.Count -eq 0) {
    Write-Host "✗ 警告: 未找到角色分配" -ForegroundColor Yellow
} else {
    Write-Host "✓ 找到 $($roleAssignments.Count) 个角色分配" -ForegroundColor Green
}

# Check Deployment Status
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

# Generate Summary Report
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "验证总结" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

$resourceCounts = [ordered]@{
    "Virtual Networks" = ($vnets.Count ?? 0)
    "PostgreSQL Servers" = ($pgServers.Count ?? 0)
    "Databases" = ($databases.Count ?? 0)
    "Container Registries" = ($registries.Count ?? 0)
    "Container App Environments" = ($caEnvs.Count ?? 0)
    "Managed Identities" = ($identities.Count ?? 0)
    "Private DNS Zones" = ($dnsZones.Count ?? 0)
    "Role Assignments" = ($roleAssignments.Count ?? 0)
}

foreach ($resource in $resourceCounts.GetEnumerator()) {
    Write-Host "$($resource.Key): $($resource.Value)" -ForegroundColor Cyan
}

# Create summary file
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
Write-Host "1. 配置PostgreSQL Entra ID认证"
Write-Host "2. 启动 API 服务并自动初始化数据库表"
Write-Host "3. 部署Container App并配置Entra ID认证"
Write-Host "4. 测试Container App与PostgreSQL的连接"
Write-Host ""
