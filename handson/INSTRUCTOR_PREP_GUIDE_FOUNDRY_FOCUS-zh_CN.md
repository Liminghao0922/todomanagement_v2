# 讲师准备指南（Foundry Focus，初学者轨道）

[English](INSTRUCTOR_PREP_GUIDE_FOUNDRY_FOCUS.md) | [简体中文](INSTRUCTOR_PREP_GUIDE_FOUNDRY_FOCUS-zh_CN.md) | [日本語](INSTRUCTOR_PREP_GUIDE_FOUNDRY_FOCUS-ja_JP.md)

[参与者指南](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS-zh_CN.md)

本指南定义了面向初学者的 Todo Management v2 研讨会中由讲师负责的准备工作。讲师需在课前完成部署、登录访问配置，以及共享 Container Apps 环境准备。参与者则在实验中自行创建 Foundry 资源、项目和 embedding 部署，然后构建 Cosmos DB MCP 工具与 Prompt agent。

讲师准备主要分为四个部分：

1. 使用 `azd` 部署完整 Todo 应用。
2. 配置参与者对 Todo 应用的登录权限。
3. 为参与者自建 Foundry 资源准备订阅访问、提供程序注册与模型配额。
4. 为参与者的 Cosmos DB MCP 部署准备共享 Container Apps 环境。

预计讲师准备时间：首次执行约 90-150 分钟，熟悉流程后约 45-60 分钟。

---

## 0. 本版本的前提假设

本 Foundry Focus 轨道假设：

- 参与者不执行基础设施部署命令。
- 参与者在实验中仍可能创建自己的 Cosmos DB MCP Container App，但共享 Container Apps 环境与镜像访问由讲师提前准备。
- Todo 应用本身由讲师通过 `azd up` 部署。
- 每位参与者都会创建唯一命名的 Foundry 资源、项目、embedding 部署、MCP 连接与 Prompt agent。

此仓库已包含本轨道所需的最小 `azd` 支持：

- [../azure.yaml](../azure.yaml)
- [../infra/main.parameters.json](../infra/main.parameters.json)
- [../infra/azd-postprovision.ps1](../infra/azd-postprovision.ps1)

`azd` 流程会先预配 Bicep 基础设施，然后运行 post-provision hook：发布 Functions API、构建/部署 Static Web App、将 SWA 连接到 Functions，并校验健康检查端点。

---

## 1. 讲师前置条件

请在讲师工作站或 Azure Cloud Shell PowerShell 中运行以下检查。

```powershell
azd version
az version
func --version
python --version
node --version
npm --version
```

所需版本：

| 工具                       | 预期                     |
| -------------------------- | ------------------------ |
| Azure Developer CLI        | 已安装 `azd`           |
| Azure CLI                  | 已登录到目标租户         |
| Azure Functions Core Tools | v4                       |
| Python                     | 3.11+                    |
| Node.js                    | 20+                      |
| npm                        | 可用                     |

讲师所需权限：

- 在 Azure 订阅/资源组上具有 Contributor 或 Owner 权限。
- 具有创建 Microsoft Entra 应用注册的权限。
- 具有授予应用同意或分配 Enterprise Application 用户/组的权限。
- 具有创建 Azure Container Registry 和 Container Apps 环境的权限。
- 具有创建和配置 Foundry 资源、项目、模型和 agent 的权限。

建议的参与者账号准备：

- 为研讨会参与者创建或确定一个 Microsoft Entra 安全组。
- 在开课前将所有参与者加入该组。
- 将该组用于 Todo 应用登录分配和共享 Container Apps 环境访问。

---

## 2. 使用 azd 部署完整 Todo 应用

### 2.1 登录并创建 azd 环境

在 Azure Cloud Shell PowerShell 中，先克隆仓库，再切换到克隆目录：

```powershell
git clone https://github.com/Liminghao0922/todomanagement_v2.git
Set-Location todomanagement_v2

$subscriptionId = "<subscription-id>"
$location = "japaneast"
$staticWebAppLocation = "eastasia"
$azdEnvName = "foundry-focus-20260806"
$resourceGroup = "rg-todomanagementv2-instructor"

azd auth login
azd env new $azdEnvName
azd env set AZURE_SUBSCRIPTION_ID $subscriptionId
azd env set AZURE_LOCATION $location
azd env set STATIC_WEB_APP_LOCATION $staticWebAppLocation
azd env set AZURE_RESOURCE_GROUP $resourceGroup
```

