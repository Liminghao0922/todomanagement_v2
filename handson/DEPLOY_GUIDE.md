# Todo Management v2 Deployment Guide (IaC track)

[English](DEPLOY_GUIDE.md) | [简体中文](DEPLOY_GUIDE-zh_CN.md) | [日本語](DEPLOY_GUIDE-ja_JP.md)

This document explains the full process, in English, of deploying the Todo Management v2 application to Azure using the Bicep templates under `infra/`.

For the beginner, Azure Portal-based path, see [`DEPLOY_GUIDE_GUI.md`](DEPLOY_GUIDE_GUI.md).

Estimated time: about 45 to 60 minutes.

---

## Prerequisites

- Azure subscription permissions: `Owner`, or `Contributor` plus `User Access Administrator`
- Permission in Microsoft Entra ID to create app registrations
- Access to a region that has all of the following: Azure Cosmos DB, Azure OpenAI, Azure AI Foundry, Azure Functions on Linux, Azure Static Web Apps (the templates default to `japaneast`)
- GitHub account
- Local tooling (or Azure Cloud Shell PowerShell):
  - Azure CLI 2.60+ with the `bicep` extension
  - PowerShell 7+
  - Python 3.11
  - Azure Functions Core Tools v4
  - Node.js 18+ and npm
  - Git

---

## Step 1. Create a Repository from the GitHub Template

### 1.1 Open the template repository

Open the v2 template repository in GitHub:

- URL: `https://github.com/Liminghao0922/todomanagement_v2`

### 1.2 Click "Use this template"

1. Click **Use this template** at the top-right of the repository page.
2. Select **Create a new repository**.
3. Fill in the repository details:
   - **Repository name**: any name, for example `my-todo-app-v2`
   - **Description**: optional
   - **Visibility**: choose `Public` (recommended for the workshop flow)
   - **Include all branches**: leave unchecked
4. Click **Create repository from template**.

> Use a `Public` repository unless you intentionally want to troubleshoot private-repo CI/CD permissions; that is outside the scope of this hands-on.

![Use this template button](image/DEPLOY_GUIDE/use-this-template.png)

---

## Step 2. Open Azure Cloud Shell (PowerShell)

### 2.1 Sign in to Azure Portal

1. Open `https://portal.azure.com`.
2. Sign in with your Azure account.

### 2.2 Start Cloud Shell

1. Click the **Cloud Shell** icon (`>_`) at the top of the Azure Portal.
2. Wait for the terminal to start.
3. Switch the shell to **PowerShell** if it opens in Bash mode.

![Cloud Shell entry point](image/DEPLOY_GUIDE/cloud-shell-entry.png)

### 2.3 Verify the subscription

```powershell
# Show the current subscription
az account show

# Switch to a different subscription if needed
az account set --subscription "<subscription-id>"
```

---

## Step 3. Clone the Repository in Cloud Shell

```powershell
# Clone your repo created from the template
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>

# Confirm the layout
ls
# Expected: src/  infra/  docs/  handson/  images/  README.md  foundry-agent-config.json
```

If you already pushed local edits before opening Cloud Shell:

```powershell
git pull origin main
```

---

## Step 4. Review and Update Deployment Parameters

Open the Cloud Shell editor:

```powershell
code .
```

Open `infra/parameters.json`. Default content:

```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "location":            { "value": "japaneast" },
    "environment":         { "value": "dev" },
    "projectName":         { "value": "todomanagement" },
    "foundryAgentEndpoint":{ "value": "" },
    "foundryAgentApiKey":  { "value": "" },
    "graphTenantId":       { "value": "" },
    "graphClientId":       { "value": "" },
    "graphClientSecret":   { "value": "" }
  }
}
```

Recommended updates:

