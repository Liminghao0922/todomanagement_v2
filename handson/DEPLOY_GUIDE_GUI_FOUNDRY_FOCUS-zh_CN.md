# Todo Management v2 实验指南（Foundry Focus，初学者路线）

[English](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS.md) | [简体中文](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS-zh_CN.md) | [日本語](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS-ja_JP.md)

本实验聚焦参与者自有的 Foundry 资源、项目、embedding 和 GPT 模型部署、MCP 身份、Cosmos DB MCP Container App，以及全新的 Microsoft Foundry Prompt agent。讲师会在课前准备共享应用基础设施、Container Apps 环境和容器镜像。

预计耗时：60–90 分钟。

---

## 1. 需要从讲师处获取的值和访问权限

开始前请先记录以下值：

| 项目                                | 你的值                                                |
| ----------------------------------- | ----------------------------------------------------- |
| 参与者 ID                           | `<p01>`                                               |
| 租户 ID                             | `<tenant-id>`                                         |
| Todo 应用 URL                       | `<todo-app-url>`                                      |
| 参与者资源组                        | `<participant-resource-group>`                        |
| Cosmos DB 账户名称                  | `<cosmos-account-name>`                               |
| Cosmos DB 资源组                    | `<cosmos-resource-group>`                             |
| Cosmos DB 终结点                    | `https://<cosmos-account>.documents.azure.com:443/`   |
| Foundry 区域                        | `<foundry-region>`                                    |
| ACR 登录服务器                      | `<registry>.azurecr.io`                               |
| MCP 镜像存储库                      | `mcp-toolkit`                                         |
| MCP 镜像标记                        | `<tag>`                                               |
| 分配的 Container Apps 环境          | `cae-todomanagement-workshop-01`                      |
| 环境资源组                          | `<instructor-resource-group>`                         |
| 环境区域                            | `japaneast`                                           |
| 分配的 Container App 名称           | `mcp-toolkit-p01`                                     |

在所有参与者自有名称中都使用你的参与者 ID：

- MCP app registration: `todomanagementv2-mcp-api-p01`
- Foundry resource: `aifoundry-todomanagement-p01`
- Foundry project: `proj-todomanagement-p01`
- Embedding deployment: `text-embedding-3-small-p01`
- Foundry connection: `AzureCosmosDB-p01`
- Foundry agent: `todomanagement-agent-p01`

不要使用其他参与者的 ID，也不要创建新的 Container Apps environment。

所需访问权限：

- 在你的 participant resource group 上拥有 Contributor 或 Owner。
- 在分配给你的 Container Apps environment 上拥有 Container Apps Contributor。
- 在讲师提供的 Cosmos DB account 上拥有 DocumentDB Account Contributor。
- 通过分配环境的系统身份使用讲师 ACR 镜像的权限。
- 创建 app registration 的权限。如果你无法分配 Enterprise Application 角色，请让讲师执行这些角色分配。

Cloud Shell PowerShell 仅用于一次 Cosmos DB 数据平面角色分配。

---

## 开始前：生成你的 Todo 数据

在创建 Foundry resource 之前，先初始化与你的参与者账号关联的 Todo 数据：

1. 在无痕浏览器窗口中打开讲师提供的 `TODO_APP_URL`。
2. 使用分配给你的参与者账号登录。
3. 打开 **Todos** 页面。
4. 选择 **Generate 50 Test Todos** 一次。
5. 等待操作完成，并确认页面中出现生成的 todo 项。

检查点：

- 你可以使用参与者账号登录 Todo 应用。
- 在 **Todos** 页面可看到生成的 todo 项。

---

## 2. 创建你的 Foundry Resource 和 Project

### 2.1 创建你的 Foundry Resource