主工作负载资源请使用 `japaneast`，Static Web Apps 请使用 `eastasia`。`Microsoft.Web/staticSites` 在 Japan East 不可用。

成功标准：

- `azd env get-values` 显示了订阅、区域和资源组值。
- 当前 Azure 账号位于预期租户。

验证：

```powershell
azd env get-values
az account show --output table
```

### 2.2 预览预配

创建资源前，请先执行预览。

```powershell
azd provision --preview
```

请确认预览包含预期的 `Create` 资源。当前测试环境（`environment=todomangementv2`）会显示类似如下条目：

```text
Create : Container App                      : mcp-todomanageme-oit3m2
Create : Container Apps Environment         : cae-todomanageme-oit3m2
Create : Azure AI Services                  : aifoundry-todomanagement-oit3m2mzmum7y
Create : Azure AI Services Model Deployment : gpt-5.4-mini
Create : Azure AI Services Model Deployment : text-embedding-3-small
Create : Foundry project                    : proj-todomanagement
Create : Container Registry                 : acrtodomanageoit3m2
Create : Azure Cosmos DB                    : cosgrtodomanagementoit3m2mzmum7y
Create : Azure Cosmos DB                    : cossqltodomanagementoit3m2mzmum7y
Create : Log Analytics workspace            : log-todomanageme-mcp-oit3m2
Create : Storage account                    : sttodomanaoit3m2mzmum7y
Create : App Service plan                   : asp-todomanagement-todomangementv2
Create : Web App                            : func-todomanagement-todomangementv2-oit3m2mzmum7y
Create : Static Web App                     : swa-todomanagement-oit3m2mzmum7y
```

如果你使用了不同的 `projectName`、`environment` 或资源组，后缀部分会不同。资源形态应包含 Todo 应用资源、两个 Cosmos 账户以及 Cosmos DB MCP Toolkit 资源。

本指南中的命名规则与当前 Bicep 模板保持一致：

- `<suffix>` = `uniqueString(resourceGroup().id)`。
- Azure AI Services: `aifoundry-<projectName>-<suffix>`
- Cosmos SQL account: `cossql<projectName><suffix>`
- Cosmos Gremlin account: `cosgr<projectName><suffix>`
- Storage account: `st<projectNameNoDashFirst8><suffix>` (project name lowercased, `-`/`_` removed, then first 8 chars)
- App Service plan: `asp-<projectName>-<env>`
- Function app name: `func-<projectName>-<env>-<suffix>` (preview resource type is shown as `Web App`)
- Static Web App: `swa-<projectName>-<suffix>`
- Container Registry: `acr<projectNameFirst10><shortSuffix>`
- Container App: `mcp-<projectNameFirst12>-<shortSuffix>`
- Container Apps environment: `cae-<projectNameFirst12>-<shortSuffix>`
- Log Analytics workspace: `log-<projectNameFirst12>-mcp-<shortSuffix>`

如果某些资源已存在或被报告为子资源/无变更资源，精确列表可能会有所差异。`azd up` 后请从部署输出中确认 Function App、应用注册、端点和各类 ID。

如果预览显示了非预期的订阅、区域或资源组，请先停止并修正 azd 环境值，再继续。

### 2.3 运行完整部署

运行：

```powershell
azd up
```

本仓库中 `azd up` 的执行内容：

1. 从 [../infra/main.bicep](../infra/main.bicep) 预配基础设施。
2. 运行 [../infra/azd-postprovision.ps1](../infra/azd-postprovision.ps1) 配置 Entra、RBAC、Cosmos 权限和 Foundry RemoteTool 连接。
3. 运行 `azd deploy`，其 postdeploy 入口为 [../infra/azd-deploy.ps1](../infra/azd-deploy.ps1)。
4. 构建并激活 Cosmos MCP Toolkit 镜像，然后创建或更新 Foundry Agent。
5. 发布 Python Functions API，并构建/部署 Vue Static Web App。
6. 尝试将 Static Web App 生产 API 连接到 Function App。
7. 校验 Function App 和 Static Web App 路由上的 `/api/health`。

如需分阶段执行，可使用 `azd provision` 执行基础设施阶段，使用 `azd deploy` 执行应用组件阶段。

来自 provision 和 deploy hooks 的预期输出包括：

