# Todo Management v3 Deployment Guide

[English](DEPLOY_GUIDE.md) | [简体中文](DEPLOY_GUIDE-zh_CN.md) | [日本語](DEPLOY_GUIDE-ja_JP.md)

Complete deployment guide from GitHub template to live Azure application. Estimated: 45-60 minutes.

## Prerequisites

- Azure subscription (Owner or Contributor + User Access Administrator)
- Microsoft Entra ID app registration permission
- GitHub account
- Azure CLI, PowerShell 7+, Git installed
- Node 18+, npm installed

## Step 1: Clone Repository from Template

1. Open https://github.com/Liminghao0922/todomanagement
2. Click **Use this template** → **Create new repository**
3. Name: e.g. `my-todo-app`
4. Visibility: Public or Private
5. Click **Create repository from template**

## Step 2: Prepare Azure Environment

### 2.1 Set subscription

```powershell
az login
az account list
az account set --subscription "<your-subscription-id>"
```

### 2.2 Create resource group

```powershell
$rg = "rg-todomanagement-dev"
$location = "japaneast"
az group create --name $rg --location $location
```

### 2.3 Clone repo locally

```powershell
git clone https://github.com/[username]/[repo].git
cd [repo]
```

## Step 3: Configure Infrastructure Parameters

Edit `infra/parameters.json`:

```json
{
  "location": "japaneast",
  "environment": "dev",
  "projectName": "todomanagement",
  "foundryAgentEndpoint": "",          // Fill after Foundry setup
  "foundryAgentApiKey": "",             // Fill after Foundry setup
  "graphTenantId": "",                  // Fill: your Entra tenant ID
  "graphClientId": "",                  // Fill: Service Principal client ID
  "graphClientSecret": ""               // Fill: Service Principal secret
}
```

Get `graphTenantId`:
```powershell
az account show --query tenantId -o tsv
```

## Step 4: Deploy Infrastructure (Bicep)

```powershell
cd infra

# Review the deployment
az deployment group validate \
  --resource-group $rg \
  --template-file main.bicep \
  --parameters parameters.json

# Execute deployment (~10 min)
az deployment group create \
  --resource-group $rg \
  --template-file main.bicep \
  --parameters parameters.json

# Save outputs (detailed below)
az deployment group show \
  --resource-group $rg \
  --name main \
  --query properties.outputs
```

### Key Outputs to Record

```
- functionAppName
- functionAppUrl (e.g., https://func-todomanagement-xxxxx.azurewebsites.net)
- staticWebAppName
- staticWebAppUrl (e.g., https://[swa].azurestaticapps.net)
- cosmosEndpoint
- cosmosAccountName
- appRegistrationClientId (Entra app for frontend)
- tenantId
- foundryResourceName
```

## Step 5: Create Entra ID App Registration (Frontend)

```powershell
# Create app registration
$appName = "todo-management-web"
$app = az ad app create --display-name $appName | ConvertFrom-Json
$appId = $app.appId

# Add web platform
$replyUrls = @(
  "https://[your-swa-url]/"
  "http://localhost:5173/"
)
az ad app update --id $appId `
  --reply-urls $replyUrls

# Add permissions: User.Read, Calendar.Read.All
az ad app permission add --id $appId \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions e1fe6dd8-ba31-4d61-89e6-40ba127554c7=Scope 570282fd-fa5c-430b-a940-f708cd10ae6e=Scope

# Grant admin consent
$servicePrincipal = az ad sp create --id $appId | ConvertFrom-Json
az ad app permission admin-consent --id $appId

echo "App Registration ID: $appId"
```

## Step 6: Create Service Principal for Graph API (Calendar Scan)

```powershell
# Create service principal for backend
$spName = "todo-management-backend"
$sp = az ad sp create-for-rbac --name $spName --role Contributor | ConvertFrom-Json

# Extract credentials
$graph_tenant_id = $sp.tenant
$graph_client_id = $sp.clientId
$graph_client_secret = $sp.password

# Grant Graph API permissions for Calendars.Read
az ad app permission add --id $graph_client_id \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions 798ee544-9d2d-430c-9da2-d3a3b914dfd4=Role

# Grant admin consent
az ad app permission admin-consent --id $graph_client_id

echo "Backend SP Client ID: $graph_client_id"
echo "Backend SP Tenant: $graph_tenant_id"
```

## Step 7: Update Infrastructure Parameters (Part 2)

Update `infra/parameters.json` with Entra values:

```json
{
  "graphTenantId": "[value from Step 6]",
  "graphClientId": "[value from Step 6]",
  "graphClientSecret": "[value from Step 6]"
}
```

Deploy again to inject these values into Function App:

```powershell
az deployment group create \
  --resource-group $rg \
  --template-file main.bicep \
  --parameters parameters.json
```

## Step 8: Deploy Function Code

```powershell
cd ../src/api

# Prepare
copy local.settings.example.json local.settings.json

# Install dependencies
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# Local test (optional)
func start
# Health check: http://localhost:7071/api/health

# Deploy to Azure
func azure functionapp publish [functionAppName] --build remote
```

## Step 9: Deploy Frontend (Static Web Apps)

```powershell
cd ../web

# Build
npm install
npm run build
# Output: dist/

# Deploy to Static Web Apps
az staticwebapp upload \
  --name [staticWebAppName] \
  --source ./dist
```

## Step 10: Configure Foundry Agent

1. Navigate to Azure Portal → AI Foundry resource
2. Open web UI
3. Create a new **Agent project**
4. Configure:
   - **Model**: gpt-4o-mini (from your Azure OpenAI deployment)
   - **System prompt**: Define agent behavior
   - **Built-in tools**: Enable Microsoft Graph + Cosmos DB queries
   - **Custom tool**: Add endpoint POST `/api/tools/estimate-hours`
     - Input: `{ "title": "...", "description": "...", "category": "...", "complexity": "..." }`
     - Output: `{ "found": true, "estimatedHours": N, "similarTodos": [...] }`

5. Update `foundry-agent-config.json` with:
   ```json
   {
     "agentName": "todo-assistant",
     "model": "gpt-4o-mini",
     "toolsEndpoint": "https://[functionAppUrl]/api/tools/estimate-hours",
     ...
   }
   ```

6. Update `infra/parameters.json` with Foundry endpoint & API key, redeploy

## Step 11: Validate Deployment

```powershell
cd ../../infra
.\validate-deployment.ps1 -ResourceGroupName $rg

# Expected checks:
# ✓ Cosmos DB Accounts: 1
# ✓ Function Apps: 1
# ✓ Static Web Apps: 1
# ✓ Cognitive Services: 1
# ✓ Health endpoint reachable
```

## Step 12: Test Application

1. Open Static Web App URL: `https://[swa].azurestaticapps.net`
2. Sign in with Microsoft Entra ID
3. Create a todo: POST /api/todos
4. Search todos: GET /api/todos?search=...
5. Chat with Foundry agent
6. Verify calendar scan (check logs in Function App)

## Troubleshooting

### Function App returns 401

- Check Entra ID application permissions
- Verify `GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET` in Function settings

### Cosmos DB returns permission error

- Verify Function managed identity has Cosmos Data Contributor role
- Check partition key `/owner_id` in queries

### Static Web App shows blank page

- Run: `npm run build`
- Verify `dist/` folder has `index.html`
- Check SWA deployment logs

### Meeting text extraction returns empty

- Verify GraphAPI bearer token generation succeeds
- Check `GRAPH_TENANT_ID` and service principal permissions

For more details see [docs/ARCHITECTURE_GUIDE.md](../docs/ARCHITECTURE_GUIDE.md).