| Setting | Description | Example |
| --- | --- | --- |
| `location` | Azure region (must support Cosmos + OpenAI + Foundry + Functions Linux + SWA) | `japaneast`, `eastus`, `westus3` |
| `environment` | Environment identifier embedded in resource names | `dev`, `handson`, `prod` |
| `projectName` | Resource name prefix; lowercase letters / digits | `mytodov2`, `mycompanytodo` |
| `foundryAgentEndpoint` | Leave empty for now; you will set this in Step 8 once the Foundry agent exists | `https://<project>.services.ai.azure.com/api/projects/<project>` |
| `foundryAgentApiKey` | Leave empty; the Function App uses its managed identity by default | (empty) |
| `graphTenantId` / `graphClientId` / `graphClientSecret` | Reserved for future server-side Microsoft Graph calendar integration; leave empty for v2 | (empty) |

> The Foundry-related values can be left blank for the initial deployment. The Function App will return `status="not_configured"` from `/api/chat` until you update them.

![Editing parameters.json in Cloud Shell editor](image/DEPLOY_GUIDE/parameters-edit.png)

---

## Step 5. Deploy the Infrastructure

### 5.1 Set local variables

```powershell
$resourceGroupName = "rg-todomanagement-dev"
$location = "japaneast"
```

### 5.2 Run the deployment script

```powershell
cd infra

# In local Windows PowerShell, you may need:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

.\deploy.ps1 -ResourceGroupName $resourceGroupName -Location $location
```

`deploy.ps1` will:
1. Confirm the active subscription.
2. Create the resource group if missing.
3. Submit `main.bicep`, which provisions:
   - Cosmos DB serverless account with SQL DB `todo-db` (containers `todos`, `owners`, `projects`, `conversations`) and Gremlin DB `todo-graph-db` / graph `todo-graph`
   - Azure OpenAI account with `gpt-4o-mini` and `text-embedding-3-small` deployments
   - Azure Functions (Python 3.11, Linux Y1 Consumption) with system-assigned managed identity, plus its plan and storage account
   - Azure Static Web App
   - Azure AI Foundry handoff resource (Cognitive Services AI account)
   - Microsoft Entra ID app registration for the SPA (`User.Read`, `Calendars.Read`)

### 5.3 Record deployment outputs

When the script completes, capture the values printed under `Infrastructure Details`:

```text
==========================================
Infrastructure Details
==========================================
Function App: func-todomanagement-dev-xxxxxxxxxxxxx
Function URL: https://func-todomanagement-dev-xxxxxxxxxxxxx.azurewebsites.net
Static Web App: stapp-todomanagement-xxxxxxxxxxxxx
Static Web URL: https://<swa>.azurestaticapps.net
Cosmos Account: cosmostodomanagementxxxxxxxxxxxxx
Cosmos Endpoint: https://<cosmos>.documents.azure.com:443/
Cosmos SQL DB: todo-db
Cosmos Graph: todo-graph-db/todo-graph

Entra App Registration:
  CLIENT_ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  TENANT_ID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

Foundry:
  RESOURCE_NAME: aifoundryxxxxxxxxxxxxx
  RESOURCE_ID: /subscriptions/.../Microsoft.CognitiveServices/accounts/...
```

Save them for later steps.

### 5.4 Validate the deployment

```powershell
.\validate-deployment.ps1 -ResourceGroupName $resourceGroupName
```

The script lists Cosmos, Function App, SWA, and Cognitive Services resources, calls `/api/health` on the Function App, and writes `validation-report.json`.

![validate-deployment.ps1 output](image/DEPLOY_GUIDE/validate-output.png)

---

## Step 6. Grant the Function App's Managed Identity Data-Plane Access

`infra/modules/functions.bicep` already wires the Cosmos primary key into the Function App, but the **Gremlin** path uses the system-assigned managed identity to obtain an AAD token for `https://cosmos.azure.com/.default`. Grant the identity the Cosmos data-plane role:

```powershell
$rg     = $resourceGroupName
$cosmos = az cosmosdb list -g $rg --query "[0].name" -o tsv
$func   = az functionapp list -g $rg --query "[0].name" -o tsv
$mi     = az functionapp identity show -g $rg -n $func --query principalId -o tsv

# Cosmos DB Built-in Data Contributor (data-plane RBAC)
az cosmosdb sql role assignment create `
  --account-name $cosmos `
  --resource-group $rg `
  --role-definition-id "00000000-0000-0000-0000-000000000002" `
  --principal-id $mi `
  --scope "/"
