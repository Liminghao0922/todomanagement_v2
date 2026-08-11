# Todo Management v2 Deployment Guide (Azure Portal track)

[English](DEPLOY_GUIDE_GUI.md) | [简体中文](DEPLOY_GUIDE_GUI-zh_CN.md) | [日本語](DEPLOY_GUIDE_GUI-ja_JP.md)

This guide follows the beginner-friendly path. Learners do not need a GitHub account or prior Git knowledge: Azure resources are created in the Azure Portal, and the application is built and deployed from Azure Cloud Shell. Instructors prepare the shared MCP container image by following [`INSTRUCTOR_PREP_GUIDE.md`](INSTRUCTOR_PREP_GUIDE.md). For the IaC-driven path, see [`DEPLOY_GUIDE.md`](DEPLOY_GUIDE.md).

Estimated time: 90–120 minutes.

---

## Before You Start

Get these eight items from the instructor:

- Todo Management v2 public repository URL
- Workshop ACR login server, for example `workshopacr.azurecr.io`
- MCP image name, `mcp-toolkit`
- MCP image tag, for example `workshop-20260727`
- Assigned Container Apps environment, for example `cae-todomanagement-workshop-01`
- Environment resource group, for example `rg-todomanagement-instructor`
- Environment region, for example `japaneast`
- Your unique Container App name, for example `mcp-toolkit-p01`

