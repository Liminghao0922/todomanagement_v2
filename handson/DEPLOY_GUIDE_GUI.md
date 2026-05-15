# Todo Management v2 Deployment Guide (Azure Portal track)

[English](DEPLOY_GUIDE_GUI.md) | [简体中文](DEPLOY_GUIDE_GUI-zh_CN.md) | [日本語](DEPLOY_GUIDE_GUI-ja_JP.md)

This guide is the beginner-friendly path. Every Azure resource is created from the Azure Portal UI, with code-only steps reduced to copy-paste blocks. For the IaC-driven path, see [`DEPLOY_GUIDE.md`](DEPLOY_GUIDE.md).

Estimated time: 90–120 minutes.

---

## Terminology Used in This Guide

| Term | Meaning in this hands-on |
| --- | --- |
| **Resource Group** | Logical container for all v2 resources (default name `rg-todomanagement-dev`). |
| **Function App** | Azure Functions on a Linux Consumption (Y1) plan that hosts `src/api/`. |
| **Static Web App (SWA)** | Hosts the Vue 3 SPA built from `src/web/`. |
| **Cosmos DB serverless** | Stores SQL containers (`todos` / `owners` / `projects` / `conversations`) and the Gremlin graph (`todo-graph-db`/`todo-graph`). |
| **Azure OpenAI** | Provides `gpt-4o-mini` and `text-embedding-3-small`. |
| **Azure AI Foundry** | Hosts the agent that `/api/chat` invokes via the `azure.ai.projects` SDK. |
| **App registration** | Entra ID identity for the SPA (sign-in) and, optionally, server-to-Foundry consent. |
| **Managed identity** | The Function App's system-assigned identity used to obtain AAD tokens for Cosmos Gremlin and Azure OpenAI. |

---

## Phase 1. Provision the Azure Resources

### 1.1 Create the resource group

1. Open `https://portal.azure.com`, sign in.
2. Search **Resource groups** → **+ Create**.
3. Subscription: your subscription. **Resource group**: `rg-todomanagement-dev`. **Region**: `Japan East` (or any region that supports Cosmos + OpenAI + Foundry + Functions Linux + SWA).
4. **Review + create** → **Create**.

📖 Reference: <https://learn.microsoft.com/azure/azure-resource-manager/management/manage-resource-groups-portal>

![Create resource group](image/DEPLOY_GUIDE_GUI/01-create-rg.png)

---

### 1.2 Create the Cosmos DB account

1. Search **Azure Cosmos DB** → **+ Create**.
2. API: **Azure Cosmos DB for NoSQL**.
3. **Basics**:
   - Resource group: `rg-todomanagement-dev`
   - Account name: `cosmos-todomanagement-<unique>` (lowercase letters / digits)
   - Location: same as RG
   - Capacity mode: **Serverless**
4. **Networking**: Public endpoint (all networks) — restrict later if needed.
5. **Backup**: defaults are fine.
6. **Review + create** → **Create**.

After provisioning:

7. Open the account → **Data Explorer** → **New Database** → ID `todo-db`. Then create four containers:

   | Container | Partition key |
   | --- | --- |
   | `todos` | `/owner_id` |
   | `owners` | `/id` |
   | `projects` | `/owner_id` |
   | `conversations` | `/owner_id` |

8. From the same Data Explorer, switch the API selector and create a **Gremlin** database `todo-graph-db` and graph `todo-graph` (partition key `/owner_id`).

> If your account was created as NoSQL only, you must create a separate Cosmos account for Gremlin and update settings accordingly. The Bicep templates do create a Gremlin DB inside the same account by default; in the Portal you may need a second account.

📖 Reference: <https://learn.microsoft.com/azure/cosmos-db/nosql/quickstart-portal>

![Cosmos containers](image/DEPLOY_GUIDE_GUI/02-cosmos-containers.png)

---

### 1.3 Create the Azure OpenAI resource

1. Search **Azure OpenAI** → **+ Create**.
2. Resource group `rg-todomanagement-dev`, Region `Japan East`, Name `aoai-todomanagement-<unique>`, Pricing tier `Standard S0`.
3. **Review + create** → **Create**.
4. Open the resource → **Model deployments** → **Manage deployments** (this opens **Azure AI Foundry**).
5. Deploy two models:
   - **gpt-4o-mini**, deployment name `gpt-4o-mini`
   - **text-embedding-3-small**, deployment name `text-embedding-3-small`

📖 Reference: <https://learn.microsoft.com/azure/ai-services/openai/how-to/create-resource>

![OpenAI deployments](image/DEPLOY_GUIDE_GUI/03-openai-deployments.png)

---

### 1.4 Create the Azure AI Foundry hub + project