- Todo app URL
- Function URL
- Foundry resource name
- Foundry project name
- Foundry project endpoint
- Entra App Registration client ID
- Tenant ID

成功标准：

- `azd up` 完成且无预配失败。
- Function 健康检查端点返回 `healthy`。
- 浏览器可打开 Todo app URL。
- Static Web App `/api/health` 返回 `healthy`，或脚本给出警告并提示你手动完成 SWA API 链接。

### 2.4 SWA API 链接失败时的手动修复

如果 hook 打印了 API 链接警告，请在 Azure 门户执行以下操作：

1. 打开 Static Web App。
2. 进入 **Settings** -> **APIs**。
3. 在 **Production** 行选择 **Link**。
4. 设置：
   - Backend resource type: **Function App**
   - Subscription: workshop subscription
   - Resource name: deployed Function App
   - Backend slot: **Production**
5. 选择 **Link**。

验证：

```powershell
$todoAppUrl = "<static-web-app-url-from-azd-output>"
Invoke-RestMethod "$todoAppUrl/api/health"
```

预期结果：

```json
{
  "status": "healthy",
  "service": "Todo Management Functions API"
}
```

---

## 3. 记录部署值

`azd up` 之后，请收集后续配置和发放参与者材料所需的值。

```powershell
$resourceGroup = (azd env get-value AZURE_RESOURCE_GROUP)

$deploymentName = az deployment group list `
  --resource-group $resourceGroup `
  --query "max_by([].{name:name,timestamp:properties.timestamp}, &timestamp).name" `
  --output tsv

$outputs = az deployment group show `
  --resource-group $resourceGroup `
  --name $deploymentName `
  --query properties.outputs `
  --output json | ConvertFrom-Json

$functionAppName = $outputs.functionAppName.value
$functionAppUrl = $outputs.functionAppUrl.value
$staticWebAppName = $outputs.staticWebAppName.value
$staticWebAppUrl = $outputs.staticWebAppUrl.value
$cosmosAccountName = $outputs.cosmosAccountName.value
$cosmosEndpoint = $outputs.cosmosEndpoint.value
$cosmosAccountId = az cosmosdb show `
  --resource-group $resourceGroup `
  --name $cosmosAccountName `
  --query id `
  --output tsv
$clientId = $outputs.appRegistrationClientId.value
$tenantId = $outputs.tenantId.value
$foundryResourceName = $outputs.foundryResourceName.value
$foundryProjectName = $outputs.foundryProjectName.value
$foundryProjectResourceId = $outputs.foundryProjectResourceId.value
$foundryProjectEndpoint = $outputs.foundryProjectEndpoint.value
$cosmosMcpAcrName = $outputs.cosmosMcpAcrName.value
$cosmosMcpAcrLoginServer = $outputs.cosmosMcpAcrLoginServer.value
$cosmosMcpImageRepository = $outputs.cosmosMcpImageRepository.value
$cosmosMcpImageTag = $outputs.cosmosMcpImageTag.value
$cosmosMcpImage = $outputs.cosmosMcpImage.value

[ordered]@{
  resourceGroup = $resourceGroup
  functionAppName = $functionAppName
  functionAppUrl = $functionAppUrl
  staticWebAppName = $staticWebAppName
  staticWebAppUrl = $staticWebAppUrl
  cosmosAccountName = $cosmosAccountName
  cosmosResourceGroup = $resourceGroup
  cosmosResourceId = $cosmosAccountId
  cosmosEndpoint = $cosmosEndpoint
  clientId = $clientId
  tenantId = $tenantId
  foundryResourceName = $foundryResourceName
  foundryProjectName = $foundryProjectName
  foundryProjectResourceId = $foundryProjectResourceId
  foundryProjectEndpoint = $foundryProjectEndpoint
  cosmosMcpAcrName = $cosmosMcpAcrName
  cosmosMcpAcrLoginServer = $cosmosMcpAcrLoginServer
  cosmosMcpImageRepository = $cosmosMcpImageRepository
  cosmosMcpImageTag = $cosmosMcpImageTag
  cosmosMcpImage = $cosmosMcpImage
} | ConvertTo-Json | Out-File .\handson\foundry-focus-class-values.json -Encoding utf8
```

成功标准：

- [foundry-focus-class-values.json](foundry-focus-class-values.json) 已在 [handson](.) 下创建，或已复制到讲师专用讲义中。
- 所有值都非空。

不要向参与者分享密钥或部署令牌。

---

## 4. 为 Todo 应用配置参与者登录权限

Bicep 部署会创建 SPA 应用注册。讲师必须确保参与者能够登录已部署的 Todo 应用。

### 4.1 验证重定向 URI

在 Microsoft Entra 管理中心：

1. 打开 **Microsoft Entra ID** -> **App registrations**。
2. 使用 `$clientId` 中的 Application (client) ID 搜索。
3. 打开 **Authentication**。
4. 确认存在以下 SPA 重定向 URI：

   - `$staticWebAppUrl`
   - `http://localhost:5173/`

