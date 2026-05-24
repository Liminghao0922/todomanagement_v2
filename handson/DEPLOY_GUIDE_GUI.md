# Todo Management v2 Deployment Guide (Azure Portal track)

[English](DEPLOY_GUIDE_GUI.md) | [简体中文](DEPLOY_GUIDE_GUI-zh_CN.md) | [日本語](DEPLOY_GUIDE_GUI-ja_JP.md)

This guide follows the beginner-friendly path. Every Azure resource is created from the Azure Portal UI, with code-only steps reduced to copy-and-paste blocks. For the IaC-driven path, see [`DEPLOY_GUIDE.md`](DEPLOY_GUIDE.md).

Estimated time: 90–120 minutes.

---

## Terminology Used in This Guide

| Term                           | Meaning in this hands-on                                                                                                                    |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **Resource Group**       | Logical container for all v2 resources (default name `rg-todomanagementv2-dev`).                                                          |
| **Function App**         | Azure Functions on a Linux Flex Consumption plan that hosts `src/api/`.                                                                  |
| **Static Web App (SWA)** | Hosts the Vue 3 SPA built from `src/web/`.                                                                                                |
| **Cosmos DB serverless** | Stores SQL containers (`todos` / `owners` / `projects` / `conversations`) and the Gremlin graph (`todo-graph-db`/`todo-graph`). |
| **Microsoft Foundry**    | Provides `gpt-5.4-mini` and `text-embedding-3-small`.                                                                                   |
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
9. Open the account → **Data Explorer** → **New Database** → ID `todo-db`. Then create four containers:

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
4. Open the foundry resource → **Go to Foundry portal**, copy the `Project endpoint` and save it.
5. **Build** → **Models** → **Deploy a base model** → search `text-embedding-3-small`
6. Select `text-embedding-3-small`, click **Deploy** → select **Default settings**
![Deploy text-embedding-3-small](image/DEPLOY_GUIDE_GUI/08-deploy-embedding-model.png)
7. **Build** → **Models** → **Deploy a base model** → search `gpt-5.4-mini`
8. Select `gpt-5.4-mini`, click **Deploy** → select **Default settings**
![Deploy gpt-5.4-mini](image/DEPLOY_GUIDE_GUI/09-deploy-gpt-model.png)

---

### 1.5 Create the Function App + Storage

1. Search **Function App** → **+ Create**.
2. Select `Flex Consumption`
3. **Basics**:
   - Resource group: `rg-todomanagementv2-dev`
   - Function App name: `func-todomanagement`, and enable **Secure unique default hostname**.
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
6. Optional. If you want to run this locally, add the redirect URI in **Authentication** → **+ Add URI** → `http://localhost:5173/`, then save.
7. From the **Overview** page, copy:
    - **Application (client) ID** → save as `CLIENT_ID`
    - **Directory (tenant) ID** → save as `TENANT_ID`

