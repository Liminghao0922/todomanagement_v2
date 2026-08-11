# 讲师准备指南

[English](INSTRUCTOR_PREP_GUIDE.md) | [简体中文](INSTRUCTOR_PREP_GUIDE-zh_CN.md) | [日本語](INSTRUCTOR_PREP_GUIDE-ja_JP.md)

[参与者指南](DEPLOY_GUIDE_GUI-zh_CN.md)

请在研讨会前使用本指南完成准备。参与者不需要 GitHub 帐户，也不需要生成容器。讲师需要准备：

- 一个共享的 Azure Container Registry (ACR)
- 一个预生成的 Cosmos DB MCP Toolkit 映像
- 供参与者 MCP Toolkit 应用使用的共享 Container Apps 环境
- Todo Management v2 公共存储库 URL
- 参与者所需的映像和环境信息

Todo 应用本身仍托管在 Azure Functions 和 Azure Static Web Apps 上。共享容器映像仅用于 Cosmos DB MCP Toolkit。

讲师提前创建好 Container Apps 环境，可以显著节省活动当天的时间。

预计准备时间：30 到 45 分钟。

---

## 先决条件

- 一个可在其中创建资源组和 ACR 的 Azure 订阅
- 在研讨会 ACR 上分配角色的权限
- 创建 Container Apps 环境并在其上分配角色的权限
- Azure Cloud Shell 访问权限
- 对此 Todo Management v2 存储库的访问权限
- 参与者帐户列表
- 参与者侧前提：对各自实验资源组拥有 **Owner**（至少 Contributor 或更高）
- 参与者侧前提：在 Microsoft Entra ID 中拥有 **Application Developer**

> 本指南使用 `az acr build`。容器生成在 ACR 中运行，因此 Cloud Shell 中不需要 Docker。

---

## 1. 创建研讨会 ACR

打开 **Azure Cloud Shell**，切换到 **PowerShell**，并设置研讨会所需的值：

```powershell
$subscriptionId = "<subscription-id>"
$location = "japaneast"
$resourceGroup = "rg-todomanagement-instructor"
$acrName = "<globally-unique-lowercase-name>"
$imageRepository = "mcp-toolkit"
$imageTag = "workshop-$(Get-Date -Format yyyyMMdd)"

az account set --subscription $subscriptionId
az acr check-name --name $acrName
```

ACR 名称必须全局唯一，只能包含小写字母和数字，长度为 5 到 50 个字符。

创建资源组和注册表：

```powershell
az group create `
  --name $resourceGroup `
  --location $location

az acr create `
  --resource-group $resourceGroup `
  --name $acrName `
  --sku Basic `
  --admin-enabled false

az acr update `
  --resource-group $resourceGroup `
  --name $acrName `
  --admin-enabled true
```

为避免参与者在 Portal 创建 Container App 时出现映像访问错误，本工作坊场景下请在创建后启用 ACR **Admin user**。

---

## 2. 生成 MCP Toolkit 映像

讲师可以在准备期间使用 GitHub。参与者不运行这些命令。

```powershell
git clone https://github.com/AzureCosmosDB/MCPToolKit.git
Set-Location MCPToolKit
```

运行时映像需要预先生成的 .NET 输出。检查 .NET 9 SDK 是否可用，然后执行发布：

```powershell
dotnet --version
dotnet publish `
  src/AzureCosmosDB.MCP.Toolkit/AzureCosmosDB.MCP.Toolkit.csproj `
  --configuration Release `
  --output src/AzureCosmosDB.MCP.Toolkit/bin/publish
```

如果 `dotnet --version` 未显示 .NET 9，请先在讲师环境中安装 .NET 9 SDK，然后再继续。

从 MCP Toolkit 存储库根目录运行远程 ACR 生成：

```powershell
az acr build `
  --registry $acrName `
  --image "${imageRepository}:${imageTag}" `
  --file Dockerfile.runtime `
  --platform linux/amd64 `
  .