如果只有带尾部斜杠的值，也要补充不带尾部斜杠的值。

成功标准：

- 测试参与者可以完成登录，不会出现 redirect URI mismatch 错误。

### 4.2 授予或确认 API 同意

在同一个应用注册中：

1. 打开 **API permissions**。
2. 确认应用所需的 Microsoft Graph 委托权限（如 `User.Read`）以及日历场景启用时相关的日历权限。
3. 如果租户不允许用户自行同意，选择 **Grant admin consent**。

成功标准：

- 不会因同意提示阻塞参与者登录。
- 测试参与者可从已部署的 Todo app URL 登录。

### 4.3 将参与者分配到 Enterprise Application

如果你希望控制谁可以访问 Todo 应用，请使用此步骤。

1. 打开 **Microsoft Entra ID** -> **Enterprise applications**。
2. 按部署创建的应用注册显示名搜索，或按 Application ID `$clientId` 搜索。
3. 打开 **Properties**。
4. 将 **Assignment required?** 设置为 **Yes**。
5. 打开 **Users and groups** -> **+ Add user/group**。
6. 添加研讨会参与者安全组或单个参与者账号。

如果你将 **Assignment required?** 保持为 **No**，则租户内用户只要同意和重定向 URI 正确即可登录。对于课堂管控，建议启用必须分配并使用参与者组。

成功标准：

- 已分配的参与者账号可以登录。
- 若启用了 Assignment required，未分配账号无法访问应用。

### 4.4 参与者登录冒烟测试

使用一个参与者级测试账号。

1. 在浏览器隐私窗口中打开 `$staticWebAppUrl`。
2. 登录。
3. 确认 **Todos** 和 **Projects** 页面可加载。
4. 选择一次 **Generate 50 Test Todos** 以准备课堂数据，或由讲师账号在课前准备数据。

成功标准：

- 参与者可登录。
- Todo 数据可加载。
- 没有出现 `AADSTS` 重定向/同意/分配错误。

---

## 5. 为参与者的 Cosmos DB MCP 部署准备 Container Apps 环境

目标是让参与者能够部署自己的 Cosmos DB MCP Container App，而无需自行创建 Container Apps 环境或构建 MCP 镜像。

参与者应拿到已构建好的镜像、已分配的 Container Apps 环境，以及唯一的 Container App 名称。

### 5.1 验证并复用 azd 部署的 ACR 镜像

不要再创建新的 ACR，也不要手动构建 MCP Toolkit 镜像。`azd up` 流程已经：

1. 创建课堂 ACR。
2. 在该 ACR 中构建 `mcp-toolkit:<tag>`。
3. 在讲师 MCP Container App 上激活该镜像。

使用第 3 节记录的值：

| 值         | 来源                          |
| ---------- | ----------------------------- |
| Registry   | `$cosmosMcpAcrLoginServer`  |
| Repository | `$cosmosMcpImageRepository` |
| Tag        | `$cosmosMcpImageTag`        |
| Full image | `$cosmosMcpImage`           |

ACR Admin user 保持禁用状态。每个课堂 Container Apps 环境都使用自己的 system-assigned managed identity，并在该 ACR 上被授予 `AcrPull`。参与者在创建 Container App 时，需选择环境系统标识作为 registry 身份验证。

验证现有镜像：

```powershell
az acr repository show-tags `
  --name $cosmosMcpAcrName `
  --repository $cosmosMcpImageRepository `
  --output table