1. From the Foundry portal opened in 1.3, click **+ New project**.
2. Pick a **hub** (or create one) inside the same resource group / region.
3. Name the project `prj-todomanagement`.
4. After creation, copy the **Project endpoint** from the project overview — it looks like `https://<hub>.services.ai.azure.com/api/projects/prj-todomanagement`. Save it.

📖 Reference: <https://learn.microsoft.com/azure/ai-foundry/how-to/create-projects>

![Foundry project endpoint](image/DEPLOY_GUIDE_GUI/04-foundry-project.png)

---

### 1.5 Create the Function App + Storage

1. Search **Function App** → **+ Create**.
2. **Basics**:
   - Resource group `rg-todomanagement-dev`
   - Function App name `func-todomanagement-<unique>`
   - Hosting `Consumption` (Y1)
   - Runtime stack `Python` 3.11
   - Operating System `Linux`
   - Region `Japan East`
3. **Storage**: create a new storage account `sttodomanagement<unique>` (lowercase + digits, max 24 chars).
4. **Networking**: Public access enabled, no inbound restriction (tighten later).
5. **Monitoring**: enable Application Insights, create a new component if needed.
6. **Identity**: enable **System-assigned managed identity**.
7. **Review + create** → **Create**.

📖 Reference: <https://learn.microsoft.com/azure/azure-functions/functions-create-function-app-portal>

![Function App created](image/DEPLOY_GUIDE_GUI/05-function-app.png)

---

### 1.6 Create the Static Web App