```

该命令会上传生成上下文，在 Azure 中生成映像，并将其推送到研讨会 ACR。

---

## 3. 验证映像

```powershell
$loginServer = az acr show `
  --resource-group $resourceGroup `
  --name $acrName `
  --query loginServer `
  --output tsv

az acr repository show-tags `
  --name $acrName `
  --repository $imageRepository `
  --output table

$fullImageName = "${loginServer}/${imageRepository}:${imageTag}"
Write-Host "Registry: $loginServer"
Write-Host "Image: $imageRepository"
Write-Host "Tag: $imageTag"
Write-Host "Full image: $fullImageName"
```

Container Apps 使用托管标识拉取映像。

---

## 4. 授予参与者研讨会 ACR 访问权限

参与者在 Portal 中创建 Container App 时直接选择共享映像。下一节创建的共享用户分配的标识具有 `AcrPull` 角色，并会附加到每个研讨会 Container Apps 环境。

对于每位参与者：

1. 在 Azure Portal 中打开研讨会 ACR。
2. 选择 **Access control (IAM)** → **+ Add role assignment**。
3. 选择 **Owner**。
4. 选择 **User, group, or service principal**。
5. 选择参与者帐户并完成分配。

> `Owner` 是研讨会中的便捷做法，使参与者可在创建 Container App 时浏览并选择共享 ACR 映像。请勿在生产环境中为普通应用用户使用这一权限范围过大的角色。

在本工作坊场景下，保持 ACR 管理员用户处于启用状态。

---

## 5. 创建共享 Container Apps 环境

一个 Container Apps 环境可以托管多个参与者的 Container App。同一环境中的应用共享其网络边界和日志记录目标，但每位参与者仍在自己的资源组中部署和管理具有唯一名称的 MCP Toolkit Container App。

首先，创建共享用户分配的托管标识，并向其授予研讨会 ACR 上的 `AcrPull` 角色：

```powershell
$environmentIdentityName = "id-todomanagement-workshop-env"

az identity create `
  --name $environmentIdentityName `
  --resource-group $resourceGroup `
  --location $location

$environmentIdentityId = az identity show `
  --name $environmentIdentityName `
  --resource-group $resourceGroup `
  --query id `
  --output tsv

$environmentIdentityPrincipalId = az identity show `
  --name $environmentIdentityName `
  --resource-group $resourceGroup `
  --query principalId `
  --output tsv

$acrId = az acr show `
  --name $acrName `
  --resource-group $resourceGroup `
  --query id `
  --output tsv

az role assignment create `
  --assignee-object-id $environmentIdentityPrincipalId `
  --assignee-principal-type ServicePrincipal `
  --role AcrPull `
  --scope $acrId
```

该角色的作用域限定为研讨会 ACR，使参与者可以在分配的环境中创建 Container App 时直接选择共享映像。

本研讨会计划每个环境中**不超过 8 位参与者**。每位参与者配置一个 MCP Toolkit 应用，使用 `0.5` vCPU、`1 GiB` 内存，且最多一个副本。如果八个应用同时处于活动状态，其请求的 CPU 总量约为 `8 × 0.5 = 4` vCPU。

Consumption 的 **4 vCPU / 8 GiB** 值是单个副本的最大大小，并非 Container Apps 环境的总计算限制。因此，八位参与者是为确保并发启动和测试具有可预测性而采用的保守研讨会规划上限，并非 Azure 硬性限制。请务必在研讨会前验证实际环境配额。

使用公式 `environmentCount = Ceiling(participantCount / 8)`。

例如，最多 8 位参与者创建一个环境，9–16 位参与者创建两个环境，17–24 位参与者创建三个环境。

在同一 Cloud Shell PowerShell 会话中创建环境：

```powershell
$participantCount = 24
$participantsPerEnvironment = 8
$environmentCount = [Math]::Ceiling($participantCount / $participantsPerEnvironment)
$environmentPrefix = "cae-todomanagement-workshop"

