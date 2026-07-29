# Todo Management v2 部署指南（Azure 门户路径）

[English](DEPLOY_GUIDE_GUI.md) | [简体中文](DEPLOY_GUIDE_GUI-zh_CN.md) | [日本語](DEPLOY_GUIDE_GUI-ja_JP.md)

本指南采用适合初学者的路径。学习者不需要 GitHub 账户，也不需要具备 Git 使用经验：Azure 资源通过 Azure 门户创建，应用程序则从 Azure Cloud Shell 构建并部署。讲师按照 [`INSTRUCTOR_PREP_GUIDE-zh_CN.md`](INSTRUCTOR_PREP_GUIDE-zh_CN.md) 准备共享的 MCP 容器映像。有关 IaC 驱动的路径，请参阅 [`DEPLOY_GUIDE.md`](DEPLOY_GUIDE.md)。

预计耗时：90–120 分钟。

---

## 开始之前

请从讲师处获取以下八项信息：

- Todo Management v2 公共存储库 URL
- 工作坊 ACR 登录服务器，例如 `workshopacr.azurecr.io`
- MCP 映像名称 `mcp-toolkit`
- MCP 映像标记，例如 `workshop-20260727`
- 分配给你的 Container Apps 环境，例如 `cae-todomanagement-workshop-01`
- 环境资源组，例如 `rg-todomanagement-instructor`
- 环境区域，例如 `japaneast`
- 你的唯一 Container App 名称，例如 `mcp-toolkit-p01`

