# Azure Infrastructure Deployment Script for Todo Management v3 (PowerShell)
# This script deploys Functions + SWA + Cosmos + Foundry-ready resources.

param(
    [Parameter(Mandatory = $false)]
    [string]$ResourceGroupName = "rg-todomanagement-dev",
    
    [Parameter(Mandatory = $false)]
    [string]$Location = "japaneast",
    
    [Parameter(Mandatory = $false)]
    [string]$Environment = "dev"
)

# Set error action
$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Green
Write-Host "Azure Infrastructure Deployment (v3)" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Check if user is logged in
Write-Host "[0/3] Checking Azure authentication..." -ForegroundColor Yellow
$currentUser = az account show 2>$null
if (-not $currentUser) {
    Write-Host ""
    Write-Host "Not logged in. Please run: az login" -ForegroundColor Red
    Write-Host ""
    Write-Host "To log in, use:" -ForegroundColor Yellow
    Write-Host "  az login" -ForegroundColor Cyan
    exit 1
}

# Get and display current subscription
$subscription = $currentUser | ConvertFrom-Json
Write-Host "Logged in as: $($subscription.user.name)" -ForegroundColor Green
Write-Host ""
Write-Host "Current subscription:" -ForegroundColor Cyan
Write-Host "  Name: $($subscription.name)" -ForegroundColor Cyan
Write-Host "  ID:   $($subscription.id)" -ForegroundColor Cyan
Write-Host ""

# Ask user to confirm subscription
$confirmSub = Read-Host "Confirm using this subscription? (y/n, default y)"
if ($confirmSub -eq "n") {
    Write-Host ""
    Write-Host "To switch subscriptions:" -ForegroundColor Yellow
    Write-Host "  1. List all subscriptions: az account list --output table" -ForegroundColor Cyan
    Write-Host "  2. Select subscription: az account set --subscription <subscription-id>"  -ForegroundColor Cyan
    Write-Host ""
    exit 0
}

Write-Host ""
Write-Host "Deployment Configuration:" -ForegroundColor Cyan
Write-Host "  Resource Group: $ResourceGroupName" -ForegroundColor Cyan
Write-Host "  Location:       $Location" -ForegroundColor Cyan
Write-Host "  Environment:    $Environment" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create Resource Group
Write-Host "[1/3] Creating Resource Group..." -ForegroundColor Yellow
az group create --name $ResourceGroupName --location $Location
Write-Host "Resource Group created: $ResourceGroupName" -ForegroundColor Green
Write-Host ""

# Step 2: Deploy main infrastructure
Write-Host "[2/3] Deploying infrastructure..." -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyyMMddHHmmss"
$deploymentName = "infra-v3-deployment-$timestamp"

az deployment group create `
    --name $deploymentName `
    --resource-group $ResourceGroupName `
    --template-file "main.bicep" `
    --parameters parameters.json location=$Location environment=$Environment

Write-Host "Infrastructure deployed" -ForegroundColor Green
Write-Host ""

# Step 3: Retrieve deployment outputs
Write-Host "[3/3] Retrieving deployment outputs..." -ForegroundColor Yellow

$outputsJson = az deployment group show `
    --name $deploymentName `
    --resource-group $ResourceGroupName `
    --query "properties.outputs" `
    -o json

if (-not $outputsJson -or $outputsJson -eq "null") {
    throw "Failed to retrieve deployment outputs for deployment '$deploymentName'."
}

$outputs = $outputsJson | ConvertFrom-Json

Write-Host "Deployment successful!" -ForegroundColor Green
Write-Host ""

Write-Host "==========================================" -ForegroundColor Green
Write-Host "Infrastructure Details" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Function App: $($outputs.functionAppName.value)"
Write-Host "Function URL: $($outputs.functionAppUrl.value)"
Write-Host "Static Web App: $($outputs.staticWebAppName.value)"
Write-Host "Static Web URL: $($outputs.staticWebAppUrl.value)"
Write-Host "Cosmos Account: $($outputs.cosmosAccountName.value)"
Write-Host "Cosmos Endpoint: $($outputs.cosmosEndpoint.value)"
Write-Host "Cosmos SQL DB: $($outputs.cosmosSqlDb.value)"
Write-Host "Cosmos Graph: $($outputs.cosmosGraphDb.value)/$($outputs.cosmosGraphName.value)"
Write-Host ""
Write-Host "Entra App Registration:" -ForegroundColor Cyan
Write-Host "  CLIENT_ID: $($outputs.appRegistrationClientId.value)"
Write-Host "  TENANT_ID: $($outputs.tenantId.value)"

Write-Host "Foundry:" -ForegroundColor Cyan
Write-Host "  RESOURCE_NAME: $($outputs.foundryResourceName.value)"
Write-Host "  RESOURCE_ID: $($outputs.foundryResourceId.value)"
Write-Host "  NOTE: $($outputs.foundryNote.value)"
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Configure Foundry Agent in Azure AI Foundry Web UI"
Write-Host "  2. Wire Foundry built-in tools (Graph + Cosmos)"
Write-Host "  3. Add custom tool endpoint: /api/tools/extract-action-items"
Write-Host ""
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Deployment Completed!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