```

成功标准：

- `az acr repository show-tags` 能看到 `$cosmosMcpImageTag`。
- 讲师在 Portal 创建测试 Container App 时可以选择该镜像。

### 5.2 创建共享 Container Apps 环境

为每个共享 Container Apps 环境启用 system-assigned identity，并将该身份在课堂 ACR 上授予 `AcrPull`。这个环境身份仅用于拉取共享镜像。每位参与者的 Container App 还需要单独启用自己的 system-assigned identity，用于 Cosmos DB 和 Foundry 运行时访问。

推荐容量规划：

- 每个 Container Apps 环境不超过 8 位参与者。
- 每位参与者对应一个唯一 Container App 名称。
- 大班请使用多个环境。
- 每个参与者 MCP 应用建议使用 `0.5` vCPU、`1 GiB` 内存，且最多 1 个副本。

使用 `environmentCount = Ceiling(participantCount / 8)`。创建每个环境时开启 system-assigned identity。以下命令直接使用 Azure Resource Manager，不依赖 Azure CLI `containerapp` 扩展：

```powershell
$participantCount = 24
$participantsPerEnvironment = 8
$environmentCount = [Math]::Ceiling($participantCount / $participantsPerEnvironment)
$environmentPrefix = "cae-todomanagement-workshop"