You need a browser, internet access, an Azure subscription, and permission to use [Azure Cloud Shell](https://learn.microsoft.com/azure/cloud-shell/overview). Select **PowerShell** when Cloud Shell asks which shell to use.

Participant accounts should have at least the following permissions:

- **Owner** on their working resource group (at minimum, Contributor or higher)
- **Application Developer** in Microsoft Entra ID (permission to create app registrations)

You will follow one route:

1. Create Azure resources in the Portal.
2. Configure two Entra app registrations and managed identities.
3. Deploy the instructor-provided MCP image to Container Apps.
4. Create and connect the Foundry agent.
5. Clone the public source and deploy the API and web app from Cloud Shell.
6. Test the application, then delete the workshop resources.

You do not create a GitHub repository, credentials, secrets, or workflows.

---

## Terminology Used in This Guide

| Term                           | Meaning in this hands-on                                                                                                                    |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **Resource Group**       | Logical container for all v2 resources (default name`rg-todomanagementv2-dev`).                                                           |
| **Function App**         | Azure Functions on a Linux Flex Consumption plan that hosts`src/api/`.                                                                   |
| **Static Web App (SWA)** | Hosts the Vue 3 SPA built from`src/web/`.                                                                                                 |
| **Cosmos DB serverless** | Stores SQL containers (`todos` / `owners` / `projects` / `conversations`) and the Gremlin graph (`todo-graph-db`/`todo-graph`). |
| **Microsoft Foundry**    | Provides`gpt-5.4-mini` and `text-embedding-3-small`.                                                                                    |
| **App registration**     | Entra ID identity for the SPA (sign-in) and, optionally, server-to-Foundry consent.                                                         |
| **Managed identity**     | The Function App's system-assigned identity used to obtain AAD tokens for Cosmos Gremlin and Azure OpenAI.                                  |

---

## Phase 1. Create Infrastructure from Azure Portal

### 1.1 Create the resource group

1. Open `https://portal.azure.com`, sign in.
2. Search **Resource groups** → **+ Create**.
3. Subscription: your subscription. **Resource group**: `rg-todomanagementv2-dev`. **Region**: `Japan East` (or any region that supports Cosmos + Foundry + Functions Linux + SWA).
4. **Review + create** → **Create**.

📖 Reference: [https://learn.microsoft.com/azure/azure-resource-manager/management/manage-resource-groups-portal](https://learn.microsoft.com/azure/azure-resource-manager/management/manage-resource-groups-portal)

![Create resource group](image/DEPLOY_GUIDE_GUI/01-create-rg.png)

---

### 1.2 Create the Cosmos DB account for NoSQL

1. Search **Azure Cosmos DB** → **+ Create**.
2. API: **Azure Cosmos DB for NoSQL**.
3. **Basics**:

   - Workload Type: `Learning`
   - Resource group: `rg-todomanagementv2-dev`
   - Account name: `cosmos-todomanagement-<unique>` (lowercase letters / digits)
   - Availability Zones: `Disable`
   - Location: same as RG
   - Capacity mode: **Serverless**
4. **Global distribution**:

   - Geo-Redundancy: `Disable`
   - Multi-region Writes: `Disable`
5. **Networking**:

   - Connectivity method: `All networks` — restrict later if needed.
6. **Backup Policy**: defaults are fine.
7. **Security**:

   - Key-based Authentication: `Disable` - We will use Entra id for authentication.
   - Data Encryption: `Service-managed key`
8. **Review + create** → **Create**.
   ![Create Cosmos DB Account](image/DEPLOY_GUIDE_GUI/02-create-cosmos.png)
   After provisioning:
9. Open the account, copy **URI** from **Overview** (`https://<cosmos>.documents.azure.com:443/`), and save it. You will use it in Phase 3 and Phase 4.
10. Open **Data Explorer** → **New Database** → ID `todo-db`. Then create four containers:

| Container         | Partition key |
| ----------------- | ------------- |
| `todos`         | `/owner_id` |
| `owners`        | `/id`       |
| `projects`      | `/owner_id` |
| `conversations` | `/owner_id` |

![Cosmos containers](image/DEPLOY_GUIDE_GUI/03-cosmos-containers.png)
📖 Reference:[https://learn.microsoft.com/azure/cosmos-db/nosql/quickstart-portal](https://learn.microsoft.com/azure/cosmos-db/nosql/quickstart-portal)

---

### 1.3 Create an Azure Cosmos DB account for Gremlin API

1. Search **Azure Cosmos DB** → **+ Create**.
2. API: **Azure Cosmos DB for Apache Gremlin**.
   ![Select Azure Cosmos DB for Apache Gremlin](image/DEPLOY_GUIDE_GUI/04-cosmosgre-select-api.png)
3. **Basics**:

   - Workload Type: `Learning`
   - Resource group: `rg-todomanagementv2-dev`
   - Account name: `cosmosgre-todomanagement-<unique>` (lowercase letters / digits)
   - Availability Zones: `Disable`
   - Location: same as RG
   - Capacity mode: **Serverless**
4. **Global distribution**:

   - Geo-Redundancy: `Disable`
   - Multi-region Writes: `Disable`
5. **Networking**:

   - Connectivity method: `All networks` — restrict later if needed.
6. **Backup Policy**: defaults are fine.
7. **Security**:

   - Data Encryption: `Service-managed key`
8. **Review + create** → **Create**.
   ![Create Cosmos DB Account](image/DEPLOY_GUIDE_GUI/05-create-cosmosgre.png)
   After provisioning:
9. Open the account → **Data Explorer** → **New Graph**:

   - **Database id**: `todo-graph-db`
   - **Graph id**: `todo-graph`
   - **Partition key**: `/owner_id`
     ![Create Graph](image/DEPLOY_GUIDE_GUI/06-create-cosmosgre-graph.png)

---

### 1.4 Create Foundry resource and deploy models

1. Search **Microsoft Foundry** → **Foundry** → **+ Create**.
2. **Basics**:
   - Resource group: `rg-todomanagementv2-dev`
   - Name: `foundry-todomanagement-<unique>` (lowercase letters / digits)
   - Region: same as RG
3. **Review + create** → **Create**.

![Create Foundry resource](image/DEPLOY_GUIDE_GUI/07-create-foundry-resource.png)
After provisioning:
4. Open the Foundry resource → **Access control (IAM)** → **+ Add role assignment**.
5. Select the **Foundry User** role, then select **Next**.
6. For **Assign access to**, select **User, group, or service principal** → **+ Select members** → select your signed-in account → **Review + assign**.
7. Wait a few minutes for the role assignment to propagate.
8. Open the Foundry resource → **Go to Foundry portal**, copy the `Project endpoint` and save it.
9. **Discover** → **Models** → **Deploy a base model** → search `text-embedding-3-small`
10. Select `text-embedding-3-small`, click **Deploy** → select **Default settings**
![Deploy text-embedding-3-small](image/DEPLOY_GUIDE_GUI/08-deploy-embedding-model.png)
11. **Discover** → **Models** → **Deploy a base model** → search `gpt-5.4-mini`
12. Select `gpt-5.4-mini`, click **Deploy** → select **Default settings**
![Deploy gpt-5.4-mini](image/DEPLOY_GUIDE_GUI/09-deploy-gpt-model.png)

---

### 1.5 Create the Function App + Storage

1. Search **Function App** → **+ Create**.
2. Select `Flex Consumption`
3. **Basics**:
   - Resource group: `rg-todomanagementv2-dev`
   - Function App name: `func-todomanagement`
   - If **Secure unique default hostname** is shown, enable it (this option may not appear depending on region or portal language).
   - Region: same as RG
   - Runtime stack: `Python` 3.11
   - Instance size: `2048 MB`
   - Zone redundancy: `Disabled`
4. **Storage**: create a new storage account `satodomanagement<unique>` (lowercase + digits, max 24 chars).
5. **Azure OpenAI**: leave it as default.
6. **Networking**: Public access enabled, no inbound restriction (tighten later).
7. **Monitoring**: enable Application Insights, create a new component if needed.
8. **Durable Functions**: leave it as default.
9. **Deployment**: leave it as default.
10. **Authentication**: change Authentication type to `Managed identity`.
    ![Set function authentication](image/DEPLOY_GUIDE_GUI/10-set-function-authentication.png)
11. **Review + create** → **Create**.
    ![Function App created](image/DEPLOY_GUIDE_GUI/11-create-function-app.png)
12. After provisioning: open Function App,  **Settings** → **Identity** → **User assigned** → **func-todomanagement-uami**
    copy the **Client Id** and **Object (principal) ID**, then save them.
    ![Copy function uami cliend id](image/DEPLOY_GUIDE_GUI/copy-function-uami-client-id.png)

📖 Reference: [https://learn.microsoft.com/azure/azure-functions/functions-create-function-app-portal](https://learn.microsoft.com/azure/azure-functions/functions-create-function-app-portal)

---

### 1.6 Create the Static Web App

1. Search **Static Web Apps** → **+ Create**.
2. **Basics**:
   - Resource group: `rg-todomanagementv2-dev`
   - Name: `stapp-todomanagement-<unique>`
   - Plan type: `Standard`.
   - Deployment details: choose **Other**
3. **Deployment configuration** → choose **Deployment token** .
4. **Advanced** choose `East Asia` for **Region for Azure Functions API and staging environments**
5. **Review + create** → **Create**.
   ![Create Static Web App](image/DEPLOY_GUIDE_GUI/12-create-swa.png)
6. After provisioning, open the SWA, copy the following information, and save it for Phase 4.
   - **Manage deployment token**
   - **URL**

📖 Reference: [https://learn.microsoft.com/azure/static-web-apps/getting-started](https://learn.microsoft.com/azure/static-web-apps/getting-started)

---

## Phase 2. Configure Identity and Permissions

### 2.1 Register the SPA in Microsoft Entra ID

1. Search **Microsoft Entra ID** → **App registrations** → **+ New registration**.
2. Name: `todomanagementv2-spa`.
3. Supported account types: **Accounts in this organizational directory only**.
4. Redirect URI: **Single-page application (SPA)** → `https://<swa>.azurestaticapps.net/`.
5. **Register**.

After creation:
6. In **Authentication** → **+ Add URI**, add the following URIs and save:

- `https://<swa>.azurestaticapps.net` (without trailing slash)
- `https://<swa>.azurestaticapps.net/` (with trailing slash)
- Optional: `http://localhost:5173` (without trailing slash)
- Optional: `http://localhost:5173/` (with trailing slash)

7. From the **Overview** page, copy:
   - **Application (client) ID** → save as `CLIENT_ID`
   - **Directory (tenant) ID** → save as `TENANT_ID`

📖 Reference: [https://learn.microsoft.com/entra/identity-platform/quickstart-register-app](https://learn.microsoft.com/entra/identity-platform/quickstart-register-app)

![SPA app registration](image/DEPLOY_GUIDE_GUI/register-an-application.png)

---

### 2.2 Register the MCP API in Microsoft Entra ID

The shared image is only application code. Each learner creates a separate identity for their own MCP endpoint.

1. Open **Microsoft Entra ID** → **App registrations** → **+ New registration**.
2. Name: `todomanagementv2-mcp-api`.
3. Supported account types: **Accounts in this organizational directory only**.
4. Leave **Redirect URI** empty, then select **Register**.
5. Copy the **Application (client) ID** and save it as `MCP_CLIENT_ID`.
6. Open **Expose an API** → **Add** next to **Application ID URI** → accept `api://<MCP_CLIENT_ID>`.
7. Open **App roles** → **Create app role** and enter:| Setting              | Value                                  |
   | -------------------- | -------------------------------------- |
   | Display name         | `MCP Tool Executor`                  |
   | Allowed member types | `Both (Users/Groups + Applications)` |
   | Value                | `Mcp.Tool.Executor`                  |
   | Description          | `Execute Cosmos DB MCP tools`        |
   | Enable this app role | Checked                                |
8. Select **Apply**.

You add the Container App redirect URIs after its URL exists in Phase 3.

---

### 2.3 Grant application identities access

1. Assign `Cosmos DB Built-in Data Contributor` to the Function App user-assigned managed identity.
   a. First, use the Azure Portal GUI data-plane role assignment in the NoSQL account (and Gremlin account) to assign `Cosmos DB Built-in Data Contributor` to `func-todomanagement-uami`.
   b. If data-plane role assignment is not available in the portal for your tenant/role, use Cloud Shell (PowerShell) with the fallback commands below.

   ```powershell
   az cosmosdb sql role assignment create `
      --account-name "<your-cosmos-db-account-name>" `
      --resource-group "<your-resource-group-name>" `
      --role-definition-id "00000000-0000-0000-0000-000000000002" `
      --principal-id "<your-azure-function-uami-object-id>" `
      --scope "/"

   az cosmosdb sql role assignment create `
      --account-name "<your-cosmos-gremlin-db-account-name>" `
      --resource-group "<your-resource-group-name>" `
      --role-definition-id "00000000-0000-0000-0000-000000000002" `
      --principal-id "<your-azure-function-uami-object-id>" `
      --scope "/"
   ```

   For `--principal-id`, use the **Object (principal) ID**, not the Client ID.

   ![Assign Cosmos DB Built-in Data Contributor role to Function App](image/DEPLOY_GUIDE_GUI/assign-cosmos-role-to-func.png)
   📖 Reference: [https://learn.microsoft.com/azure/cosmos-db/how-to-setup-rbac](https://learn.microsoft.com/azure/cosmos-db/how-to-setup-rbac)
2. Open the Foundry **project** → **Access control (IAM)** → **+ Add role assignment**:

   - Role `Foundry User`
   - Assign access to: **Managed identity** → select the **func-todomanagement-uami**.
     ![Assign Foundry User role to Function App](image/DEPLOY_GUIDE_GUI/assign-foundry-role-to-func.png)
3. Grant the `MCP Tool Executor` role to the Foundry project's managed identity.
   a. GUI-first path: open **Enterprise applications** → `todomanagementv2-mcp-api` → **Users and groups** → **+ Add user/group**.
   b. Select the Foundry project managed identity (for example `<foundry-resource-name>/projects/proj-default`) as the principal, select role `MCP Tool Executor`, and assign.
   c. If the portal cannot select the managed identity principal, use the same Cloud Shell PowerShell session and run the fallback command below.

   ```powershell
   $ResourceName = "todomanagementv2-mcp-api"
   $AppRoleName = "Mcp.Tool.Executor"
   $PrincipalName = "<your-foundry-resource-name>/projects/proj-default"
   $Resource = az ad sp list --display-name $ResourceName --query "{ AppRoleId: [0] .appRoles [?value=='$AppRoleName'].id | [0], ObjectId:[0] .id }" -o json | ConvertFrom-Json

   $Principal = az ad sp list --display-name $PrincipalName --query "{ ObjectId: [0] .id }" -o json | ConvertFrom-Json


   $spObjectId = $Resource.ObjectId 
   $body = @{
      principalId = $Principal.ObjectId
      resourceId = $Resource.ObjectId 
      appRoleId = $Resource.AppRoleId
   } | ConvertTo-Json

   az rest --method POST `
      --url "https://graph.microsoft.com/v1.0/servicePrincipals/$spObjectId/appRoleAssignedTo" `
      --headers "Content-Type=application/json" `
      --body $body 2>&1
   ```

---

## Phase 3. Configure the Foundry Agent

### 3.1 Deploy MCP tool for Cosmos DB

Before the workshop, the instructor builds the MCP Toolkit image and shares these values:

| Value                      | Example                            |
| -------------------------- | ---------------------------------- |
| Registry                   | `workshopacr.azurecr.io`         |
| Image                      | `mcp-toolkit`                    |
| Tag                        | `workshop-20260727`              |
| Container Apps environment | `cae-todomanagement-workshop-01` |
| Environment resource group | `rg-todomanagement-instructor`   |
| Environment region         | `japaneast`                      |
| Container App name         | `mcp-toolkit-p01`                |

The instructor has already created the shared Container Apps environment and granted you permission to deploy your Container App into it. Do not create another environment, clone the MCP Toolkit repository, or build an image during the hands-on.

#### 3.1.1 Create the Container App with the MCP image

1. Search **Container Apps** → **+ Create**.
2. On **Basics**:

   - Resource group: `rg-todomanagementv2-dev`
   - Container app name: the unique name assigned by the instructor, for example `mcp-toolkit-p01`
   - Region: the instructor-provided environment region
   - Container Apps environment: select the environment assigned by the instructor, for example `cae-todomanagement-workshop-01`
3. On **Container**:

   - Use quickstart image: **Unchecked**
   - Image source: **Azure Container Registry**
   - Registry: the instructor-provided registry
   - Image: the instructor-provided image
   - Image tag: the instructor-provided tag
   - CPU: `0.5`
   - Memory: `1 GiB`
4. Add these environment variables:

   | Name                            | Value                                  |
   | ------------------------------- | -------------------------------------- |
   | `AzureAd__ClientId`           | Your`MCP_CLIENT_ID` from Phase 2     |
   | `AzureAd__TenantId`           | Your`TENANT_ID` from Phase 2         |
   | `AzureAd__Audience`           | Your`MCP_CLIENT_ID` from Phase 2     |
   | `COSMOS_ENDPOINT`             | NoSQL endpoint from Step 1.2           |
   | `OPENAI_ENDPOINT`             | Foundry project endpoint from Step 1.4 |
   | `OPENAI_EMBEDDING_DEPLOYMENT` | `text-embedding-3-small`             |
   | `ASPNETCORE_ENVIRONMENT`      | `Production`                         |
   | `ASPNETCORE_URLS`             | `http://+:8080`                      |
5. In the **Scale** section at the bottom of the **Container** tab (or in a dedicated **Scale** tab, depending on portal layout):

   - Minimum replicas: `0`
   - Maximum replicas: `1`
6. On **Ingress**:

   - Ingress: **Enabled**
   - Ingress traffic: **Accepting traffic from anywhere**
   - Ingress type: **HTTP**
   - Target port: `8080`
7. Select **Review + create** → **Create**, then confirm that the revision becomes **Running**.

If the assigned environment is not selectable, confirm the subscription, environment resource group, and region with the instructor. The instructor must grant your account **Container Apps Contributor** at the assigned environment's scope. Do not create a replacement environment.

If the registry or image is not selectable, stop and ask the instructor to confirm your workshop ACR access and whether ACR **Admin user** is enabled on the instructor side. Do not change ACR settings from the participant side.

#### 3.1.2 Grant the Container App runtime permissions

1. Open your Container App → **Settings** → **Identity** → **System assigned**.
2. Set **Status** to **On** → **Save**.
3. Open the Cosmos DB for NoSQL account → **Access control (IAM)** and assign **Cosmos DB Account Reader Role** to the Container App managed identity.
4. In Cloud Shell PowerShell, grant the Cosmos data-plane reader role:

   ```powershell
   $resourceGroup = "rg-todomanagementv2-dev"
   $cosmosAccount = "<your-nosql-account-name>"
   $mcpAppName = "<your-assigned-container-app-name>"
   $mcpPrincipalId = az containerapp identity show `
     --resource-group $resourceGroup `
     --name $mcpAppName `
     --query principalId -o tsv

   az cosmosdb sql role assignment create `
     --account-name $cosmosAccount `
     --resource-group $resourceGroup `
     --role-definition-id "00000000-0000-0000-0000-000000000001" `
     --principal-id $mcpPrincipalId `
     --scope "/"
   ```
5. Open the Foundry project → **Access control (IAM)** and assign **Foundry User** to the same managed identity.
6. Restart the Container App revision after role assignments have propagated.

#### 3.1.3 Complete MCP authentication and test

1. Open your assigned Container App and copy its **Application URL**.
2. Open **Microsoft Entra ID** → **App registrations** → `todomanagementv2-mcp-api` → **Authentication**.
3. Add the following **Single-page application (SPA)** redirect URIs, then save:
   - `https://<mcp-app-url>/`
4. Open **Enterprise applications** → `todomanagementv2-mcp-api` → **Users and groups** → **+ Add user/group**.
5. Assign your user the **MCP Tool Executor** role.
6. Open the Container App URL, enter `MCP_CLIENT_ID` and `TENANT_ID`, then sign in.
7. Select **Test Tool** → `List Databases` → **Invoke Selected Tool**.
   ![MCP Toolkit List Databases](image/DEPLOY_GUIDE_GUI/mcp-toolkit-list-databases.png)

📖 Reference: [Azure Cosmos DB MCP Toolkit](https://github.com/AzureCosmosDB/MCPToolKit)

---

### 3.2 Create the agent

1. Open the Foundry project → **Agents** → **Create agent** → specify the agent name as `todomanagement-agent` → Create.
   ![Create agent](image/DEPLOY_GUIDE_GUI/3-06-create-agent.png)
2. Specify the following information.
   - **Model**: (`gpt-5.4-mini`)
   - **Instructions**: specify the content in [../prompt/todomanagement-agent.instructions.md](../prompt/todomanagement-agent.instructions.md)
3. **Tools**:
   1. Remove **Web search** tool
   2. Add **Azure Cosmos DB** tool
      a. **Add** → **Browse all tools**
      ![Browse all tools](image/DEPLOY_GUIDE_GUI/agent-add-tool.png)
      b. **Catalog** → search `Azure Cosmos DB` → select the tool → **Create**
      ![Select Azure Cosmos DB tool](image/DEPLOY_GUIDE_GUI/agent-search-cosmos-tool.png)
      c. **Connect tool with endpoint**
      ![Connect tool](image/DEPLOY_GUIDE_GUI/agent-connect-tool.png)
      d. **Connect the Azure Cosmos DB tool**
      - **Name**: `AzureCosmosDB`
      - **Remote MCP Server endpoint**: `<container-application-url>/mcp`, for example `https://mcp-toolkit-p01.livelyforest-279726ad.japaneast.azurecontainerapps.io/mcp`.
      - **Authentication**: `Microsoft Entra`
      - **Type**: `Project Managed Identity`
        - **Audience**: Enter your `MCP_CLIENT_ID` from Phase 2.
          ![Connect tool](image/DEPLOY_GUIDE_GUI/agent-connect-tool-02.png)
          e. Click **Connect**.
4. In **Memory**, choose **auto-create memory store** (Create memory store).
5. **Save** the agent. Note its **Name** (e.g. `todomanagement-agent`) and **Version** (`3`).
6. Test the agent.
   1. Enter the following message in the playground. Approve the tool-calling request when asked.
      `List all databases in my Cosmos DB account`
      ![Test Cosmos DB tool](image/DEPLOY_GUIDE_GUI/agent-test-cosmos-tool.png)
      📖 Reference: [https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/tool-catalog](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/tool-catalog)

---

## Phase 4. Configure and Deploy the Application

### 4.1 Set the Function App application settings

In the Function App → **Settings** → **Environment variables** → **+ Add**, add the following variables:

| Name                                | Value                                                                                                              |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `AZURE_CLIENT_ID`           　    | `<func-todomanagement-uami-client-id>`, the User Assigned Identity's **Client Id** from step 1.5        　 |
| `COSMOS_AUTO_CREATE`           　 | `true`                                                                                                  　       |
| `COSMOS_AUTH_MODE`             　 | `aad`                                                                                                   　       |
| `COSMOS_ENDPOINT`              　 | `https://<cosmos>.documents.azure.com:443/`, the endpoint from step 1.2                                 　       |
| `COSMOS_DATABASE`              　 | `todo-db`                                                                                               　       |
| `COSMOS_GREMLIN_ENDPOINT`      　 | `https://<cosmos>.documents.azure.com:443/`, the endpoint from step 1.3                                 　       |
| `COSMOS_GRAPH_DATABASE`        　 | `todo-graph-db`                                                                                         　       |
| `COSMOS_GRAPH_NAME`            　 | `todo-graph`                                                                                            　       |
| `FOUNDRY_AGENT_ENDPOINT`       　 | `https://<foundry>.services.ai.azure.com/api/projects/proj-default`, the project endpoint from step 1.4 　       |
| `FOUNDRY_EMBEDDING_DEPLOYMENT` 　 | `text-embedding-3-small`                                                                                　       |
| `FOUNDRY_AGENT_NAME`           　 | `todomanagement-agent`, the agent name from step 3.2                                                    　       |
| `FOUNDRY_AGENT_VERSION`        　 | e.g.`1`, the version from step 3.2                                                                      　       |

Click **Apply**.

> If you prefer to use a Cosmos account key, set `COSMOS_AUTH_MODE=key` and add `COSMOS_KEY=<primary key>` instead of granting RBAC.

![Function App settings](image/DEPLOY_GUIDE_GUI/function-app-settings.png)

---

### 4.2 Clone the application source in Cloud Shell

1. Open **Cloud Shell** in the Azure Portal and select **PowerShell**.
2. Clone the public repository provided by the instructor:

   ```powershell
   git clone https://github.com/Liminghao0922/todomanagement_v2.git

   $repoRoot = "$HOME/todomanagement_v2"
   Set-Location $repoRoot
   Get-ChildItem src
   ```

   The expected folders under `src` are `api` and `web`. This is the only Git command used in the participant guide; you do not need to create or sign in to a GitHub account.
3. Confirm the correct Azure subscription:

   ```powershell
   az account show --output table

   # Use this only when you need to switch subscriptions.
   # az account set --subscription "<subscription-id>"
   ```

---

### 4.3 Deploy the API with Azure Functions Core Tools

1. Check the tools available in Cloud Shell:

   ```powershell
   az version
   python --version
   func --version
   node --version
   npm --version
   ```

   Confirm Python `3.11`, Functions Core Tools `4.x`, and Node.js `20.x`. If a command is unavailable or reports a different major version, stop and ask the instructor; the instructor should verify the workshop Cloud Shell environment before the session.
2. Publish the Python application. Core Tools reads `requirements.txt` and performs the deployment build:

   ```powershell
   $functionAppName = "<your-function-app-name>"

   Set-Location "$repoRoot\src\api"
   func azure functionapp publish $functionAppName --python
   ```

   ![Function Deployed](image/DEPLOY_GUIDE_GUI/func-deployment-result.png)
3. Verify the API:

   ```powershell
   Invoke-RestMethod "https://{function-unique-domain}.azurewebsites.net/api/health"
   ```

Expected result: `status` is `healthy`.

📖 Reference: [Publish to Azure with Azure Functions Core Tools](https://learn.microsoft.com/azure/azure-functions/functions-run-local#publish-to-azure)

---

### 4.4 Build and deploy the web app with Static Web Apps CLI

The Vite settings below are build-time values. Replace every placeholder before running the build.

```powershell
$env:VITE_AZURE_CLIENT_ID = "<CLIENT_ID-from-Step-2.1>"
$env:VITE_AZURE_AUTHORITY = "https://login.microsoftonline.com/<TENANT_ID-from-Step-2.1>"
$env:VITE_AZURE_REDIRECT_URI = "https://<your-static-web-app>.azurestaticapps.net/"

Set-Location "$repoRoot\src\web"
npm ci
npm run build

# Vite does not copy this root-level file automatically.
Copy-Item staticwebapp.config.json dist/staticwebapp.config.json -Force
```

1. In the Azure Portal, open the Static Web App → **Overview** → **Manage deployment token**.
2. Copy the token. Do not paste it into the guide, chat, or a shared file.
3. Return to Cloud Shell PowerShell and set it only for the current shell session:

   ```powershell
   $env:SWA_CLI_DEPLOYMENT_TOKEN = "<paste-deployment-token>"

   npx --yes @azure/static-web-apps-cli@latest deploy ./dist `
     --env production `
     --deployment-token $env:SWA_CLI_DEPLOYMENT_TOKEN

   Remove-Item Env:SWA_CLI_DEPLOYMENT_TOKEN
   ```

📖 Reference: [Deploy with Static Web Apps CLI](https://learn.microsoft.com/azure/static-web-apps/static-web-apps-cli-deploy)

---

### 4.5 Link the Function App backend

This step makes browser requests to `/api/*` reach your separate Function App.

1. Open the Static Web App in the Azure Portal.
2. Select **Settings** → **APIs**.
3. On the **Production** row, select **Link**.
4. Set:
   - Backend resource type: **Function App**
   - Subscription: your subscription
   - Resource name: your Function App
   - Backend slot: **Production**
5. Select **Link**.
   ![Link to function](image/DEPLOY_GUIDE_GUI/swa-link-to-function.png)
   The Static Web App must use the **Standard** plan for this integration.

📖 Reference: [Bring your own functions to Azure Static Web Apps](https://learn.microsoft.com/azure/static-web-apps/functions-bring-your-own)

---

### 4.6 Deployment checkpoint

- Function health URL returns `healthy`.
- Static Web App **APIs** shows the linked Function App.
- Static Web App URL loads the sign-in page.
- No GitHub repository, service principal, secret, or workflow was created.

---

## Phase 5. Validate End-to-End

1. Open `https://<swa>.azurestaticapps.net` and sign in via MSAL.
2. **Todos** page → Click **Generate to Test Todos** (the demo seeding action) → verify todos.
   ![End-to-end check todos](image/DEPLOY_GUIDE_GUI/e2e-check-verify-todos.png)
3. **Projects** → open a seeded project → **View Graph** → confirm Cytoscape renders edges from the Gremlin graph.
   ![End-to-end check project](image/DEPLOY_GUIDE_GUI/e2e-check-verify-projects-01.png)
   ![End-to-end check view project graph](image/DEPLOY_GUIDE_GUI/e2e-check-verify-projects-02.png)
4. **Chat** → send a message such as `What should I prioritize today?` → the Foundry agent should respond and possibly invoke the `Azure Cosmos DB` tool.
   ![End-to-end check chat](image/DEPLOY_GUIDE_GUI/e2e-check-verify-chat.png)
   ![End-to-end check chat tool call](image/DEPLOY_GUIDE_GUI/e2e-check-verify-chat-tool-call.png)

---

## Phase 6. Cleanup

```powershell
az group delete --name rg-todomanagementv2-dev --yes --no-wait
```

Manually delete the Entra ID app registration (`todomanagement-spa`) under **Microsoft Entra ID → App registrations** if you no longer need it.

---

## Related Docs

- [`handson/DEPLOY_GUIDE.md`](DEPLOY_GUIDE.md)
- [`docs/ARCHITECTURE_GUIDE.md`](../docs/ARCHITECTURE_GUIDE.md)
