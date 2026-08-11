# Todo Management v2 Lab Guide (Foundry Focus, Beginner Track)

[English](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS.md) | [简体中文](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS-zh_CN.md) | [日本語](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS-ja_JP.md)

This lab focuses on a participant-owned Foundry resource, project, embedding deployment, MCP identity, Cosmos DB MCP Container App, and new Microsoft Foundry Prompt agent. The instructor prepares the shared application infrastructure, Container Apps environments, and container image before class.

Estimated time: 60-90 minutes.

---

## 1. Values And Access Required From The Instructor

Record these values before starting:

| Item                                | Your value                                            |
| ----------------------------------- | ----------------------------------------------------- |
| Participant ID                      | `<p01>`                                             |
| Tenant ID                           | `<tenant-id>`                                       |
| Todo app URL                        | `<todo-app-url>`                                     |
| Participant resource group          | `<participant-resource-group>`                      |
| Cosmos DB account name              | `<cosmos-account-name>`                             |
| Cosmos DB resource group            | `<cosmos-resource-group>`                           |
| Cosmos DB endpoint                  | `https://<cosmos-account>.documents.azure.com:443/` |
| Foundry region                      | `<foundry-region>`                                  |
| ACR login server                    | `<registry>.azurecr.io`                             |
| MCP image repository                | `mcp-toolkit`                                       |
| MCP image tag                       | `<tag>`                                             |
| Assigned Container Apps environment | `cae-todomanagement-workshop-01`                    |
| Environment resource group          | `<instructor-resource-group>`                       |
| Environment region                  | `japaneast`                                         |
| Assigned Container App name         | `mcp-toolkit-p01`                                   |

Use your participant ID in every participant-owned name:

- MCP app registration: `todomanagementv2-mcp-api-p01`
- Foundry resource: `aifoundry-todomanagement-p01`
- Foundry project: `proj-todomanagement-p01`
- Embedding deployment: `text-embedding-3-small-p01`
- Foundry connection: `AzureCosmosDB-p01`
- Foundry agent: `todomanagement-agent-p01`

Do not use another participant's ID and do not create another Container Apps environment.

Required access:

- Contributor or Owner on your participant resource group.
- Container Apps Contributor on the assigned Container Apps environment.
- DocumentDB Account Contributor on the instructor-provided Cosmos DB account.
- Permission to use the instructor ACR image through the assigned environment's system identity.
- Permission to create an app registration. If you cannot assign Enterprise Application roles, ask the instructor to perform those role assignments.

Cloud Shell PowerShell is used only for a Cosmos DB data-plane role assignment.

---

## Before You Begin: Generate Your Todo Data

Before creating your Foundry resource, initialize the Todo data associated with your participant account:

1. Open the instructor-provided `TODO_APP_URL` in a private browser window.
2. Sign in with your assigned participant account.
3. Open the **Todos** page.
4. Select **Generate 50 Test Todos** once.
5. Wait for the operation to complete and confirm that the generated todo items appear on the page.

Checkpoint:

- You can sign in to the Todo app with your participant account.
- Generated todo items are visible on the **Todos** page.

---

## 2. Create Your Foundry Resource And Project

### 2.1 Create Your Foundry Resource