```

If you also want to switch the SQL data path off the primary key (recommended for production), set `COSMOS_AUTH_MODE=aad` on the Function App and redeploy:

```powershell
az functionapp config appsettings set -g $rg -n $func `
  --settings COSMOS_AUTH_MODE=aad
```

---

## Step 7. Configure the Microsoft Entra ID SPA Sign-in

The template registers an SPA app registration. Make sure its redirect URIs include both the Static Web App URL and `http://localhost:5173` (for local development):

```powershell
$clientId = az ad app list --display-name "todomanagement-spa" --query "[0].appId" -o tsv
$swaUrl   = az staticwebapp list -g $rg --query "[0].defaultHostname" -o tsv

az ad app update --id $clientId `
  --set "spa.redirectUris=['https://$swaUrl/','http://localhost:5173/']"
```

Confirm the API permissions are `User.Read` and `Calendars.Read` (delegated). Grant admin consent if your tenant requires it.

![Entra ID app redirect URIs](image/DEPLOY_GUIDE/entra-redirect-uris.png)

---

## Step 8. Configure the Azure AI Foundry Agent

The Function App's `/api/chat` endpoint calls the Foundry agent via the `azure.ai.projects` SDK. You must create the agent in the Azure AI Foundry portal first.

### 8.1 Open the Foundry project

1. Go to `https://ai.azure.com`.
2. Open the project that lives inside the Cognitive Services account named in the deployment output (`foundryResourceName`).
3. Note the **Project endpoint** under the project overview — you will save it as `FOUNDRY_PROJECT_ENDPOINT`.

![Foundry project overview](image/DEPLOY_GUIDE/foundry-project-overview.png)

### 8.2 Create the agent

1. In the project, open **Agents** → **+ New agent**.
2. Use [`foundry-agent-config.json`](../foundry-agent-config.json) as the reference for **Name**, **Model** (`gpt-4o-mini`), **Description**, and **Instructions**.
3. Under **Tools**, enable:
   - Built-in **Microsoft Graph** (Calendar) tool — sign in with a delegated identity that has `Calendars.Read`.
   - Built-in **Azure Cosmos DB** tools (SQL query + Gremlin) — point them at the Cosmos account from Step 5 and at databases `todo-db` / `todo-graph-db`.
   - **Custom REST tool** named `estimate_hours` — method `POST`, URL `https://<function-app>/api/tools/estimate-hours`, with the input schema from `foundry-agent-config.json`.
4. Save the agent. Note the **Agent name** and **Version** (e.g. `todo-agent` / `1`).

![Adding the estimate_hours custom tool](image/DEPLOY_GUIDE/foundry-custom-tool.png)

### 8.3 Wire the Foundry settings into the Function App

```powershell
$projectEndpoint = "<paste from Foundry project overview>"
$agentName       = "todo-agent"
$agentVersion    = "1"

az functionapp config appsettings set -g $rg -n $func --settings `
  FOUNDRY_PROJECT_ENDPOINT=$projectEndpoint `
  FOUNDRY_AGENT_NAME=$agentName `
  FOUNDRY_AGENT_VERSION=$agentVersion
```

### 8.4 Grant the Function App access to the Foundry project

```powershell
$projectId = az cognitiveservices account list -g $rg --query "[?kind=='AIServices'] | [0].id" -o tsv

# Azure AI Developer (or the project-level role suitable for your tenant)
az role assignment create `
  --assignee-object-id $mi `
  --assignee-principal-type ServicePrincipal `
  --role "Azure AI Developer" `
  --scope $projectId
```

---

## Step 9. Deploy the Function App Code

From your local machine (or Cloud Shell):

```powershell
cd ../src/api

# (Optional) Run locally first to confirm the package
copy local.settings.example.json local.settings.json
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
func start
# Visit http://localhost:7071/api/health then stop with Ctrl+C
deactivate