1..$environmentCount | ForEach-Object {
  $environmentName = "{0}-{1:D2}" -f $environmentPrefix, $_

  az containerapp env create `
    --name $environmentName `
    --resource-group $resourceGroup `
    --location $location

  az containerapp env identity assign `
    --name $environmentName `
    --resource-group $resourceGroup `
    --user-assigned $environmentIdentityId
}
```

确认每个环境都已就绪：

```powershell
az containerapp env list `
  --resource-group $resourceGroup `
  --query "[].{Name:name,State:properties.provisioningState,Location:location}" `
  --output table
```

为每位参与者分配一个环境和一个唯一的 Container App 名称，然后记录映射关系。例如，参与者 1–8 使用 `cae-todomanagement-workshop-01`，应用名称为 `mcp-toolkit-p01` 到 `mcp-toolkit-p08`；参与者 9–16 使用 `cae-todomanagement-workshop-02`，应用名称为 `mcp-toolkit-p09` 到 `mcp-toolkit-p16`。

Container App 名称在共享环境中必须唯一。不要为所有参与者分配同一个通用应用名称。

对于每位参与者：

1. 在 Azure Portal 中打开为其分配的 Container Apps 环境。
2. 选择 **Access control (IAM)** → **+ Add role assignment**。
3. 选择 **Container Apps Contributor**。
4. 选择 **User, group, or service principal**。
5. 选择参与者帐户并完成分配。

请在特定 Container Apps 环境作用域（而不是讲师资源组作用域）分配此角色。该角色包含 `Microsoft.App/managedEnvironments/join/action`，允许参与者在共享环境中创建 Container App，但不授予修改或删除环境的权限。参与者还必须对自己的资源组拥有 **Contributor** 或 **Owner** 角色，才能创建和管理分配给自己的 Container App。

> 对于规模更大的研讨会，请为每个环境创建一个 Microsoft Entra 安全组，将分配到该环境的参与者添加到组中，然后在该环境的作用域向该组一次性授予 **Container Apps Contributor** 角色。

研讨会开始前，检查每个环境的当前配额和使用情况：

```powershell
1..$environmentCount | ForEach-Object {
  $environmentName = "{0}-{1:D2}" -f $environmentPrefix, $_

  az containerapp env list-usages `
    --name $environmentName `
    --resource-group $resourceGroup `
    --output table
}
```

如果某个环境接近其应用或 Consumption 核心配额，请在研讨会前另建一个环境，并将一组参与者移至新环境。共享环境适用于此临时实验；需要网络、日志记录、安全性或故障隔离时，请使用独立环境。

📖 参考资料：[Azure Container Apps environments](https://learn.microsoft.com/azure/container-apps/environment) 和 [Container Apps quotas](https://learn.microsoft.com/azure/container-apps/quotas)

---

## 6. 向参与者提供以下信息

| 项目                       | 值                                                               |
| -------------------------- | ------------------------------------------------------------------- |
| 公共存储库 URL      | `https://github.com/Liminghao0922/todomanagement_v2.git`          |
| Registry                   | `<acr-name>.azurecr.io`                                           |
| Image                      | `mcp-toolkit`                                                     |
| Tag                        | `workshop-YYYYMMDD`                                               |
| Container Apps environment | 分配的环境，例如`cae-todomanagement-workshop-01` |
| Environment resource group | `rg-todomanagement-instructor`                                    |
| Environment region         | `japaneast`                                                       |
| Container App name         | 分配的唯一名称，例如`mcp-toolkit-p01`                |

参与者在 Cloud Shell 中运行一条 `git clone` 命令。存储库必须保持公开可读，使参与者无需 GitHub 帐户即可访问。请在研讨会前验证 URL；如果使用其他存储库或分支，请更新该 URL。