1..$environmentCount | ForEach-Object {
  $environmentName = "{0}-{1:D2}" -f $environmentPrefix, $_
  $environmentResourceId = "/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.App/managedEnvironments/$environmentName"
  $environmentBody = @{
    location = $location
    identity = @{
      type = "SystemAssigned"
    }
    properties = @{}
  }
  $environmentBodyFile = Join-Path $HOME "$environmentName.json"

  try {
    $environmentBody | ConvertTo-Json -Depth 10 | Set-Content $environmentBodyFile -Encoding utf8
    az rest `
      --method put `
      --url "https://management.azure.com$($environmentResourceId)?api-version=2024-03-01" `
      --headers "Content-Type=application/json" `
      --body "@$environmentBodyFile" `
      --output none
  }
  finally {
    Remove-Item $environmentBodyFile -ErrorAction SilentlyContinue
  }
}
```

当每个环境都报告 `Succeeded` 且 `identity.principalId` 非空后，为每个环境系统身份授予 `AcrPull`：

```powershell
$acrId = az acr show `
  --name $cosmosMcpAcrName `
  --resource-group $resourceGroup `
  --query id `
  --output tsv

1..$environmentCount | ForEach-Object {
  $environmentName = "{0}-{1:D2}" -f $environmentPrefix, $_
  $environmentResourceId = "/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.App/managedEnvironments/$environmentName"
  $environmentPrincipalId = az rest `
    --method get `
    --url "https://management.azure.com$($environmentResourceId)?api-version=2024-03-01" `
    --query identity.principalId `
    --output tsv

  if ([string]::IsNullOrWhiteSpace($environmentPrincipalId)) {
    throw "System identity is not ready for $environmentName. Confirm provisioning and rerun this role-assignment block."
  }

  az role assignment create `
    --assignee-object-id $environmentPrincipalId `
    --assignee-principal-type ServicePrincipal `
    --role AcrPull `
    --scope $acrId
}
```

PUT 响应初期可能显示 `Waiting`。Azure 完成预配后，请确认所有环境都已就绪并具备 system-assigned identity：

```powershell
1..$environmentCount | ForEach-Object {
  $environmentName = "{0}-{1:D2}" -f $environmentPrefix, $_
  $environmentResourceId = "/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.App/managedEnvironments/$environmentName"

  az rest `
    --method get `
    --url "https://management.azure.com$($environmentResourceId)?api-version=2024-03-01" `
    --query "{Name:name,State:properties.provisioningState,Location:location,Identity:identity}" `
    --output json
}
```

示例映射：

| Participant range | Environment                        | Container App names                        |
| ----------------- | ---------------------------------- | ------------------------------------------ |
| 1-8               | `cae-todomanagement-workshop-01` | `mcp-toolkit-p01` to `mcp-toolkit-p08` |
| 9-16              | `cae-todomanagement-workshop-02` | `mcp-toolkit-p09` to `mcp-toolkit-p16` |

在共享环境中，Container App 名称必须唯一。请为每位参与者记录一个分配环境和一个唯一 Container App 名称。

开课前检查配额和当前使用量：

```powershell
1..$environmentCount | ForEach-Object {
  $environmentName = "{0}-{1:D2}" -f $environmentPrefix, $_
  $environmentResourceId = "/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.App/managedEnvironments/$environmentName"

  az rest `
    --method get `
    --url "https://management.azure.com$($environmentResourceId)/usages?api-version=2024-03-01" `
    --query "value[].{Name:name.localizedValue,Current:currentValue,Limit:limit}" `
    --output table
}
```

如果某个环境接近 app 数量或 consumption-core 配额，请在课前新增环境并迁移一个参与者分组。

成功标准：

- 所有环境都报告 `Succeeded`。
- 所有环境都报告 `identity.type` 为 `SystemAssigned`，且 `identity.principalId` 非空。
- 所有环境系统身份都在课堂 ACR 上拥有 `AcrPull`。
- 开课前已检查环境 usage/quota。
- 参与者只能在其被分配的环境中创建 Container App。

### 5.3 授予参与者访问权限

对于每位参与者或参与者组，授予：

| 作用域                              | 角色                           | 原因                                                                                                   |
| ----------------------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------ |
| 课堂 ACR                            | Owner                          | 使参与者在本实验流程中可在 Portal 浏览/选择共享镜像                                                     |
| 已分配的 Container Apps 环境        | Container Apps Contributor     | 使参与者能在预创建环境中创建其 MCP Container App                                                       |
| 参与者资源组                        | Owner or Contributor           | 使参与者可创建其分配的 Container App 资源                                                              |
| 共享 Cosmos DB 账户                 | DocumentDB Account Contributor | 使参与者可为其 Container App identity 创建 Cosmos DB SQL 数据平面角色分配                             |

这些较宽泛权限适用于临时培训实验，不应直接作为生产环境指导。

每位参与者在创建 Container App 后会启用 system-assigned identity。除非参与者有权限在共享资源上做 role assignment，否则实验中需由讲师完成以下分配：

- 在共享 Cosmos 账户上，把 `Cosmos DB Built-in Data Reader` 分配给该 identity。
- 在参与者 Foundry 资源上，把 `Foundry User` 分配给该 identity。
- 在参与者 Enterprise Application 上，把 `MCP Tool Executor` 分配给 Foundry project managed identity。

参与者 Container App 的 system identity 不需要 `AcrPull`，因为 registry 身份验证使用的是 Container Apps 环境 system identity。

参与者还需要有权限创建应用注册。如果他们无法把用户或托管身份分配到 Enterprise Application 角色，则由讲师执行这些分配。

`DocumentDB Account Contributor` 应分配给参与者账号或参与者组。不要把它分配给 Container App identity。Container App identity 只需要上面列出的运行时角色。

成功标准：

- 测试参与者只能选择被分配的 Container Apps 环境。
- 测试参与者可选择被分配环境的 system identity 用于 registry 身份验证。
- 测试参与者可选择课堂 ACR 镜像。
- 测试参与者无需创建新环境即可创建唯一命名的 Container App。
- 测试参与者可针对共享 Cosmos DB 账户运行 `az cosmosdb sql role assignment create`。

### 5.4 需要发给每位参与者的值

请准备按参与者区分的发放表：

| 项目                                | 示例                                                      |
| ----------------------------------- | --------------------------------------------------------- |
| Todo 应用 URL                       | `$staticWebAppUrl`                                        |
| Foundry 区域                        | `$location`                                               |
| Registry                            | `$cosmosMcpAcrLoginServer`                                |
| Image                               | `$cosmosMcpImageRepository`                               |
| Tag                                 | `$cosmosMcpImageTag`                                      |
| 分配的 Container Apps 环境          | `cae-todomanagement-workshop-01`                          |
| 环境资源组                          | `rg-todomanagement-instructor`                            |
| 环境区域                            | `japaneast`                                               |
| 环境 identity principal ID          | 分配环境的 system identity principal ID                   |
| 唯一 Container App 名称             | `mcp-toolkit-p01`                                         |
| 参与者 ID                           | `p01`                                                     |
| Cosmos endpoint                     | `$cosmosEndpoint`                                         |
| Cosmos account name                 | `$cosmosAccountName`                                      |
| Cosmos resource group               | `$resourceGroup`                                          |
| Cosmos resource ID                  | `$cosmosAccountId`                                        |
| Tenant ID                           | `$tenantId`                                               |

不要向参与者提供 deployment tokens、app secrets、ACR 密码或讲师凭据。

---

## 6. 开课前的 Foundry 准备

参与者实验会创建参与者专属的 Foundry 资源、项目和模型部署。请在课前准备好订阅访问、模型可用性和配额。

1. 保留 Bicep 创建的 Foundry 资源、`proj-todomanagement` 项目和模型部署，供讲师持有的 Todo 应用使用。
2. 确认研讨会订阅中已注册 `Microsoft.CognitiveServices`。
3. 确认每位参与者在其参与者资源组上有 Contributor 或 Owner 权限。
4. 确认 `text-embedding-3-small` 和 `gpt-5.4-mini` 在讲师指定的 Foundry 区域可用。
5. 确认所有参与者部署所需的模型配额充足。
6. 用一个参与者账号测试：可创建 `aifoundry-todomanagement-p01`、可创建 `proj-todomanagement-p01`，并可部署 `text-embedding-3-small-p01`。
7. 确认参与者在部署 `text-embedding-3-small` 后、创建 MCP Container App 前，能够部署 `gpt-5.4-mini`。
8. 删除该测试 Foundry 资源，或将其保留用于讲师彩排。

成功标准：

- Foundry Playground 提示词 `List all databases in my Cosmos DB account.` 返回 `todo-db`。
- Todo app Copilot 面板对 `What should I prioritize today?` 能返回答案。

---

## 7. 讲师最终彩排

使用一个测试参与者账号。

### Todo App

1. 打开 `$staticWebAppUrl`。
2. 登录。
3. 打开 **Todos**。
4. 确认已存在生成的数据。
5. 打开 **Projects** -> **View Graph**。
6. 向 Copilot 提问：`What should I prioritize today?`

### Participant MCP Setup

1. 按参与者说明创建一个测试 Container App。
2. 使用被分配的共享 Container Apps 环境。
3. 选择课堂 ACR 镜像。
4. 配置必需的环境变量。
5. 打开 MCP 测试 UI。
6. 登录并调用 `List Databases`。
7. 在 `todo-db/todos` 上调用 `Vector Search`，搜索文本为 `adoption-plan`。
8. 确认 `OPENAI_ENDPOINT` 使用参与者资源的 `https://<resource>.openai.azure.com/` 端点，并且 embedding 调用成功且无 `401 Unauthorized`。

### Foundry

1. 创建一个参与者专属 Foundry 资源和项目。
2. 部署一个参与者专属 `text-embedding-3-small` 部署。
3. 若该资源尚未可用，则部署 `gpt-5.4-mini`。
4. 在该项目中创建 Prompt agent 和 MCP 连接。
5. 提问：`List containers in database todo-db.`
6. 打开 Trace。
7. 确认可见 Cosmos DB 工具调用。

仅当上述三个区域全部成功时，彩排才算通过。

---

## 8. 课堂运行计划

| 时间      | 活动                                                                        | 负责人            |
| --------- | --------------------------------------------------------------------------- | ----------------- |
| 0-10 分钟 | 讲解架构和已准备资源                                                        | 讲师              |
| 10-30 分钟 | 参与者创建 Foundry 资源、项目和 embedding 部署                             | 参与者            |
| 30-55 分钟 | 参与者在已准备环境中部署/使用 Cosmos DB MCP Container App                  | 参与者            |
| 55-75 分钟 | 参与者创建 Prompt agent 并连接 Cosmos DB MCP 工具                          | 讲师引导          |
| 75-85 分钟 | Trace 阅读练习                                                              | 参与者            |
| 85-90 分钟 | Prompt 调优与总结                                                           | 参与者            |

---

## 9. 故障处理

| 症状                                                 | 讲师处理动作                                                                  |
| ---------------------------------------------------- | ----------------------------------------------------------------------------- |
| `azd up` 在预配期间失败                              | 课前修复基础设施；不要在课堂上与参与者一起实时排障                            |
| SWA API 链接失败                                     | 手动执行 Static Web App -> APIs -> Function App 链接                          |
| 参与者无法登录                                       | 检查 Enterprise Application 分配、同意和重定向 URI                            |
| 参与者无法选择 ACR 镜像                              | 检查 ACR Owner 分配和 Admin user 设置                                         |
| 参与者无法选择 Container Apps 环境                   | 检查环境作用域上的 Container Apps Contributor 分配                            |
| MCP 工具无法列出数据库                               | 检查 Cosmos endpoint、managed identity/app role，以及 tenant/client ID        |
| Foundry 工具调用失败                                 | 使用预先准备的备用 agent 或预采集 trace，并继续授课流程                       |

开课前请至少准备一个已验证可用的测试参与者账号和一个已验证可用的 MCP Container App。