你只需要浏览器、Internet 访问、Azure 订阅，以及使用 [Azure Cloud Shell](https://learn.microsoft.com/azure/cloud-shell/overview) 的权限。当 Cloud Shell 询问要使用的 shell 时，请选择 **PowerShell**。

你将按照以下路线操作：

1. 在门户中创建 Azure 资源。
2. 配置两个 Entra 应用注册和托管标识。
3. 将讲师提供的 MCP 映像部署到 Container Apps。
4. 创建并连接 Foundry Agent。
5. 克隆公共源代码，并从 Cloud Shell 部署 API 和 Web 应用。
6. 测试应用程序，然后删除工作坊资源。

你无需创建 GitHub 存储库、凭据、机密或工作流。

---

## 本指南使用的术语

| 术语 | 在本次动手实验中的含义 |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- |
| **资源组** | 所有 v2 资源的逻辑容器（默认名称为 `rg-todomanagementv2-dev`）。 |
| **Function App** | 运行在 Linux Flex Consumption 计划上的 Azure Functions，用于托管 `src/api/`。 |
| **Static Web App (SWA)** | 托管从 `src/web/` 构建的 Vue 3 SPA。 |
| **Cosmos DB Serverless** | 存储 SQL 容器（`todos` / `owners` / `projects` / `conversations`）以及 Gremlin 图（`todo-graph-db`/`todo-graph`）。 |
| **Microsoft Foundry** | 提供 `gpt-5.4-mini` 和 `text-embedding-3-small`。 |
| **应用注册** | 用于 SPA 登录以及可选的服务器到 Foundry 授权的 Entra ID 标识。 |
| **托管标识** | Function App 的系统分配标识，用于获取 Cosmos Gremlin 和 Azure OpenAI 的 AAD 令牌。 |

---

## 阶段 1：通过 Azure 门户创建基础设施

### 1.1 创建资源组

1. 打开 `https://portal.azure.com` 并登录。
2. 搜索 **Resource groups** → **+ Create**。
3. Subscription：选择你的订阅。**Resource group**：`rg-todomanagementv2-dev`。**Region**：`Japan East`（或任何同时支持 Cosmos + Foundry + Functions Linux + SWA 的区域）。
4. 选择 **Review + create** → **Create**。

📖 参考：[https://learn.microsoft.com/azure/azure-resource-manager/management/manage-resource-groups-portal](https://learn.microsoft.com/azure/azure-resource-manager/management/manage-resource-groups-portal)

![创建资源组](image/DEPLOY_GUIDE_GUI/01-create-rg.png)

---

### 1.2 创建用于 NoSQL 的 Cosmos DB 账户

1. 搜索 **Azure Cosmos DB** → **+ Create**。
2. API：选择 **Azure Cosmos DB for NoSQL**。
3. **Basics**：

   - Workload Type：`Learning`
   - Resource group：`rg-todomanagementv2-dev`
   - Account name：`cosmos-todomanagement-<unique>`（小写字母/数字）
   - Availability Zones：`Disable`
   - Location：与资源组相同
   - Capacity mode：**Serverless**
4. **Global distribution**：

   - Geo-Redundancy：`Disable`
   - Multi-region Writes：`Disable`
5. **Networking**：

   - Connectivity method：`All networks`，如有需要可稍后限制。
6. **Backup Policy**：保持默认即可。
7. **Security**：

   - Key-based Authentication：`Disable`，我们将使用 Entra ID 进行身份验证。
   - Data Encryption：`Service-managed key`
8. 选择 **Review + create** → **Create**。
   ![创建 Cosmos DB 账户](image/DEPLOY_GUIDE_GUI/02-create-cosmos.png)
   预配完成后：
9. 打开该账户 → **Data Explorer** → **New Database** → ID 填写 `todo-db`。然后创建以下四个容器：

   | 容器 | 分区键 |
   | ----------------- | ------------- |
   | `todos` | `/owner_id` |
   | `owners` | `/id` |
   | `projects` | `/owner_id` |
   | `conversations` | `/owner_id` |

![Cosmos 容器](image/DEPLOY_GUIDE_GUI/03-cosmos-containers.png)
📖 参考：[https://learn.microsoft.com/azure/cosmos-db/nosql/quickstart-portal](https://learn.microsoft.com/azure/cosmos-db/nosql/quickstart-portal)

---

### 1.3 创建用于 Gremlin API 的 Azure Cosmos DB 账户

1. 搜索 **Azure Cosmos DB** → **+ Create**。
2. API：选择 **Azure Cosmos DB for Apache Gremlin**。
   ![选择 Azure Cosmos DB for Apache Gremlin](image/DEPLOY_GUIDE_GUI/04-cosmosgre-select-api.png)
3. **Basics**：

   - Workload Type：`Learning`
   - Resource group：`rg-todomanagementv2-dev`
   - Account name：`cosmosgre-todomanagement-<unique>`（小写字母/数字）
   - Availability Zones：`Disable`
   - Location：与资源组相同
   - Capacity mode：**Serverless**
4. **Global distribution**：

   - Geo-Redundancy：`Disable`
   - Multi-region Writes：`Disable`
5. **Networking**：

   - Connectivity method：`All networks`，如有需要可稍后限制。
6. **Backup Policy**：保持默认即可。
7. **Security**：

   - Data Encryption：`Service-managed key`
8. 选择 **Review + create** → **Create**。
   ![创建 Cosmos DB 账户](image/DEPLOY_GUIDE_GUI/05-create-cosmosgre.png)
   预配完成后：
9. 打开该账户 → **Data Explorer** → **New Graph**：

   - **Database id**：`todo-graph-db`
   - **Graph id**：`todo-graph`
   - **Partition key**：`/owner_id`
     ![创建图](image/DEPLOY_GUIDE_GUI/06-create-cosmosgre-graph.png)

---

### 1.4 创建 Foundry 资源并部署模型

1. 搜索 **Microsoft Foundry** → **Foundry** → **+ Create**。
2. **Basics**：
   - Resource group：`rg-todomanagementv2-dev`
   - Name：`foundry-todomanagement-<unique>`（小写字母/数字）
   - Region：与资源组相同
3. 选择 **Review + create** → **Create**。

![创建 Foundry 资源](image/DEPLOY_GUIDE_GUI/07-create-foundry-resource.png)
预配完成后：
4. 打开 Foundry 资源 → **Access control (IAM)** → **+ Add role assignment**。
5. 选择 **Foundry User** 角色，然后选择 **Next**。
6. 在 **Assign access to** 中选择 **User, group, or service principal** → **+ Select members** → 选择你当前登录的账户 → **Review + assign**。
7. 等待几分钟，使角色分配生效。
8. 打开 Foundry 资源 → **Go to Foundry portal**，复制 `Project endpoint` 并保存。
9. **Build** → **Models** → **Deploy a base model** → 搜索 `text-embedding-3-small`
10. 选择 `text-embedding-3-small`，单击 **Deploy** → 选择 **Default settings**
![部署 text-embedding-3-small](image/DEPLOY_GUIDE_GUI/08-deploy-embedding-model.png)
11. **Build** → **Models** → **Deploy a base model** → 搜索 `gpt-5.4-mini`
12. 选择 `gpt-5.4-mini`，单击 **Deploy** → 选择 **Default settings**
![部署 gpt-5.4-mini](image/DEPLOY_GUIDE_GUI/09-deploy-gpt-model.png)

---

### 1.5 创建 Function App 和存储账户

1. 搜索 **Function App** → **+ Create**。
2. 选择 `Flex Consumption`。
3. **Basics**：
   - Resource group：`rg-todomanagementv2-dev`
   - Function App name：`func-todomanagement`，并启用 **Secure unique default hostname**。
   - Region：与资源组相同
   - Runtime stack：`Python` 3.11
   - Instance size：`2048 MB`
   - Zone redundancy：`Disabled`
4. **Storage**：创建新的存储账户 `satodomanagement<unique>`（小写字母 + 数字，最多 24 个字符）。
5. **Azure OpenAI**：保持默认。
6. **Networking**：启用公共访问，不设置入站限制（可稍后收紧）。
7. **Monitoring**：启用 Application Insights，如有需要则创建新组件。
8. **Durable Functions**：保持默认。
9. **Deployment**：保持默认。
10. **Authentication**：将 Authentication type 更改为 `Managed identity`。
    ![设置 Function 身份验证](image/DEPLOY_GUIDE_GUI/10-set-function-authentication.png)
11. 选择 **Review + create** → **Create**。
    ![Function App 创建完成](image/DEPLOY_GUIDE_GUI/11-create-function-app.png)
12. 预配完成后：打开 Function App → **Settings** → **Identity** → **User assigned** → **func-todomanagement-uami**，复制 **Client Id** 和 **Object (principal) ID**，然后保存。
    ![复制 Function UAMI Client ID](image/DEPLOY_GUIDE_GUI/copy-function-uami-client-id.png)

📖 参考：[https://learn.microsoft.com/azure/azure-functions/functions-create-function-app-portal](https://learn.microsoft.com/azure/azure-functions/functions-create-function-app-portal)

---

### 1.6 创建 Static Web App

1. 搜索 **Static Web Apps** → **+ Create**。
2. **Basics**：
   - Resource group：`rg-todomanagementv2-dev`
   - Name：`stapp-todomanagement-<unique>`
   - Plan type：`Standard`。
   - Deployment details：选择 **Other**
3. **Deployment configuration** → 选择 **Deployment token**。
4. 在 **Advanced** 中，将 **Region for Azure Functions API and staging environments** 设为 `East Asia`
5. 选择 **Review + create** → **Create**。
   ![创建 Static Web App](image/DEPLOY_GUIDE_GUI/12-create-swa.png)
6. 预配完成后，打开 SWA，复制以下信息并保存，供阶段 4 使用。
   - **Manage deployment token**
   - **URL**

📖 参考：[https://learn.microsoft.com/azure/static-web-apps/getting-started](https://learn.microsoft.com/azure/static-web-apps/getting-started)

---

## 阶段 2：配置身份和权限

### 2.1 在 Microsoft Entra ID 中注册 SPA

1. 搜索 **Microsoft Entra ID** → **App registrations** → **+ New registration**。
2. Name：`todomanagementv2-spa`。
3. Supported account types：**Accounts in this organizational directory only**。
4. Redirect URI：**Single-page application (SPA)** → `https://<swa>.azurestaticapps.net/`。
5. 选择 **Register**。

创建完成后：
6. 可选。如果希望在本地运行，请在 **Authentication** → **+ Add URI** 中添加重定向 URI `http://localhost:5173/`，然后保存。
7. 从 **Overview** 页面复制：
    - **Application (client) ID** → 保存为 `CLIENT_ID`
    - **Directory (tenant) ID** → 保存为 `TENANT_ID`

📖 参考：[https://learn.microsoft.com/entra/identity-platform/quickstart-register-app](https://learn.microsoft.com/entra/identity-platform/quickstart-register-app)

![SPA 应用注册](image/DEPLOY_GUIDE_GUI/register-an-application.png)

---

### 2.2 在 Microsoft Entra ID 中注册 MCP API

共享映像只包含应用程序代码。每位学习者都需要为自己的 MCP 终结点创建独立标识。

1. 打开 **Microsoft Entra ID** → **App registrations** → **+ New registration**。
2. Name：`todomanagementv2-mcp-api`。
3. Supported account types：**Accounts in this organizational directory only**。
4. 将 **Redirect URI** 留空，然后选择 **Register**。
5. 复制 **Application (client) ID** 并保存为 `MCP_CLIENT_ID`。
6. 打开 **Expose an API** → 在 **Application ID URI** 旁选择 **Add** → 接受 `api://<MCP_CLIENT_ID>`。
7. 打开 **App roles** → **Create app role**，然后输入：

   | 设置 | 值 |
   | -------------------- | -------------------------------------- |
   | Display name | `MCP Tool Executor` |
   | Allowed member types | `Both (Users/Groups + Applications)` |
   | Value | `Mcp.Tool.Executor` |
   | Description | `Execute Cosmos DB MCP tools` |
   | Enable this app role | Checked |

8. 选择 **Apply**。

在阶段 3 中获得 Container App URL 后，再添加其重定向 URI。

---

### 2.3 为应用程序标识授予访问权限

1. 将 `Cosmos DB Built-in Data Contributor` 角色分配给 Function App 的用户分配托管标识。
   a. 在 Azure 门户中打开 **Cloud Shell** 并选择 **PowerShell**。
   b. 运行以下命令：

   ```powershell
   az cosmosdb sql role assignment create `
      --account-name "<your-cosmos-db-account-name>" `
      --resource-group "<your-resource-group-name>" `
      --role-definition-id "00000000-0000-0000-0000-000000000002" `
      --principal-id "<your-azure-function-uami-id>" `
      --scope "/"

   az cosmosdb sql role assignment create `
      --account-name "<your-cosmos-gremlin-db-account-name>" `
      --resource-group "<your-resource-group-name>" `
      --role-definition-id "00000000-0000-0000-0000-000000000002" `
      --principal-id "<your-azure-function-uami-id>" `
      --scope "/"
   ```

   ![将 Cosmos DB Built-in Data Contributor 角色分配给 Function App](image/DEPLOY_GUIDE_GUI/assign-cosmos-role-to-func.png)
   📖 参考：[https://learn.microsoft.com/azure/cosmos-db/how-to-setup-rbac](https://learn.microsoft.com/azure/cosmos-db/how-to-setup-rbac)
2. 打开 Foundry **project** → **Access control (IAM)** → **+ Add role assignment**：

   - Role：`Foundry User`
   - Assign access to：**Managed identity** → 选择 **func-todomanagement-uami**。
     ![将 Foundry User 角色分配给 Function App](image/DEPLOY_GUIDE_GUI/assign-foundry-role-to-func.png)
3. 将 `MCP Tool Executor` 角色授予 Foundry 项目的托管标识。
   a. 使用同一个 Cloud Shell PowerShell 会话。
   b. 运行以下命令：

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

## 阶段 3：配置 Foundry Agent

### 3.1 为 Cosmos DB 部署 MCP 工具

工作坊开始前，讲师会构建 MCP Toolkit 映像并共享以下值：

| 值 | 示例 |
| -------------------------- | ---------------------------------- |
| Registry | `workshopacr.azurecr.io` |
| Image | `mcp-toolkit` |
| Tag | `workshop-20260727` |
| Container Apps environment | `cae-todomanagement-workshop-01` |
| Environment resource group | `rg-todomanagement-instructor` |
| Environment region | `japaneast` |
| Container App name | `mcp-toolkit-p01` |

讲师已创建共享的 Container Apps 环境，并授予你在该环境中部署 Container App 的权限。在动手实验期间，请勿创建其他环境、克隆 MCP Toolkit 存储库或构建映像。

#### 3.1.1 使用 MCP 映像创建 Container App

1. 搜索 **Container Apps** → **+ Create**。
2. 在 **Basics** 中：

   - Resource group：`rg-todomanagementv2-dev`
   - Container app name：讲师分配的唯一名称，例如 `mcp-toolkit-p01`
   - Region：讲师提供的环境区域
   - Container Apps environment：选择讲师分配的环境，例如 `cae-todomanagement-workshop-01`
3. 在 **Container** 中：

   - Use quickstart image：**Unchecked**
   - Image source：**Azure Container Registry**
   - Registry：讲师提供的注册表
   - Image：讲师提供的映像
   - Image tag：讲师提供的标记
   - CPU：`0.5`
   - Memory：`1 GiB`
4. 添加以下环境变量：

   | 名称 | 值 |
   | ------------------------------- | -------------------------------------- |
   | `AzureAd__ClientId` | 阶段 2 中的 `MCP_CLIENT_ID` |
   | `AzureAd__TenantId` | 阶段 2 中的 `TENANT_ID` |
   | `AzureAd__Audience` | 阶段 2 中的 `MCP_CLIENT_ID` |
   | `COSMOS_ENDPOINT` | 步骤 1.2 中的 NoSQL 终结点 |
   | `OPENAI_ENDPOINT` | 步骤 1.4 中的 Foundry 项目终结点 |
   | `OPENAI_EMBEDDING_DEPLOYMENT` | `text-embedding-3-small` |
   | `ASPNETCORE_ENVIRONMENT` | `Production` |
   | `ASPNETCORE_URLS` | `http://+:8080` |

5. 在 **Scale** 中：

   - Minimum replicas：`0`
   - Maximum replicas：`1`
6. 在 **Ingress** 中：

   - Ingress：**Enabled**
   - Ingress traffic：**Accepting traffic from anywhere**
   - Ingress type：**HTTP**
   - Target port：`8080`
7. 选择 **Review + create** → **Create**，然后确认修订版变为 **Running**。

如果无法选择分配的环境，请与讲师确认订阅、环境资源组和区域。讲师必须在所分配环境的作用域内向你的账户授予 **Container Apps Contributor**。请勿创建替代环境。

如果无法选择注册表或映像，请停止操作并要求讲师确认你对工作坊 ACR 的访问权限。请勿启用 ACR 管理员用户或使用注册表密码。

#### 3.1.2 授予 Container App 运行时权限

1. 打开你的 Container App → **Settings** → **Identity** → **System assigned**。
2. 将 **Status** 设置为 **On** → **Save**。
3. 打开 Cosmos DB for NoSQL 账户 → **Access control (IAM)**，将 **Cosmos DB Account Reader Role** 分配给 Container App 托管标识。
4. 在 Cloud Shell PowerShell 中授予 Cosmos 数据平面读取者角色：

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

5. 打开 Foundry 项目 → **Access control (IAM)**，将 **Foundry User** 分配给同一托管标识。
6. 等待角色分配生效后，重启 Container App 修订版。

#### 3.1.3 完成 MCP 身份验证并测试

1. 打开分配给你的 Container App 并复制其 **Application URL**。
2. 打开 **Microsoft Entra ID** → **App registrations** → `todomanagementv2-mcp-api` → **Authentication**。
3. 添加以下 **Single-page application (SPA)** 重定向 URI，然后保存：
   - `https://<mcp-app-url>/`
4. 打开 **Enterprise applications** → `todomanagementv2-mcp-api` → **Users and groups** → **+ Add user/group**。
5. 为你的用户分配 **MCP Tool Executor** 角色。
6. 打开 Container App URL，输入 `MCP_CLIENT_ID` 和 `TENANT_ID`，然后登录。
7. 选择 **Test Tool** → `List Databases` → **Invoke Selected Tool**。
   ![MCP Toolkit List Databases](image/DEPLOY_GUIDE_GUI/mcp-toolkit-list-databases.png)

📖 参考：[Azure Cosmos DB MCP Toolkit](https://github.com/AzureCosmosDB/MCPToolKit)

---

### 3.2 创建 Agent

1. 打开 Foundry 项目 → **Agents** → **Create agent** → 将 Agent 名称指定为 `todomanagement-agent` → Create。
   ![创建 Agent](image/DEPLOY_GUIDE_GUI/3-06-create-agent.png)
2. 指定以下信息。
   - **Model**：`gpt-5.4-mini`
   - **Instructions**：指定 [../prompt/todomanagement-agent.instructions.md](../prompt/todomanagement-agent.instructions.md) 中的内容
3. **Tools**：
   1. 移除 **Web search** 工具
   2. 添加 **Azure Cosmos DB** 工具
      a. **Add** → **Browse all tools**
      ![浏览所有工具](image/DEPLOY_GUIDE_GUI/agent-add-tool.png)
      b. **Catalog** → 搜索 `Azure Cosmos DB` → 选择该工具 → **Create**
      ![选择 Azure Cosmos DB 工具](image/DEPLOY_GUIDE_GUI/agent-search-cosmos-tool.png)
      c. **Connect tool with endpoint**
      ![连接工具](image/DEPLOY_GUIDE_GUI/agent-connect-tool.png)
      d. **Connect the Azure Cosmos DB tool**
      - **Name**：`AzureCosmosDB`
      - **Remote MCP Server endpoint**：`<container-application-url>/mcp`，例如 `https://mcp-toolkit-p01.livelyforest-279726ad.japaneast.azurecontainerapps.io/mcp`。
      - **Authentication**：`Microsoft Entra`
      - **Type**：`Project Managed Identity`
        - **Audience**：输入阶段 2 中的 `MCP_CLIENT_ID`。
          ![连接工具](image/DEPLOY_GUIDE_GUI/agent-connect-tool-02.png)
          e. 单击 **Connect**。
4. **Memory** → **Add** → **Create memory store**。
5. **Save** Agent。记下其 **Name**（例如 `todomanagement-agent`）和 **Version**（`3`）。
6. 测试 Agent。
   1. 在 Playground 中输入以下消息。出现提示时批准工具调用请求。
      `List all databases in my Cosmos DB account`
      ![测试 Cosmos DB 工具](image/DEPLOY_GUIDE_GUI/agent-test-cosmos-tool.png)
      📖 参考：[https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/tool-catalog](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/tool-catalog)

---

## 阶段 4：配置并部署应用程序

### 4.1 设置 Function App 应用程序设置

在 Function App → **Settings** → **Environment variables** → **+ Add** 中添加以下变量：

| 名称 | 值 |
| --------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `AZURE_CLIENT_ID` | `<func-todomanagement-uami-client-id>`，步骤 1.5 中用户分配标识的 **Client Id** |
| `COSMOS_AUTO_CREATE` | `true` |
| `COSMOS_AUTH_MODE` | `aad` |
| `COSMOS_ENDPOINT` | `https://<cosmos>.documents.azure.com:443/`，步骤 1.2 中的终结点 |
| `COSMOS_DATABASE` | `todo-db` |
| `COSMOS_GREMLIN_ENDPOINT` | `https://<cosmos>.documents.azure.com:443/`，步骤 1.3 中的终结点 |
| `COSMOS_GRAPH_DATABASE` | `todo-graph-db` |
| `COSMOS_GRAPH_NAME` | `todo-graph` |
| `FOUNDRY_AGENT_ENDPOINT` | `https://<foundry>.services.ai.azure.com/api/projects/proj-default`，步骤 1.4 中的项目终结点 |
| `FOUNDRY_EMBEDDING_DEPLOYMENT` | `text-embedding-3-small` |
| `FOUNDRY_AGENT_NAME` | `todomanagement-agent`，步骤 3.2 中的 Agent 名称 |
| `FOUNDRY_AGENT_VERSION` | 例如 `1`，步骤 3.2 中的版本 |

单击 **Apply**。

> 如果你更愿意使用 Cosmos 账户密钥，请设置 `COSMOS_AUTH_MODE=key` 并添加 `COSMOS_KEY=<primary key>`，而不是授予 RBAC 权限。

![Function App 设置](image/DEPLOY_GUIDE_GUI/function-app-settings.png)

---

### 4.2 在 Cloud Shell 中克隆应用程序源代码

1. 在 Azure 门户中打开 **Cloud Shell** 并选择 **PowerShell**。
2. 克隆讲师提供的公共存储库：

   ```powershell
   git clone https://github.com/Liminghao0922/todomanagement_v2.git

   $repoRoot = "$HOME/todomanagement_v2"
   Set-Location $repoRoot
   Get-ChildItem src
   ```

   `src` 下应包含 `api` 和 `web` 文件夹。这是参与者指南中唯一使用的 Git 命令；你不需要创建或登录 GitHub 账户。
3. 确认正确的 Azure 订阅：

   ```powershell
   az account show --output table

   # Use this only when you need to switch subscriptions.
   # az account set --subscription "<subscription-id>"
   ```

---

### 4.3 使用 Azure Functions Core Tools 部署 API

1. 检查 Cloud Shell 中可用的工具：

   ```powershell
   az version
   python --version
   func --version
   node --version
   npm --version
   ```

   确认 Python 为 `3.11`、Functions Core Tools 为 `4.x`，Node.js 为 `20.x`。如果某个命令不可用或报告了不同的主版本，请停止并询问讲师；讲师应在课程开始前验证工作坊 Cloud Shell 环境。
2. 发布 Python 应用程序。Core Tools 会读取 `requirements.txt` 并执行部署构建：

   ```powershell
   $functionAppName = "<your-function-app-name>"

   Set-Location "$repoRoot\src\api"
   func azure functionapp publish $functionAppName --python
   ```

   ![Function 已部署](image/DEPLOY_GUIDE_GUI/func-deployment-result.png)
3. 验证 API：

   ```powershell
   Invoke-RestMethod "https://{function-unique-domain}.azurewebsites.net/api/health"
   ```

预期结果：`status` 为 `healthy`。

📖 参考：[使用 Azure Functions Core Tools 发布到 Azure](https://learn.microsoft.com/azure/azure-functions/functions-run-local#publish-to-azure)

---

### 4.4 使用 Static Web Apps CLI 构建并部署 Web 应用

以下 Vite 设置是构建时值。运行构建前，请替换所有占位符。

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

1. 在 Azure 门户中打开 Static Web App → **Overview** → **Manage deployment token**。
2. 复制令牌。请勿将其粘贴到指南、聊天或共享文件中。
3. 返回 Cloud Shell PowerShell，并仅为当前 shell 会话设置该令牌：

   ```powershell
   $env:SWA_CLI_DEPLOYMENT_TOKEN = "<paste-deployment-token>"

   npx --yes @azure/static-web-apps-cli@latest deploy ./dist `
     --env production `
     --deployment-token $env:SWA_CLI_DEPLOYMENT_TOKEN

   Remove-Item Env:SWA_CLI_DEPLOYMENT_TOKEN
   ```

📖 参考：[使用 Static Web Apps CLI 部署](https://learn.microsoft.com/azure/static-web-apps/static-web-apps-cli-deploy)

---

### 4.5 链接 Function App 后端

此步骤使浏览器对 `/api/*` 的请求到达独立的 Function App。

1. 在 Azure 门户中打开 Static Web App。
2. 选择 **Settings** → **APIs**。
3. 在 **Production** 行中选择 **Link**。
4. 设置：
   - Backend resource type：**Function App**
   - Subscription：你的订阅
   - Resource name：你的 Function App
   - Backend slot：**Production**
5. 选择 **Link**。
![链接到 Function](image/DEPLOY_GUIDE_GUI/swa-link-to-function.png)
Static Web App 必须使用 **Standard** 计划才能进行此集成。

📖 参考：[将你自己的 Functions 引入 Azure Static Web Apps](https://learn.microsoft.com/azure/static-web-apps/functions-bring-your-own)

---

### 4.6 部署检查点

- Function 健康检查 URL 返回 `healthy`。
- Static Web App 的 **APIs** 显示已链接的 Function App。
- Static Web App URL 能够加载登录页面。
- 未创建 GitHub 存储库、服务主体、机密或工作流。

---

## 阶段 5：端到端验证

1. 打开 `https://<swa>.azurestaticapps.net`，并通过 MSAL 登录。
2. 在 **Todos** 页面 → 单击 **Generate to Test Todos**（演示数据种子操作）→ 验证 Todo。
   ![端到端检查 Todo](image/DEPLOY_GUIDE_GUI/e2e-check-verify-todos.png)
3. 打开 **Projects** → 打开一个已生成的项目 → **View Graph** → 确认 Cytoscape 能够渲染来自 Gremlin 图的边。
   ![端到端检查项目](image/DEPLOY_GUIDE_GUI/e2e-check-verify-projects-01.png)
   ![端到端检查项目图](image/DEPLOY_GUIDE_GUI/e2e-check-verify-projects-02.png)
4. 打开 **Chat** → 发送消息，例如 `What should I prioritize today?` → Foundry Agent 应会响应，并可能调用 `Azure Cosmos DB` 工具。
   ![端到端检查聊天](image/DEPLOY_GUIDE_GUI/e2e-check-verify-chat.png)
   ![端到端检查聊天工具调用](image/DEPLOY_GUIDE_GUI/e2e-check-verify-chat-tool-call.png)

---

## 阶段 6：清理

```powershell
az group delete --name rg-todomanagementv2-dev --yes --no-wait
```

如果不再需要，请在 **Microsoft Entra ID → App registrations** 下手动删除 Entra ID 应用注册 (`todomanagement-spa`)。

---

## 相关文档

- [`handson/DEPLOY_GUIDE.md`](DEPLOY_GUIDE.md)
- [`docs/ARCHITECTURE_GUIDE.md`](../docs/ARCHITECTURE_GUIDE.md)