1. Search **Static Web Apps** → **+ Create**.
2. Resource group `rg-todomanagement-dev`, Name `stapp-todomanagement-<unique>`, Plan type `Free`.
3. Region (for backend): `East Asia`.
4. **Deployment details** → choose **Other** (we'll deploy with the SWA CLI later, not GitHub Actions).
5. **Review + create** → **Create**.
6. After provisioning: open the SWA → **Manage deployment token** → copy the token. Save it for Phase 4.

📖 Reference: <https://learn.microsoft.com/azure/static-web-apps/getting-started>

![SWA deployment token](image/DEPLOY_GUIDE_GUI/06-swa-token.png)

---

## Phase 2. Configure Identity and Permissions

### 2.1 Register the SPA in Microsoft Entra ID

1. Search **Microsoft Entra ID** → **App registrations** → **+ New registration**.
2. Name: `todomanagement-spa`.
3. Supported account types: **Accounts in this organizational directory only**.
4. Redirect URI: **Single-page application (SPA)** → `https://<swa>.azurestaticapps.net/`.
5. **Register**.

After creation:

6. **Authentication** → **+ Add URI** → `http://localhost:5173/`. Save.
7. **API permissions** → **+ Add a permission** → Microsoft Graph → **Delegated**:
   - `User.Read`
   - `Calendars.Read`
   - **Grant admin consent** if your tenant requires it.
8. From the **Overview** page, copy:
   - **Application (client) ID** → save as `CLIENT_ID`
   - **Directory (tenant) ID** → save as `TENANT_ID`

📖 Reference: <https://learn.microsoft.com/entra/identity-platform/quickstart-register-app>

![SPA app registration](image/DEPLOY_GUIDE_GUI/07-spa-app-registration.png)

---

### 2.2 Grant the Function App's managed identity access to Cosmos and Foundry

1. Open the Cosmos DB account → **Access control (IAM)** → **+ Add** → **Add role assignment**:
   - Role `Cosmos DB Built-in Data Contributor`
   - Assign access to: **Managed identity** → select the Function App.
2. Open the Foundry **project** → **Access control (IAM)** → **+ Add role assignment**:
   - Role `Azure AI Developer`
   - Assign access to: **Managed identity** → select the Function App.
3. Open the **Azure OpenAI** resource → **Access control (IAM)** → **+ Add**:
   - Role `Cognitive Services OpenAI User`
   - Assign to the Function App's managed identity.

📖 Reference: <https://learn.microsoft.com/azure/cosmos-db/how-to-setup-rbac>

![Cosmos role assignment](image/DEPLOY_GUIDE_GUI/08-cosmos-rbac.png)

---

## Phase 3. Configure the Foundry Agent

### 3.1 Create the agent

1. Open the Foundry project → **Agents** → **+ New agent**.
2. Use [`foundry-agent-config.json`](../foundry-agent-config.json) as a reference for **Name**, **Model** (`gpt-4o-mini`), **Description**, and **Instructions**.
3. **Tools** to enable:
   - Built-in **Microsoft Graph (Calendar)** — sign in with a delegated identity that has `Calendars.Read`.
   - Built-in **Azure Cosmos DB SQL query** — point to the Cosmos account → database `todo-db`.
   - Built-in **Azure Cosmos DB Gremlin** — point to `todo-graph-db` / graph `todo-graph`.
   - **Custom REST tool** named `estimate_hours`:
     - Method: `POST`
     - URL: `https://<function-app>.azurewebsites.net/api/tools/estimate-hours`
     - Body / response schema: copy from `foundry-agent-config.json`
4. **Save** the agent. Note its **Name** (e.g. `todo-agent`) and **Version** (`1`).

📖 Reference: <https://learn.microsoft.com/azure/ai-foundry/agents/concepts/tools>

![Foundry agent custom tool](image/DEPLOY_GUIDE_GUI/09-foundry-agent-tool.png)

---

## Phase 4. Configure and Deploy the Application

### 4.1 Set the Function App application settings

In the Function App → **Settings** → **Configuration** → **+ New application setting**, add:

| Name | Value |
| --- | --- |
| `COSMOS_ENDPOINT` | `https://<cosmos>.documents.azure.com:443/` |
| `COSMOS_DATABASE` | `todo-db` |
| `COSMOS_AUTH_MODE` | `aad` |
| `COSMOS_AUTO_CREATE` | `true` |
| `COSMOS_GRAPH_ACCOUNT` | `<cosmos>` (just the account name, no FQDN) |
| `COSMOS_GRAPH_DATABASE` | `todo-graph-db` |
| `COSMOS_GRAPH_NAME` | `todo-graph` |
| `OPENAI_ENDPOINT` | `https://<aoai>.openai.azure.com/` |
| `OPENAI_DEPLOYMENT_CHAT` | `gpt-4o-mini` |
| `OPENAI_DEPLOYMENT_EMBEDDING` | `text-embedding-3-small` |
| `OPENAI_API_VERSION` | `2024-08-01-preview` |
| `FOUNDRY_PROJECT_ENDPOINT` | Project endpoint from Phase 1.4 |
| `FOUNDRY_AGENT_NAME` | e.g. `todo-agent` |
| `FOUNDRY_AGENT_VERSION` | e.g. `1` |
| `FUNCTIONS_WORKER_RUNTIME` | `python` (already set) |

Click **Save**.

> If you prefer to use a Cosmos account key, set `COSMOS_AUTH_MODE=key` and add `COSMOS_KEY=<primary key>` instead of granting RBAC.

![Function App settings](image/DEPLOY_GUIDE_GUI/10-function-app-settings.png)

---

### 4.2 Publish the Function code from Cloud Shell

```powershell
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>/src/api

func azure functionapp publish func-todomanagement-<unique> --python
```

Verify:

```powershell
curl https://func-todomanagement-<unique>.azurewebsites.net/api/health
```

You should see `{"status":"healthy",...}`.

![func publish output](image/DEPLOY_GUIDE_GUI/11-func-publish.png)

---

### 4.3 Build the SPA and deploy to SWA

Still in Cloud Shell:

```powershell
cd ../web

@"
VITE_AZURE_CLIENT_ID=<CLIENT_ID from Phase 2.1>
VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/<TENANT_ID from Phase 2.1>
VITE_AZURE_REDIRECT_URI=https://<swa>.azurestaticapps.net
"@ | Out-File .env.local -Encoding utf8

npm install
npm run build

npm install -g @azure/static-web-apps-cli
swa deploy ./dist --deployment-token <SWA token from Phase 1.6> --env production
```

📖 Reference: <https://learn.microsoft.com/azure/static-web-apps/static-web-apps-cli-deploy>

![SWA deploy](image/DEPLOY_GUIDE_GUI/12-swa-deploy.png)

---

## Phase 5. Validate End-to-End

1. Open `https://<swa>.azurestaticapps.net` and sign in via MSAL.
2. **Todos** page → **+ New todo** → fill in title and description → save.
3. Search for a todo title; vector search should rank fuzzy matches.
4. Click **Generate todos** (the demo seeding action) → verify projects + todos in Cosmos **Data Explorer**.
5. **Projects** → open a seeded project → **Project Graph** → confirm Cytoscape renders edges from the Gremlin graph.
6. **Chat** → send a message such as `Estimate the hours for "Migrate API to Functions"` → the Foundry agent should respond and possibly invoke the `estimate_hours` tool.
7. Confirm transcript persistence: in Cosmos Data Explorer, open the `conversations` container; you should see new documents partitioned by `owner_id`.

![End-to-end check](image/DEPLOY_GUIDE_GUI/13-e2e-check.png)

---

## Phase 6. Cleanup

```powershell
az group delete --name rg-todomanagement-dev --yes --no-wait
```

Manually delete the Entra ID app registration (`todomanagement-spa`) under **Microsoft Entra ID → App registrations** if you no longer need it.

---

## Related Docs

- [`handson/DEPLOY_GUIDE.md`](DEPLOY_GUIDE.md)
- [`handson/QUICK_REFERENCE.md`](QUICK_REFERENCE.md)
- [`handson/TROUBLESHOOTING.md`](TROUBLESHOOTING.md)
- [`docs/ARCHITECTURE_GUIDE.md`](../docs/ARCHITECTURE_GUIDE.md)