# Publish to Azure
func azure functionapp publish $func --python
```

After publish completes, hit the cloud health endpoint:

```powershell
curl https://$func.azurewebsites.net/api/health
# {"status":"healthy","service":"Todo Management Functions API","timestamp":"..."}
```

![func azure functionapp publish output](image/DEPLOY_GUIDE/func-publish-output.png)

---

## Step 10. Deploy the Static Web App

### 10.1 Build the SPA locally

```powershell
cd ../web
copy .env.example .env.local
```

Edit `.env.local`:

```text
VITE_AZURE_CLIENT_ID=<CLIENT_ID from Step 5.3>
VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/<TENANT_ID from Step 5.3>
VITE_AZURE_REDIRECT_URI=https://<swa>.azurestaticapps.net
```

Then build:

```powershell
npm install
npm run build
# Output is written to dist/
```

### 10.2 Deploy with the SWA CLI

```powershell
npm install -g @azure/static-web-apps-cli

$swaName = az staticwebapp list -g $rg --query "[0].name" -o tsv
$swaToken = az staticwebapp secrets list -g $rg -n $swaName --query "properties.apiKey" -o tsv

swa deploy ./dist --deployment-token $swaToken --env production
```

Open `https://<swa>.azurestaticapps.net` and sign in.

![Static Web App deployed](image/DEPLOY_GUIDE/swa-deployed.png)

---

## Step 11. Optional — Wire up GitHub Actions

If you prefer CI/CD over manual `func azure functionapp publish` and `swa deploy`:

1. Create a service principal scoped to the resource group:
   ```powershell
   $subscriptionId = $(az account show --query id -o tsv)
   az ad sp create-for-rbac `
     --name "github-todomanagement-v2-ci" `
     --role "Contributor" `
     --scopes "/subscriptions/$subscriptionId/resourceGroups/$rg" `
     --sdk-auth
   ```
   Copy the JSON output into the GitHub repository secret `AZURE_CREDENTIALS`.
2. Run `setup-github-variables-update.ps1` (in the repo root) to populate the per-repo Variables (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_REDIRECT_URI`, `API_PROXY_TARGET`).
3. Add workflows that publish the Function App (`func azure functionapp publish` or `azure/functions-action@v1`) and the Static Web App (`Azure/static-web-apps-deploy@v1`).

---

## Step 12. End-to-End Validation

Run through the smoke test:

1. Open the SWA URL and sign in via MSAL.
2. **Todos** page → **+ New todo**, fill in title / description, save. Confirm the todo appears in the list.
3. Use the search box (`?search=...`) to confirm vector search returns ranked results.
4. **Generate todos** (the seeding endpoint behind the demo button) — verify items appear in `todos` and `projects` in the Cosmos Data Explorer.
5. **Projects** → **Project Graph** for the seeded project — confirm the Cytoscape view renders relations (`BLOCKED_BY`, `PRECEDES`, `SUBTASK_OF`, `SIMILAR_TO`). This proves the Gremlin path is working.
6. **Chat** view → send a message that mentions a todo title; the Foundry agent should respond and may call `estimate_hours`. Confirm a transcript shows up under `/api/conversations`.

![End-to-end smoke test](image/DEPLOY_GUIDE/smoke-test.png)

---

## Step 13. Cleanup

To remove all resources created in this guide:

```powershell
az group delete --name $resourceGroupName --yes --no-wait
```

The Entra ID app registration is **not** in the resource group — delete it from the Azure Portal under **Microsoft Entra ID → App registrations** if you no longer need it.

---

## Related Docs

- [`docs/ARCHITECTURE_GUIDE.md`](../docs/ARCHITECTURE_GUIDE.md)
- [`handson/DEPLOY_GUIDE_GUI.md`](DEPLOY_GUIDE_GUI.md)
- [`handson/QUICK_REFERENCE.md`](QUICK_REFERENCE.md)
- [`handson/TROUBLESHOOTING.md`](TROUBLESHOOTING.md)
- [`infra/README.md`](../infra/README.md)