📖 Reference: [https://learn.microsoft.com/entra/identity-platform/quickstart-register-app](https://learn.microsoft.com/entra/identity-platform/quickstart-register-app)

![SPA app registration](image/DEPLOY_GUIDE_GUI/register-an-application.png)

---

### 2.2 Grant the Function App's managed identity access to Cosmos, Foundry, and the Cosmos MCP Toolkit

1. Assign `Cosmos DB Built-in Data Contributor` role to Function App's User Assigned Managed Identity.
   a. Open **Cloud Shell** and click **Switch to PowerShell** if the current session is not PowerShell from Azure Portal.
   ![Switch to Bash](image/DEPLOY_GUIDE_GUI/cloudshell-switch-to-powershell.png)
   b. Run this command:

   ```bash
   az cosmosdb sql role assignment create \
    --account-name "<your-cosmos-db-account-name>" \
    --resource-group "<your-resource-group-name>" \
    --role-definition-id "00000000-0000-0000-0000-000000000002" \
    --principal-id "<your-azure-function-uami-id>" \
    --scope "/"

   az cosmosdb sql role assignment create \
    --account-name "<your-cosmos-gremlin-db-account-name>" \
    --resource-group "<your-resource-group-name>" \
    --role-definition-id "00000000-0000-0000-0000-000000000002" \
    --principal-id "<your-azure-function-uami-id>" \
    --scope "/"
   ```

   ![Assign Cosmos DB Built-in Data Contributor role to Function App](image/DEPLOY_GUIDE_GUI/assign-cosmos-role-to-func.png)
   📖 Reference: [https://learn.microsoft.com/azure/cosmos-db/how-to-setup-rbac](https://learn.microsoft.com/azure/cosmos-db/how-to-setup-rbac)
2. Open the Foundry **project** → **Access control (IAM)** → **+ Add role assignment**:

   - Role `Foundry User`
   - Assign access to: **Managed identity** → select the **func-todomanagement-uami**.
     ![Assign Foundry User role to Function App](image/DEPLOY_GUIDE_GUI/assign-foundry-role-to-func.png)
3. Grant the `MCP Tool Executor` role to the Function App's managed identity.
   a. Open **Cloud Shell** and click **Switch to PowerShell** if the current session is not PowerShell from Azure Portal.
   ![Switch to Bash](image/DEPLOY_GUIDE_GUI/cloudshell-switch-to-bash.png)
   b. Run this command:

   ```powershell
   $TenantDomain = "<Specify your tenant id>"
   $ResourceName = "Azure Cosmos DB MCP Toolkit API"
   $AppRoleName = "Mcp.Tool.Executor"
   $PrincipalName = "foundry-todomanagement-v2/projects/proj-default"
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

1. Open the GitHub repository [https://github.com/AzureCosmosDB/MCPToolKit#option-a-deploy-to-azure-button](https://github.com/AzureCosmosDB/MCPToolKit#option-a-deploy-to-azure-button)
2. Click **Deploy to Azure**

   - Resource Group: `rg-todomanagementv2-dev`
   - Region: same as RG
   - Cosmos Endpoint: specify the Cosmos DB account created in step 2, for example `https://cosmos-todomanagement-v2.documents.azure.com:443/`
   - Azure AI Service Endpoint: specify the Foundry project endpoint, for example `https://foundry-todomanagement-v2.services.ai.azure.com/api/projects/proj-default`
   - Embedding Deployment Name: `text-embedding-3-small`
3. **Review + create** → **Create**.
   ![Deploy cosmos MCP](image/DEPLOY_GUIDE_GUI/3-01-depoly-cosmos-mcp.png)
4. Deploy the MCP Server application.
   a. Open **Cloud Shell** and click **Switch to PowerShell** if the current session is not PowerShell from Azure Portal.
   ![Switch to PowerShell](image/DEPLOY_GUIDE_GUI/cloudshell-switch-to-powershell.png)
   b. Clone the repository with the following command.

   ```powershell
   git clone https://github.com/AzureCosmosDB/MCPToolKit.git
   cd MCPToolKit
   ```

   c. Modify the script. Because we run the PowerShell script from Cloud Shell, Docker is not supported.

   ```powershell
    copy ./scripts/Deploy-Cosmos-MCP-Toolkit.ps1 ./scripts/Deploy-Cosmos-MCP-Toolkit-CloudShellVersion.ps1
   ```

   Click **Editor** and open `Deploy-Cosmos-MCP-Toolkit-CloudShellVersion.ps1`.
   Go to line 851 and change it as shown below.

   ```powershell
   az acr login --name $ACR_NAME --resource-group $script:ACR_RESOURCE_GROUP --expose-token
   ```

   Go to line 870, and comment out lines 870-882.
   Replace line 870 with the following command.

   ```powershell
   az acr build -r $ACR_NAME --platform linux/amd64 -f Dockerfile.runtime . -t $IMAGE_TAG
   ```

   ![modify script](image/DEPLOY_GUIDE_GUI/3-02-modify-script.png)

   d. Run the deployment script from the repository root:

   ```powershell
   .\scripts\Deploy-Cosmos-MCP-Toolkit-CloudShellVersion.ps1 -ResourceGroup "rg-todomanagementv2-dev"
   ```

5. Test Your Deployment
   a. Search **Container Apps** → click the newly created container app **mcp-toolkit-app**.
   b. Click **Application Url** to open the MCP app in a new tab.
   c. Open **Cloud Shell** and click **Switch to Bash** if the current session is not Bash from Azure Portal.
   ![switch to bash](image/DEPLOY_GUIDE_GUI/cloudshell-switch-to-bash.png)
   d. Execute the following command to get client id, tenant id, and save them.

   ```bash
   az ad app list --display-name "Azure Cosmos DB MCP Toolkit API" --query "[0].appId" -o tsv
   az account show --query "tenantId" -o tsv
   ```

   e. Enter the client ID and tenant ID in the MCP app, then click **Sign In with Microsoft Entra**.
   ![sign in with entra](image/DEPLOY_GUIDE_GUI/3-04-sign-in-with-entra.png)
   f. **Test Tool** → **Select Tool** as `List Databases`  → **Invoke Selected Tool** and make sure the correct result can be returned.
   ![Test tool List Databases](image/DEPLOY_GUIDE_GUI/3-05-test-tool.png)

📖 Reference: [https://github.com/AzureCosmosDB/MCPToolKit](https://github.com/AzureCosmosDB/MCPToolKit)

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
      - **Remote MCP Server endpoint**: `<container-application-url>/mcp`, eg `https://mcp-toolkit-app.livelyforest-279726ad.japaneast.azurecontainerapps.io/mcp`.
      - **Authentication**: `Microsoft Entra`
      - **Type**: `Project Managed Identity`
      - **Audience**: Enter your `<entra-app-client-id>` as the audience. This is the value from the output for `az ad app list --display-name "Azure Cosmos DB MCP Toolkit API" --query "[0].appId" -o tsv`.
        ![Connect tool](image/DEPLOY_GUIDE_GUI/agent-connect-tool-02.png)
        e. Click **Connect**.
4. **Memory** → **Add** → **Create memory store**.
5. **Save** the agent. Note its **Name** (e.g. `todomanagement-agent`) and **Version** (`3`).
6. Test the agent.
   1. Enter the following message in the playground. Approve the tool-calling request when asked.
      `List all databases in my Cosmos DB account`
      ![Test Cosmos DB tool](image/DEPLOY_GUIDE_GUI/agent-test-cosmos-tool.png)
   2. Enter the following message in the playground. Approve the tool-calling request when asked.
      `List all meetings in my calendar`
      ![Test WorkIQ Calendar tool](image/DEPLOY_GUIDE_GUI/agent-test-calendar-tool.png)
      📖 Reference: [https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/tool-catalog](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/tool-catalog)

---

## Phase 4. Configure and Deploy the Application

### 4.1 Set the Function App application settings

In the Function App → **Settings** → **Environment variables** → **+ Add**, add the following variables:

| Name                             | Value                                                                                                     |
| -------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `COSMOS_AUTH_MODE`             | `aad`                                                                                                   |
| `COSMOS_AUTO_CREATE`           | `true`                                                                                                  |
| `COSMOS_ENDPOINT`              | `https://<cosmos>.documents.azure.com:443/`, the endpoint from step 1.2                                 |
| `COSMOS_DATABASE`              | `todo-db`                                                                                               |
| `COSMOS_GREMLIN_ENDPOINT`      | `https://<cosmos>.documents.azure.com:443/`, the endpoint from step 1.3                                 |
| `COSMOS_GRAPH_DATABASE`        | `todo-graph-db`                                                                                         |
| `COSMOS_GRAPH_NAME`            | `todo-graph`                                                                                            |
| `FOUNDRY_AGENT_ENDPOINT`       | `https://<foundry>.services.ai.azure.com/api/projects/proj-default`, the project endpoint from step 1.4 |
| `FOUNDRY_EMBEDDING_DEPLOYMENT` | `text-embedding-3-small`                                                                                |
| `FOUNDRY_AGENT_NAME`           | `todomanagement-agent`, the agent name from step 3.2                                                    |
| `FOUNDRY_AGENT_VERSION`        | e.g.`1`, the version from step 3.2                                                                      |

Click **Apply**.

> If you prefer to use a Cosmos account key, set `COSMOS_AUTH_MODE=key` and add `COSMOS_KEY=<primary key>` instead of granting RBAC.

![Function App settings](image/DEPLOY_GUIDE_GUI/function-app-settings.png)

---

### 4.2 Repository Setup

Create your repository from the template. See [Creating a repository from a template (GitHub Docs)](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template).

1. Open the [template repository](https://github.com/Liminghao0922/todomanagement_v2)
2. Click **Use this template** → **Create a new repository**
3. Set:
   - **Repository name**: for example `my-todo-app-v2`
   - **Visibility**: `Public` (recommended for this workshop flow)
4. Click **Create repository from template**
5. Wait for the repository to be created

---

### 4.3 GitHub Actions Configuration

Configure GitHub Actions with your Azure credentials and resource details first, then enable workflow files to avoid empty/failed initial runs.

#### 4.3.1 Create Azure Service Principal and Credentials

Reference: [Create an Azure service principal (MS Learn)](https://learn.microsoft.com/en-us/azure/developer/github/publish-docker-container)

1. Open **Azure Cloud Shell** in Azure Portal
2. Run this command to create a service principal scoped to your resource group:

   ```powershell
   # Check current subscription
   az account show

   # Switch to a different subscription (if needed)
   # Replace `<subscription-id>` with your subscription ID from Phase 1 summary (Step 1.9).
   az account set --subscription "<subscription-id>"

   # Set variables
   $subscriptionId = $(az account show --query id -o tsv)
   $spName = "github-todomanagementv2-ci"
   # Replace with your resource group name from Phase 1 summary (Step 1.9) if you changed it.
   $resourceGroupName = "rg-todomanagementv2-dev"
   # Create service principal
   $sp = az ad sp create-for-rbac `
   --name $spName `
   --role "Owner" `
   --scopes "/subscriptions/$subscriptionId/resourceGroups/$resourceGroupName" `
   --json-auth | ConvertFrom-Json

   # Output as JSON (for later use)
   $sp | ConvertTo-Json
   ```
3. Copy the JSON output (the entire `{...}` block)

**Note:** This JSON output is sensitive. Keep it secure.

---

#### 4.3.2 Add GitHub Actions Secret

1. In your GitHub repository, go to **Settings**
2. In the left menu, click **Secrets and variables** > **Actions** > click **New repository secret**, and add these repository secrets.| Variable                            | Value                                                  | Reference       |
   | ----------------------------------- | ------------------------------------------------------ | --------------- |
   | `AZURE_CREDENTIALS`               | Application's credentials JSON                         | From Step 4.3.1 |
   | `AZURE_STATIC_WEB_APPS_API_TOKEN` | Your Static Web App's**Manage deployment token** | From Step 1.6   |

 ![Add AZURE_CREDENTIALS secret](image/DEPLOY_GUIDE_GUI/github-add-cred.png)

---

#### 4.3.3 Add GitHub Repository Variables

Reference: [Using variables in GitHub Actions (GitHub Docs)](https://docs.github.com/en/actions/learn-github-actions/variables)

In your GitHub repository **Settings** > **Secrets and variables** > **Actions**, click **Variables**, and add these repository variables:

| Variable               | Value                                               | Reference     |
| ---------------------- | --------------------------------------------------- | ------------- |
| `AZURE_CLIENT_ID`    | Entra ID App Client ID                              | From Step 2.1 |
| `AZURE_TENANT_ID`    | Entra ID App Tenant ID                              | From Step 2.1 |
| `AZURE_REDIRECT_URI` | Your static web App URL                             | From Step 1.6 |
| `FUNCTION_APP_NAME`  | Your function app name, e.g.`func-todomanagement` | From Step 1.5 |

---

#### 4.3.4 Prepare workflow files

Reference: [GitHub Actions documentation](https://docs.github.com/en/actions)

After secrets and variables are configured, enable workflow files.

In your repository, CI/CD workflow files are provided as templates:

- `.github/workflows/build-deploy-api.yml.template` → rename to `build-deploy-api.yml`
- `.github/workflows/build-deploy-web.yml.template` → rename to `build-deploy-web.yml`

To create the files:

1. Open **Azure Cloud Shell** in Azure Portal
2. Run this command:

```powershell
git clone <your-repo-url>
cd my-todo-app

# Copy templates without .template extension
cp .github/workflows/build-deploy-api.yml.template .github/workflows/build-deploy-api.yml
cp .github/workflows/build-deploy-web.yml.template .github/workflows/build-deploy-web.yml

# Commit and push
git add .github/workflows/*.yml
git commit -m "Enable API and Web build-deploy workflows"
git push origin main
```

---

#### 4.3.5 Run GitHub Actions Workflows

1. In your repository, go to the **Actions** tab
2. You should see both workflows listed:
   - `Build and Deploy API to ACR`
   - `Build and Deploy Web to ACR`
3. If workflows don't show, ensure:
   - `.github/workflows/build-deploy-api.yml` and `.github/workflows/build-deploy-web.yml` are committed to `main`
4. The workflows should trigger automatically on commits to the `main` branch.
5. Click on each workflow and monitor:
   - Check for any **red X** (failures) or **green checkmark** (success)
   - Both should complete within 5-10 minutes each

**Troubleshooting workflow failures:**

- Check **AZURE_CREDENTIALS** is valid JSON
- Ensure all variables are filled
- Check that Azure resources exist and names match exactly

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