1. 打开 [Azure portal](https://portal.azure.com)。
2. 在搜索栏中搜索 **Foundry**，然后在 **Use with Foundry** 下打开 **Foundry**。
3. 选择 **+ Create**。
4. 在 **Basics** 中配置资源：

   - Subscription：讲师提供的 workshop subscription。
   - Resource group：你的 participant resource group。
   - Resource name：`aifoundry-todomanagement-p01`，将 `p01` 替换为你的参与者 ID。该名称必须全局唯一。
   - Region：讲师提供的 Foundry region，例如：**Japan East**。
5. 其余选项卡保持讲师提供的默认值，除非有额外指示。
6. 选择 **Review + create** -> **Create**。
7. 等待部署成功，然后选择 **Go to resource**。
8. 在 Azure portal 的 `FOUNDRY_RESOURCE_NAME` **Overview** 页面中，选择 **Go to Foundry portal**。
9. 打开 **Home** 并记录：

   - Project endpoint 记为 `FOUNDRY_PROJECT_ENDPOINT`。
   - 去掉 `/openai/v1` 的 Azure OpenAI endpoint 记为 `AZURE_OPENAI_ENDPOINT`，例如：`https://aifuondry-todomanagement-p01.openai.azure.com`。

### 2.2 分配 Foundry User 权限

1. 返回 [Azure portal](https://portal.azure.com)。
2. 打开你在 2.1 节中创建的 `FOUNDRY_RESOURCE_NAME` 资源。
3. 打开 **Access control (IAM)** -> **+ Add** -> **Add role assignment**。
4. 在 **Role** 中搜索并选择 **Foundry User**，然后选择 **Next**。
5. 在 **Members**：
   - Assign access to: **User, group, or service principal**。
   - 选择 **+ Select members**。
   - 搜索并选择你的参与者账号。
6. 选择 **Review + assign**，然后再次选择 **Review + assign**。
7. 打开 **Access control (IAM)** -> **Role assignments**，确认你的参与者账号在 **This resource** 作用域下拥有 **Foundry User**。

如果 **Add role assignment** 不可用，请让讲师在 `FOUNDRY_RESOURCE_NAME` 上为你的参与者账号分配 **Foundry User**。仅有 Contributor 无法创建角色分配；此操作需要 Owner、User Access Administrator 或等效权限。

检查点：

- 你的参与者账号在 **Role assignments** 中显示角色 **Foundry User**。
- 作用域是参与者专属的 Foundry resource，而不是 subscription 或讲师资源。

---

## 3. 部署你的模型

### 3.1 部署 `text-embedding-3-small`

1. 在你的 Foundry project 中，打开 **Build** -> **Deployments**。
2. 选择 **Deploy a base model**。
3. 搜索并选择 `text-embedding-3-small`。
4. 选择 **Deploy** -> **Default settings**。
5. 记录部署名称为 `EMBEDDING_DEPLOYMENT_NAME`。

### 3.2 部署 `gpt-5.4-mini`

1. 在 **Build** -> **Deployments** 中，选择 **Deploy a base model**。
2. 搜索并选择 `gpt-5.4-mini`。
3. 选择 **Deploy** -> **Default settings**。
4. 等待部署状态变为 **Succeeded**。
5. 记录部署名称为 `GPT_DEPLOYMENT_NAME`。

---

## 4. 创建 MCP API 身份和 Container App

### 4.1 创建 App Registration

1. 打开 Azure portal。
2. 打开 **Microsoft Entra ID** -> **App registrations**。
3. 选择 **+ New registration**。
4. 输入：
   - Name: `todomanagementv2-mcp-api-p01`，将 `p01` 替换为你的参与者 ID。
   - Supported account types: **Accounts in this organizational directory only**。
   - Redirect URI: 现在先留空。
5. 选择 **Register**。
6. 在 **Overview** 中记录：
   - **Application (client) ID** 记为 `MCP_CLIENT_ID`。
   - **Directory (tenant) ID** 记为 `TENANT_ID`。

### 4.2 暴露 MCP API

1. 打开 **Expose an API**。
2. 在 **Application ID URI** 旁边选择 **Add**。
3. 接受 `api://<MCP_CLIENT_ID>` 并保存。
4. 选择 **+ Add a scope**。
5. 输入：
   - Scope name: `access_as_user`
   - Who can consent: **Admins and users**
   - Admin consent display name: `Access Cosmos DB MCP Toolkit API`
   - Admin consent description: `Allow access to the Cosmos DB MCP Toolkit API on behalf of the signed-in user.`
   - User consent display name: `Access Cosmos DB MCP Toolkit API`
   - User consent description: `Allow access to the Cosmos DB MCP Toolkit API on your behalf.`
   - State: **Enabled**
6. 选择 **Add scope**。

### 4.3 创建 MCP Tool Executor App Role

1. 打开 **App roles**。
2. 选择 **+ Create app role**。
3. 输入以下值：

   | Setting | Value |
   | --- | --- |
   | Display name | `MCP Tool Executor` |
   | Allowed member types | **Both (Users/Groups + Applications)** |
   | Value | `Mcp.Tool.Executor` |
   | Description | `Execute Cosmos DB MCP tools` |
   | Enable this app role | Checked |

4. 选择 **Apply**。

### 4.4 添加 Delegated API Permissions

1. 打开 **API permissions**。
2. 选择 **+ Add a permission** -> **My APIs**。
3. 选择你的 `todomanagementv2-mcp-api-p01` 应用。
4. 选择 **Delegated permissions** -> `access_as_user` -> **Add permissions**。
5. 如果你的租户需要管理员同意，请让讲师选择 **Grant admin consent**。

检查点：

- Application ID URI 是 `api://<MCP_CLIENT_ID>`。
- Delegated scope `access_as_user` 已存在。
- App role `Mcp.Tool.Executor` 允许用户和应用程序两种成员类型。

---

私有 ACR 镜像拉取使用的是在分配的 Container Apps environment 上已启用的 system-assigned identity。你的 Container App 自身的 system-assigned identity 会单独启用，用于 Cosmos DB 和 Foundry 运行时访问。

### 4.5 使用 MCP 镜像创建 Container App

1. 在 Azure portal 中搜索 **Container Apps**。
2. 选择 **+ Create** -> **Container App**。
3. 在 **Basics** 中输入：

   - Resource group：你的 participant resource group。
   - Container app name：分配给你的唯一名称，例如 `mcp-toolkit-p01`。
   - Region：讲师提供的 environment region。
   - Container Apps environment：选择讲师分配给你的环境。
4. 在 **Container**：

   - 清除 **Use quickstart image**。
   - Image source: **Azure Container Registry**
   - Registry: 讲师提供的 ACR
   - Image: 讲师提供的 `mcp-toolkit` repository
   - Image tag: 讲师提供的 tag
   - Authentication type: **Managed identity**
   - Managed identity: 为分配的 Container Apps environment 选择 **System assigned**
   - CPU: `0.5`
   - Memory: `1 GiB`
5. 添加以下环境变量：

   | 名称                            | 值                                    |
   | ------------------------------- | ------------------------------------- |
   | `AzureAd__ClientId` | `MCP_CLIENT_ID` |
   | `AzureAd__TenantId` | `TENANT_ID` |
   | `AzureAd__Audience` | `MCP_CLIENT_ID` |
   | `COSMOS_ENDPOINT` | 讲师提供的 Cosmos DB 终结点 |
   | `OPENAI_ENDPOINT` | `AZURE_OPENAI_ENDPOINT` |
   | `OPENAI_EMBEDDING_DEPLOYMENT` | `EMBEDDING_DEPLOYMENT_NAME` |
   | `ASPNETCORE_ENVIRONMENT` | `Production` |
   | `ASPNETCORE_URLS` | `http://+:8080` |

   ![1786453747959](image/DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS/1786453747959.png)
6. 在 **Ingress**：

   - Ingress: **Enabled**
   - Ingress traffic: **Accepting traffic from anywhere**
   - Ingress type: **HTTP**
   - Target port: `8080`

   ![1786453787990](image/DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS/1786453787990.png)
7. 选择 **Review + create** -> **Create**。
8. 等待 revision 状态显示 **Running**。
9. 复制 Container App 的 **Application URL** 记为 `MCP_APP_URL`。

如果分配的 environment 无法被选择，停止并请讲师验证你是否被分配了 Container Apps Contributor。不要创建替代环境。

如果私有镜像无法拉取，验证 environment system identity 是否具有 `AcrPull`，并且 registry authentication 选择了 **System assigned**。

### 4.6 启用 Container App Managed Identity

1. 打开你的 Container App。
2. 打开 **Settings** -> **Identity** -> **System assigned**。
3. 将 **Status** 设为 **On** 并选择 **Save**。
4. 记录 **Object (principal) ID** 为 `MCP_PRINCIPAL_ID`。

### 4.7 向该 Identity 授予 Cosmos DB 访问权限

首先，授予控制平面读取角色：

1. 打开讲师提供的 Cosmos DB for NoSQL account。
2. 打开 **Access control (IAM)** -> **+ Add role assignment**。
3. 选择 **Cosmos DB Account Reader Role**。
4. 将其分配给你的 Container App 的 system-assigned managed identity。

然后打开 Azure Cloud Shell 并选择 **PowerShell**。运行：

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

以 `0001` 结尾的 role ID 是 **Cosmos DB Built-in Data Reader**。

### 4.9 向该 Identity 授予 Foundry 访问权限

1. 在 Azure portal 中打开你的参与者专属 Foundry resource。
2. 打开 **Access control (IAM)** -> **+ Add role assignment**。
3. 选择 **Foundry User**。
4. 将其分配给你的 Container App 的 system-assigned managed identity。
5. 打开 **Access control (IAM)** -> **Role assignments**，并确认该角色已在 **This resource** 作用域分配给 `MCP_PRINCIPAL_ID`。
6. 测试前至少等待五分钟以完成 Azure RBAC 传播。

`Foundry User` 包含了生成 embeddings 所需的 Foundry 和 Azure OpenAI 数据平面权限。本实验不要添加其他推理角色。

### 4.10 配置 Redirect URIs

1. 打开 **Microsoft Entra ID** -> **App registrations** -> 你的 MCP app registration。
2. 打开 **Authentication**。
3. 选择 **+ Add a platform** -> **Single-page application**。
4. 添加以下两个 redirect URI：
   - `https://<your-container-app-hostname>/`
5. 保存配置。

### 4.11 分配 MCP Tool Executor

将该角色分配给你的用户：

1. 打开 **Microsoft Entra ID** -> **Enterprise applications**。
2. 找到你的 `todomanagementv2-mcp-api-p01` 应用。
3. 打开 **Users and groups** -> **+ Add user/group**。
4. 选择你的用户和角色 **MCP Tool Executor**。
5. 完成分配。

将同一角色分配给 Foundry project 的 managed identity：

1. 在同一个 Enterprise Application 中，选择 **+ Add user/group**。
2. 选择名为 `<foundry-account-name>/projects/<project-name>` 的 managed identity。
3. 选择角色 **MCP Tool Executor** 并完成分配。

如果 portal 无法选择 project managed identity，请让讲师执行该分配。这个 Entra 权限与 Azure subscription RBAC 是分开的。

### 4.11 直接测试 MCP Toolkit

1. 在无痕浏览器窗口中打开 `MCP_APP_URL`。
2. 如有提示，输入你的 `MCP_CLIENT_ID` 和 `TENANT_ID`。
3. 登录。
4. 打开 **Test Tool**。
5. 选择 **List Databases** 并调用。
6. 选择 **Vector Search** 并输入：
   - Database: `todo-db`
   - Container: `todos`
   - Search text: `adoption-plan`
   - Vector Property: `embeddings`
   - Select Properties: `title,description`
7. 调用该工具。
![1786454636662](image/DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS/1786454636662.png)

预期结果：

- **List Databases** 返回 `todo-db`。
- **Vector Search** 返回匹配的 todo 项，且不出现 `401 Unauthorized`。

如果 **List Databases** 成功但 **Vector Search** 返回 `401 Unauthorized`，先验证 `OPENAI_ENDPOINT` 使用的是 Azure OpenAI endpoint `https://<your-foundry-resource>.openai.azure.com/`，而不是包含 `/api/projects/` 的 Project endpoint。然后验证 Container App system identity 具有 **Foundry User**，等待 RBAC 传播，重启 Container App，并再次测试。

在两个直接 MCP 测试都成功之前，不要继续。

---

## 5. 创建新的 Foundry Prompt Agent

### 5.1 创建参与者唯一 Agent

1. 返回 Microsoft Foundry portal 中你的参与者专属 project。
2. 打开 **Build** -> **Agents**。
3. 选择 **New agent** -> **Build an agent**。
4. 输入 agent name `todomanagement-agent-p01`，将 `p01` 替换为你的参与者 ID。
5. 选择你在 3.2 节记录为 `GPT_DEPLOYMENT_NAME` 的 model deployment。

### 5.2 输入 Agent Instructions

将以下内容直接粘贴到 **Instructions**：

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

### 5.3 添加你的 Azure Cosmos DB MCP Tool

1. 在 agent editor 中，如果自动添加了 **Web search**，请移除。
2. 选择 **Add** -> **Browse all tools**。
3. 搜索并选择 **Azure Cosmos DB**。
4. 使用以下值创建新连接：

   | Setting | Value |
   | --- | --- |
   | Connection name | 使用你的参与者 ID，例如 `AzureCosmosDB-p01` |
   | Remote MCP Server endpoint | `https://<your-container-app-hostname>/mcp` |
   | Authentication | **Microsoft Entra** |
   | Authentication type | **Project Managed Identity** |
   | Audience | `MCP_CLIENT_ID` |

![1786454765316](image/DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS/1786454765316.png)
5. 选择 **Connect**。
6. 确认该工具出现在 agent 的工具列表中。
7. 保存 agent，并确认新版本状态是 **Running** 或 **Active**。

使用唯一连接名，便于将该连接映射到你的参与者自有 project 和 Container App。

### 5.4 测试 Agent

按顺序运行以下提示词：

1. `List all databases in my Cosmos DB account.`
2. `List containers in database todo-db.`
3. `What should I prioritize today?`

预期行为：

- Agent 调用你参与者专属的 Azure Cosmos DB MCP tool。
- 第一条响应中出现 `todo-db`。
- 工具结果来自 Cosmos DB，而不是仅来自模型知识。
- 优先级响应引用工具返回的具体 todo 项。
- 运行第 3 条提示词时，可能会要求你提供 `owner_id`。在 Azure portal 中打开 **Microsoft Entra ID**，搜索你的 user principal name (UPN)，选择你的账号，并从 **Overview** 页面复制 **Object ID**。
![1786455087699](image/DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS/1786455087699.png)

如果 Foundry 请求工具批准，请检查工具名称和参数，然后批准该调用。

---

## 6. 查看 Traces 并调优 Instructions

### 6.1 查看一条 Trace

1. 打开该 agent 对话的 **Traces**。
![1786455569486](image/DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS/1786455569486.png)
2. 验证最终回答是基于工具结果。

### 6.2 调优 Instructions

将以下约束添加到 Agent instructions：

```text
For prioritization requests, return exactly five items in a Markdown table with columns Rank, Todo, Reason, and Next action.
```

点击 **Save** 以创建新的 Agent version，重新运行相同提示词，并比较：

- 是否调用了同一个工具
- 工具参数是否变化
- 输出格式是否改进
- 回答是否仍然基于 Cosmos DB 数据

---

## 7. 完成标准

当以下条件满足时，实验完成：

- 你的 MCP API app registration 具有 `access_as_user` 和 `Mcp.Tool.Executor`。
- 你的参与者专属 Foundry resource 和 project 存在于你的 participant resource group 中。
- 你的参与者专属 `text-embedding-3-small` 部署已成功。
- 你的 `gpt-5.4-mini` 部署已成功。
- 你的 Container App 使用 managed identity authentication 运行讲师提供的 MCP 镜像。
- 直接 **List Databases** 测试返回 `todo-db`。
- 你的新 Prompt agent 具有参与者唯一名称和连接。
- Agent 成功调用 Cosmos DB MCP。
- 你可以解释一条从 prompt 到工具调用再到最终响应的 trace。
- 你已保存并比较至少一次 instruction 变更。

---

## 8. 故障排查

| 症状                                      | 检查项                                                                                                                   |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| 无法创建 Foundry resource | 验证你在参与者资源组上拥有 Contributor 或 Owner 权限，并确认已注册 `Microsoft.CognitiveServices` 资源提供程序。 |
| 无法创建 Foundry project | 验证参与者专属 Foundry resource 已成功部署并处于选中状态。 |
| Embedding 部署失败 | 验证 `text-embedding-3-small` 的可用性、部署类型、参与者唯一部署名称和配额。 |
| 无法选择分配的 Container Apps environment | 验证订阅，并确认你在该环境上具有 Container Apps Contributor 角色。 |
| 无法选择 ACR 镜像或 revision 显示镜像拉取失败 | 验证环境的 system identity 具有 `AcrPull`，并为 managed identity registry authentication 选择 **System assigned**。 |
| Container revision 无法启动 | 验证目标端口 `8080`、`ASPNETCORE_URLS`、镜像标记和所有必需的环境变量。 |
| MCP UI 登录失败 | 验证两个 redirect URI、tenant ID、client ID，以及用户的 `MCP Tool Executor` 分配。 |
| 直接执行 List Databases 返回 403 | 验证已向 Container App identity 分配 Cosmos DB Account Reader 和 Cosmos DB Built-in Data Reader。 |
| Vector Search 返回 401 | 将 `OPENAI_ENDPOINT` 设置为 `https://<your-foundry-resource>.openai.azure.com/`；验证 Container App identity 具有 **Foundry User**，然后重启应用。 |
| Foundry tool 返回 401 或 403 | 验证 Foundry project managed identity 在你的 Enterprise Application 上具有 `MCP Tool Executor`。 |
| Foundry connection name 已存在 | 使用参与者专属名称，例如 `AzureCosmosDB-p01`。 |
| Agent 显示 Classic migration 消息 | 确认创建的是 **New agent -> Prompt agent**，而不是 Classic agent 或 Assistant。 |
| Agent 未调用工具便直接回答 | 强化 tool-first instruction，并明确要求提供 Cosmos DB 证据。 |

在更改共享 ACR 或 Container Apps environment 设置前，请先咨询讲师。只更改你参与者专属的 Foundry resource 和 project。
