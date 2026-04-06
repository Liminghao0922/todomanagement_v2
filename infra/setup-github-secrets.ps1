# Setup GitHub Secrets for ACR Integration
# This script helps you get ACR credentials and instructions for setting up GitHub Secrets

param(
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory = $true)]
    [string]$AcrName,
    
    [Parameter(Mandatory = $false)]
    [string]$ServicePrincipalName = "github-acr-push"
)

Write-Host "========================================" -ForegroundColor Green
Write-Host "ACR GitHub Integration Setup" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Get ACR Login Server
Write-Host "[1/4] Getting ACR Login Server..." -ForegroundColor Yellow
$acr = az acr show --resource-group $ResourceGroupName --name $AcrName | ConvertFrom-Json
$loginServer = $acr.properties.loginServer
Write-Host "ACR Login Server: $loginServer" -ForegroundColor Cyan
Write-Host ""

# Option 1: Enable ACR Admin User
Write-Host "[2/4] Enabling ACR Admin User (Simple Option)..." -ForegroundColor Yellow
az acr update --resource-group $ResourceGroupName --name $AcrName --admin-enabled true
$credentials = az acr credential show --resource-group $ResourceGroupName --name $AcrName | ConvertFrom-Json
$adminUsername = $credentials.username
$adminPassword = $credentials.passwords[0].value

Write-Host "Admin Credentials:" -ForegroundColor Cyan
Write-Host "  Username: $adminUsername" -ForegroundColor Cyan
Write-Host "  Password: (hidden for security)" -ForegroundColor Cyan
Write-Host ""

# Option 2: Create Service Principal (More Secure)
Write-Host "[3/4] Creating Service Principal (Recommended)..." -ForegroundColor Yellow
$subscription = az account show | ConvertFrom-Json
$subscriptionId = $subscription.id
$acrResourceId = "/subscriptions/$subscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.ContainerRegistry/registries/$AcrName"

# Check if SP already exists
$existingSp = az ad sp list --display-name $ServicePrincipalName --query "[0]" 2>$null | ConvertFrom-Json
if ($existingSp.id) {
    Write-Host "Service Principal already exists: $($existingSp.displayName)" -ForegroundColor Green
    $spId = $existingSp.appId
    
    # Reset password
    Write-Host "Resetting Service Principal password..." -ForegroundColor Yellow
    $spPassword = az ad app credential reset --id $existingSp.appId --display-name "github-push" --query "password" -o tsv
} else {
    # Create new SP with AcrPush role
    Write-Host "Creating new Service Principal..." -ForegroundColor Yellow
    $sp = az ad sp create-for-rbac `
        --name $ServicePrincipalName `
        --role "AcrPush" `
        --scopes $acrResourceId | ConvertFrom-Json
    
    $spId = $sp.appId
    $spPassword = $sp.password
}

Write-Host "Service Principal:" -ForegroundColor Cyan
Write-Host "  ID (Username): $spId" -ForegroundColor Cyan
Write-Host "  Password: (hidden for security)" -ForegroundColor Cyan
Write-Host ""

# Display GitHub Secrets Instructions
Write-Host "[4/4] GitHub Secrets Configuration" -ForegroundColor Yellow
Write-Host ""
Write-Host "Add these secrets to your GitHub repository:" -ForegroundColor Green
Write-Host "  Repository → Settings → Secrets and variables → Actions" -ForegroundColor Cyan
Write-Host ""
Write-Host "Secret 1: REGISTRY_LOGIN_SERVER" -ForegroundColor Yellow
Write-Host "  Value: $loginServer" -ForegroundColor Cyan
Write-Host ""
Write-Host "Secret 2: REGISTRY_USERNAME (Option A - Admin User)" -ForegroundColor Yellow
Write-Host "  Value: $adminUsername" -ForegroundColor Cyan
Write-Host ""
Write-Host "Secret 3: REGISTRY_PASSWORD (Option A - Admin User)" -ForegroundColor Yellow
Write-Host "  Value: $adminPassword" -ForegroundColor Cyan
Write-Host ""
Write-Host "OR" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Secret 2: REGISTRY_USERNAME (Option B - Service Principal)" -ForegroundColor Yellow
Write-Host "  Value: $spId" -ForegroundColor Cyan
Write-Host ""
Write-Host "Secret 3: REGISTRY_PASSWORD (Option B - Service Principal)" -ForegroundColor Yellow
Write-Host "  Value: (copy the password from above output)" -ForegroundColor Cyan
Write-Host ""

# Copy to clipboard
Write-Host "Creating clipboard content..." -ForegroundColor Yellow
$clipboardContent = @"
GitHub Secrets for ACR Integration:

REGISTRY_LOGIN_SERVER=$loginServer
REGISTRY_USERNAME=$spId
REGISTRY_PASSWORD=[Paste password from above]

Alternative (Admin User):
REGISTRY_USERNAME=$adminUsername
REGISTRY_PASSWORD=$adminPassword
"@

$clipboardContent | Set-Clipboard
Write-Host "Secrets copied to clipboard!" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "Next Steps:" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "1. Go to: GitHub Repository → Settings → Secrets and variables → Actions"
Write-Host "2. Click 'New repository secret'"
Write-Host "3. Add the secrets above"
Write-Host "4. Update .github/workflows/build-deploy.yml with ACR credentials"
Write-Host "5. Test by pushing code to main branch"
Write-Host ""