参与者在 Azure Portal 中配置自己的 Cosmos endpoint、Foundry endpoint、tenant ID 和 MCP client ID。这些值均不会预置到映像中。

---

## 7. 讲师试运行

使用测试参与者帐户，在研讨会前完整执行一次中文版[参与者指南](DEPLOY_GUIDE_GUI-zh_CN.md)。

确认以下所有事项：

- 无需登录 GitHub 即可在 Cloud Shell 中运行 `git clone`。
- 克隆的存储库包含 `src/api` 和 `src/web`。
- Cloud Shell PowerShell 中提供 `az`、Python 3.11、Functions Core Tools v4 和 Node.js 20。
- `src/web` 的 `npm ci` 和 `npm run build` 成功完成。
- `npx @azure/static-web-apps-cli@latest` 可在 Cloud Shell PowerShell 中运行。
- 测试参与者只能看到并选择实验所需、分配给自己的共享 Container Apps 环境。
- 测试参与者可以在自己的资源组中创建具有唯一名称的 Container App，且无法修改共享环境。
- 测试参与者可以在创建 Container App 时选择共享 ACR 映像。
- MCP Container App 在端口 `8080` 上达到正常运行的修订状态。
- Function App 运行状况终结点返回 `healthy`。
- Static Web Apps 将 `/api/*` 代理到已链接的 Function App。

---

## 8. 研讨会前检查清单

- [ ] 研讨会 ACR 已存在。
- [ ] ACR 管理员用户已启用。
- [ ] `mcp-toolkit` 映像生成成功。
- [ ] 已记录映像标记，且研讨会期间不会更改。
- [ ] 已完成参与者 ACR 角色分配。
- [ ] 共享用户分配的标识在研讨会 ACR 上拥有 `AcrPull` 角色，并已分配给每个 Container Apps 环境。
- [ ] 已根据参与者人数创建足够的 Container Apps 环境。
- [ ] 每个环境均报告 `Succeeded`，且有充足配额。
- [ ] 每位参与者均已映射到一个环境，拥有唯一的 Container App 名称，并在分配的环境上拥有 **Container Apps Contributor** 角色。
- [ ] 每位参与者均可在自己的资源组中创建资源。
- [ ] 无需 GitHub 帐户即可克隆公共存储库。
- [ ] 已向参与者提供 Registry、Image、Tag、分配的 Environment、Environment resource group、Region、唯一 Container App name 和 Repository URL。
- [ ] 已使用参与者级别帐户完成完整试运行且结果通过。

---

## 故障排除

### ACR 名称不可用

选择另一个仅包含小写字母和数字的全局唯一名称：

```powershell
az acr check-name --name "<new-acr-name>"
```

### 远程生成找不到已发布的应用程序

先运行 `dotnet publish`，并验证预期的 DLL 是否存在：

```powershell
Test-Path src/AzureCosmosDB.MCP.Toolkit/bin/publish/AzureCosmosDB.MCP.Toolkit.dll
```

在运行 `az acr build` 前，结果必须为 `True`。

### 参与者无法选择或拉取映像

确认：

- Registry、Repository 和 Tag 完全正确。
- 参与者已获得研讨会 ACR 角色分配。
- ACR 管理员用户已启用。
- Container App 已启用系统分配的托管标识。
- Container App 标识在讲师 ACR 上拥有 `AcrPull` 角色。
- ACR 公共网络设置允许从研讨会环境进行访问。

### 需要新映像

创建新的不可变标记，不要替换已提供给参与者的标记：

```powershell
$imageTag = "workshop-$(Get-Date -Format yyyyMMdd-HHmm)"
az acr build `
  --registry $acrName `
  --image "${imageRepository}:${imageTag}" `
  --file Dockerfile.runtime `
  --platform linux/amd64 `
  .
```

在研讨会开始前，使用新标记更新参与者讲义。