1. Open the [Azure portal](https://portal.azure.com).
2. In the search bar, search for **Foundry**, then open **Foundry** under **Use with Foundry**.
3. Select **+ Create**.
4. On **Basics**, configure the resource:

   - Subscription: instructor-provided workshop subscription.
   - Resource group: your participant resource group.
   - Resource name: `aifoundry-todomanagement-p01`, replacing `p01` with your participant ID. The name must be globally unique.
   - Region: instructor-provided Foundry region， e.g.: **Japan East**.
5. Keep the instructor-provided defaults on the remaining tabs unless directed otherwise.
6. Select **Review + create** -> **Create**.
7. Wait until deployment succeeds, then select **Go to resource**.
8. On the Azure Portal **Overview** page for `FOUNDRY_RESOURCE_NAME`, select **Go to Foundry portal**.
9. Open **Home** and record:

   - Project endpoint as `FOUNDRY_PROJECT_ENDPOINT`.
   - Azure OpenAI endpoint removing /openai/v1 as `AZURE_OPENAI_ENDPOINT`, e.g,: `https://aifuondry-todomanagement-p01.openai.azure.com`.

### 2.2 Assign Foundry User Permission

1. Return to the [Azure portal](https://portal.azure.com).
2. Open the `FOUNDRY_RESOURCE_NAME` resource created in section 2.1.
3. Open **Access control (IAM)** -> **+ Add** -> **Add role assignment**.
4. On **Role**, search for and select **Foundry User**, then select **Next**.
5. On **Members**:
   - Assign access to: **User, group, or service principal**.
   - Select **+ Select members**.
   - Search for and select your participant account.
6. Select **Review + assign**, then select **Review + assign** again.
7. Open **Access control (IAM)** -> **Role assignments** and confirm your participant account has **Foundry User** at **This resource** scope.

If **Add role assignment** is unavailable, ask the instructor to assign **Foundry User** to your participant account on `FOUNDRY_RESOURCE_NAME`. Contributor access alone cannot create role assignments; this action requires Owner, User Access Administrator, or equivalent permission.

Checkpoint:

- Your participant account appears under **Role assignments** with role **Foundry User**.
- Scope is the participant-specific Foundry resource, not the subscription or instructor resource.

---

## 3. Deploy Your Models

### 3.1 Deploy `text-embedding-3-small`

1. In your Foundry project, open **Build** -> **Deployments**.
2. Select **Deploy a base model**.
3. Search for and select `text-embedding-3-small`.
4. Select **Deploy** -> **Default settings**.
5. Record the deployment name as `EMBEDDING_DEPLOYMENT_NAME`.

### 3.2 Deploy `gpt-5.4-mini`

1. In **Build** -> **Deployments**, select **Deploy a base model**.
2. Search for and select `gpt-5.4-mini`.
3. Select **Deploy** -> **Default settings**.
4. Wait until the deployment status is **Succeeded**.
5. Record the deployment name as `GPT_DEPLOYMENT_NAME`.

---

## 4. Create The MCP API Identity And Container App

### 4.1 Create The App Registration

1. Open the Azure portal.
2. Open **Microsoft Entra ID** -> **App registrations**.
3. Select **+ New registration**.
4. Enter:
   - Name: `todomanagementv2-mcp-api-p01`, replacing `p01` with your participant ID.
   - Supported account types: **Accounts in this organizational directory only**.
   - Redirect URI: leave empty for now.
5. Select **Register**.
6. On **Overview**, record:
   - **Application (client) ID** as `MCP_CLIENT_ID`.
   - **Directory (tenant) ID** as `TENANT_ID`.

### 4.2 Expose The MCP API

1. Open **Expose an API**.
2. Next to **Application ID URI**, select **Add**.
3. Accept `api://<MCP_CLIENT_ID>` and save.
4. Select **+ Add a scope**.
5. Enter:
   - Scope name: `access_as_user`
   - Who can consent: **Admins and users**
   - Admin consent display name: `Access Cosmos DB MCP Toolkit API`
   - Admin consent description: `Allow access to the Cosmos DB MCP Toolkit API on behalf of the signed-in user.`
   - User consent display name: `Access Cosmos DB MCP Toolkit API`
   - User consent description: `Allow access to the Cosmos DB MCP Toolkit API on your behalf.`
   - State: **Enabled**
6. Select **Add scope**.

### 4.3 Create The MCP Tool Executor App Role

1. Open **App roles**.
2. Select **+ Create app role**.
3. Enter:| Setting              | Value                                        |
   | -------------------- | -------------------------------------------- |
   | Display name         | `MCP Tool Executor`                        |
   | Allowed member types | **Both (Users/Groups + Applications)** |
   | Value                | `Mcp.Tool.Executor`                        |
   | Description          | `Execute Cosmos DB MCP tools`              |
   | Enable this app role | Checked                                      |
4. Select **Apply**.

### 4.4 Add Delegated API Permissions

1. Open **API permissions**.
2. Select **+ Add a permission** -> **My APIs**.
3. Select your `todomanagementv2-mcp-api-p01` app.
4. Select **Delegated permissions** -> `access_as_user` -> **Add permissions**.
5. If your tenant requires admin consent, ask the instructor to select **Grant admin consent**.

Checkpoint:

- Application ID URI is `api://<MCP_CLIENT_ID>`.
- Delegated scope `access_as_user` exists.
- App role `Mcp.Tool.Executor` allows both users and applications.

---

Private ACR image pulls use the system-assigned identity already enabled on the assigned Container Apps environment. Your Container App's own system-assigned identity is enabled separately for Cosmos DB and Foundry runtime access.

### 4.5 Create The Container App With The MCP Image

1. Search for **Container Apps** in the Azure portal.
2. Select **+ Create** -> **Container App**.
3. On **Basics**, enter:

   - Resource group: your participant resource group.
   - Container app name: your assigned unique name, such as `mcp-toolkit-p01`.
   - Region: the instructor-provided environment region.
   - Container Apps environment: select the environment assigned by the instructor.
4. On **Container**:

   - Clear **Use quickstart image**.
   - Image source: **Azure Container Registry**
   - Registry: instructor-provided ACR
   - Image: instructor-provided `mcp-toolkit` repository
   - Image tag: instructor-provided tag
   - Authentication type: **Managed identity**
   - Managed identity: select **System assigned** for the assigned Container Apps environment
   - CPU: `0.5`
   - Memory: `1 GiB`
5. Add these environment variables:

   | Name                            | Value                                  |
   | ------------------------------- | -------------------------------------- |
   | `AzureAd__ClientId`           | Your`MCP_CLIENT_ID`                  |
   | `AzureAd__TenantId`           | Your`TENANT_ID`                      |
   | `AzureAd__Audience`           | Your`MCP_CLIENT_ID`                  |
   | `COSMOS_ENDPOINT`             | Instructor-provided Cosmos DB endpoint |
   | `OPENAI_ENDPOINT`             | Your`AZURE_OPENAI_ENDPOINT`          |
   | `OPENAI_EMBEDDING_DEPLOYMENT` | Your`EMBEDDING_DEPLOYMENT_NAME`      |
   | `ASPNETCORE_ENVIRONMENT`      | `Production`                         |
   | `ASPNETCORE_URLS`             | `http://+:8080`                      |

   ![1786453747959](image/DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS/1786453747959.png)
6. On **Ingress**:

   - Ingress: **Enabled**
   - Ingress traffic: **Accepting traffic from anywhere**
   - Ingress type: **HTTP**
   - Target port: `8080`

   ![1786453787990](image/DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS/1786453787990.png)
7. Select **Review + create** -> **Create**.
8. Wait until the revision reports **Running**.
9. Copy the Container App **Application URL** as `MCP_APP_URL`.

If the assigned environment is not selectable, stop and ask the instructor to verify your Container Apps Contributor assignment. Do not create a replacement environment.

If the private image cannot be pulled, verify that the environment system identity has `AcrPull` and that **System assigned** is selected for registry authentication.

### 4.6 Enable The Container App Managed Identity

1. Open your Container App.
2. Open **Settings** -> **Identity** -> **System assigned**.
3. Set **Status** to **On** and select **Save**.
4. Record the **Object (principal) ID** as `MCP_PRINCIPAL_ID`.

### 4.7 Grant The Identity Access To Cosmos DB

First grant the control-plane reader role:

1. Open the instructor-provided Cosmos DB for NoSQL account.
2. Open **Access control (IAM)** -> **+ Add role assignment**.
3. Select **Cosmos DB Account Reader Role**.
4. Assign it to your Container App's system-assigned managed identity.

Then open Azure Cloud Shell and select **PowerShell**. Run:

```powershell
$cosmosResourceGroup = "<cosmos-resource-group>"
$cosmosAccountName = "<cosmos-account-name>"
$cosmosAccountId = az cosmosdb show `
   --resource-group $cosmosResourceGroup `
   --name $cosmosAccountName `
   --query id `
   --output tsv

$mcpPrincipalId = "<MCP_PRINCIPAL_ID>"

az cosmosdb sql role assignment create `
  --resource-group $cosmosResourceGroup `
  --account-name $cosmosAccountName `
  --role-definition-id "00000000-0000-0000-0000-000000000001" `
  --principal-id $mcpPrincipalId `
  --scope $cosmosAccountId
```

The role ID ending in `0001` is **Cosmos DB Built-in Data Reader**.

### 4.9 Grant The Identity Access To Foundry

1. Open your participant-specific Foundry resource in the Azure portal.
2. Open **Access control (IAM)** -> **+ Add role assignment**.
3. Select **Foundry User**.
4. Assign it to your Container App's system-assigned managed identity.
5. Open **Access control (IAM)** -> **Role assignments** and confirm the role is assigned to `MCP_PRINCIPAL_ID` at **This resource** scope.
6. Wait at least five minutes for Azure RBAC propagation before testing.

`Foundry User` includes the Foundry and Azure OpenAI data-plane permissions required to generate embeddings. Do not add another inference role for this lab.

### 4.10 Configure Redirect URIs

1. Open **Microsoft Entra ID** -> **App registrations** -> your MCP app registration.
2. Open **Authentication**.
3. Select **+ Add a platform** -> **Single-page application**.
4. Add both redirect URIs:
   - `https://<your-container-app-hostname>/`
5. Save the configuration.

### 4.11 Assign MCP Tool Executor

Assign the role to your user:

1. Open **Microsoft Entra ID** -> **Enterprise applications**.
2. Find your `todomanagementv2-mcp-api-p01` application.
3. Open **Users and groups** -> **+ Add user/group**.
4. Select your user and role **MCP Tool Executor**.
5. Complete the assignment.

Assign the same role to the Foundry project's managed identity:

1. In the same Enterprise Application, select **+ Add user/group**.
2. Select the managed identity named `<foundry-account-name>/projects/<project-name>`.
3. Select role **MCP Tool Executor** and complete the assignment.

If the portal cannot select the project managed identity, ask the instructor to perform this assignment. This Entra permission is separate from Azure subscription RBAC.

### 4.12 Test The MCP Toolkit Directly

1. Open `MCP_APP_URL` in a private browser window.
2. Enter your `MCP_CLIENT_ID` and `TENANT_ID` if prompted.
3. Sign in.
4. Open **Test Tool**.
5. Select **List Databases** and invoke it.
6. Select **Vector Search** and enter:
   - Database: `todo-db`
   - Container: `todos`
   - Search text: `adoption-plan`
   - Vector Property: `embeddings`
   - Select Properties: `title,description`
7. Invoke the tool.
![1786454636662](image/DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS/1786454636662.png)

Expected results:

- **List Databases** returns `todo-db`.
- **Vector Search** returns matching todo items without `401 Unauthorized`.

If **List Databases** succeeds but **Vector Search** returns `401 Unauthorized`, first verify that `OPENAI_ENDPOINT` uses the Azure OpenAI endpoint `https://<your-foundry-resource>.openai.azure.com/`, not the Project endpoint containing `/api/projects/`. Then verify the Container App system identity has **Foundry User**, wait for RBAC propagation, restart the Container App, and test again.

Do not continue until both direct MCP tests succeed.

---

## 5. Create A New Foundry Prompt Agent

### 5.1 Create A Participant-Unique Agent

1. Return to your participant-specific project in the Microsoft Foundry portal.
2. Open **Build** -> **Agents**.
3. Select **New agent** -> **Build an agent**.
4. Enter agent name `todomanagement-agent-p01`, replacing `p01` with your participant ID.
5. Select the model deployment recorded as `GPT_DEPLOYMENT_NAME` in section 3.2.

### 5.2 Enter Agent Instructions

Paste the following directly into **Instructions**:

```text
You are an intelligent Todo Management Assistant that helps users organize, prioritize, and manage tasks.

Communication rules:
- Be concise and actionable.
- Use numbered or bulleted lists.
- Ask a focused clarifying question only when a required identifier is missing.
- Ground answers in tool results rather than generic productivity advice.

Cosmos DB data:
- Database: todo-db
- Containers: todos, projects, owners, conversations
- Always preserve owner_id boundaries when reading or changing data.

Tool-first rules:
- For requests such as "What should I prioritize today?", "What should I work on next?", "Which todos should I delegate?", or "Summarize my top risks", call the Cosmos DB MCP tool before answering.
- Query incomplete todos first.
- Query related projects when project context is required.
- Rank tasks by overdue/today/this-week urgency, then impactScore, then priority.
- Prefer incomplete work unless the user explicitly requests a retrospective.
- If no matching data exists, state that clearly and ask one focused follow-up question.

When suggesting tasks, return:
1. Task title
2. Why it matters
3. Priority or urgency
4. Recommended next action
```

### 5.3 Add Your Azure Cosmos DB MCP Tool

1. In the agent editor, remove **Web search** if it was added automatically.
2. Select **Add** -> **Browse all tools**.
3. Search for and select **Azure Cosmos DB**.
4. Create a new connection using:| Setting                    | Value                                           |
   | -------------------------- | ----------------------------------------------- |
   | Connection name            | `AzureCosmosDB-p01` using your participant ID |
   | Remote MCP Server endpoint | `https://<your-container-app-hostname>/mcp`   |
   | Authentication             | **Microsoft Entra**                       |
   | Authentication type        | **Project Managed Identity**              |
   | Audience                   | Your`MCP_CLIENT_ID`                           |
![1786454765316](image/DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS/1786454765316.png)
5. Select **Connect**.
6. Confirm the tool appears in the agent's tool list.
7. Save the agent and confirm the new version is **Running** or **Active**.

Use a unique connection name so it remains easy to map the connection to your participant-owned project and Container App.

### 5.4 Test The Agent

Run these prompts in order:

1. `List all databases in my Cosmos DB account.`
2. `List containers in database todo-db.`
3. `What should I prioritize today?`

Expected behavior:

- The Agent invokes your participant-specific Azure Cosmos DB MCP tool.
- `todo-db` appears in the first response.
- Tool results come from Cosmos DB rather than model-only knowledge.
- The prioritization response cites concrete todos returned by the tool.
- When running prompt 3, you may be asked to provide an `owner_id`. In the Azure portal, open **Microsoft Entra ID**, search for your user principal name (UPN), select your account, and copy the **Object ID** from the **Overview** page.
![1786455087699](image/DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS/1786455087699.png)

If Foundry requests tool approval, review the tool name and arguments, then approve the call.

---

## 6. Inspect Traces And Tune Instructions

### 6.1 Inspect A Trace

1. Open **Traces** for the agent conversation.
![1786455569486](image/DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS/1786455569486.png)
2. Verify that the final answer is grounded in the tool result.

### 6.2 Tune The Instructions

Add this constraint to the Agent instructions:

```text
For prioritization requests, return exactly five items in a Markdown table with columns Rank, Todo, Reason, and Next action.
```

Click **Save** to create a new Agent version, rerun the same prompt, and compare:

- Whether the same tool is called
- Whether tool arguments changed
- Whether the output format improved
- Whether the answer remains grounded in Cosmos DB data

---

## 7. Completion Criteria

The lab is complete when:

- Your MCP API app registration has `access_as_user` and `Mcp.Tool.Executor`.
- Your participant-specific Foundry resource and project exist in your participant resource group.
- Your participant-specific `text-embedding-3-small` deployment has succeeded.
- Your `gpt-5.4-mini` deployment has succeeded.
- Your Container App runs the instructor-provided MCP image using managed identity authentication.
- Direct **List Databases** testing returns `todo-db`.
- Your new Prompt agent has a participant-unique name and connection.
- The Agent calls Cosmos DB MCP successfully.
- You can explain one trace from prompt through tool call to final response.
- You saved and compared at least one instruction change.

---

## 8. Troubleshooting

| Symptom                                                          | Check                                                                                                                                                      |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Cannot create a Foundry resource                                 | Verify Contributor or Owner access on your participant resource group and`Microsoft.CognitiveServices` provider registration.                            |
| Cannot create a Foundry project                                  | Verify that your participant-specific Foundry resource deployed successfully and is selected.                                                              |
| Embedding deployment fails                                       | Verify`text-embedding-3-small` availability, deployment type, participant-unique deployment name, and quota.                                             |
| Assigned Container Apps environment is not selectable            | Verify subscription and Container Apps Contributor assignment on that environment.                                                                         |
| ACR image is not selectable or revision shows image pull failure | Verify the environment system identity has`AcrPull` and select **System assigned** for managed identity registry authentication.                   |
| Container revision does not start                                | Verify target port`8080`, `ASPNETCORE_URLS`, image tag, and all required environment variables.                                                        |
| MCP UI sign-in fails                                             | Verify both redirect URIs, tenant ID, client ID, and user`MCP Tool Executor` assignment.                                                                 |
| Direct List Databases returns 403                                | Verify Cosmos DB Account Reader and Cosmos DB Built-in Data Reader assignments for the Container App identity.                                             |
| Vector Search returns 401                                        | Set`OPENAI_ENDPOINT` to `https://<your-foundry-resource>.openai.azure.com/`; verify the Container App identity has Foundry User, then restart the app. |
| Foundry tool returns 401 or 403                                  | Verify the Foundry project managed identity has`MCP Tool Executor` on your Enterprise Application.                                                       |
| Foundry connection name already exists                           | Use your participant-specific name, such as`AzureCosmosDB-p01`.                                                                                          |
| Agent shows Classic migration messaging                          | Ensure you created**New agent -> Prompt agent**, not a Classic agent or Assistant.                                                                   |
| Agent answers without calling tools                              | Strengthen the tool-first instruction and explicitly request Cosmos DB evidence.                                                                           |

Ask the instructor before changing the shared ACR or Container Apps environment settings. Only change your participant-specific Foundry resource and project.
