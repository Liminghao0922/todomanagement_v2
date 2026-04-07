# Todo Management v3 部署指南

[English](DEPLOY_GUIDE.md) | [简体中文](DEPLOY_GUIDE-zh_CN.md) | [日本語](DEPLOY_GUIDE-ja_JP.md)

完整部署指南：从 GitHub 模板到 Azure 上线。预计时间: 45~60 分钟。

## 前置条件

- Azure 订阅（Owner 或 Contributor + User Access Administrator）
- Microsoft Entra ID 应用注册权限
- GitHub 账户
- 安装 Azure CLI、PowerShell 7+、Git
- 安装 Node 18+、npm

## 步骤 1: 从模板克隆仓库

1. 打开 https://github.com/Liminghao0922/todomanagement
2. 点击 **Use this template** → **Create new repository**
3. 仓库名: 例 `my-todo-app`
4. 可见性: Public 或 Private
5. 点击 **Create repository from template**

## 步骤 2: 准备 Azure 环境

### 2.1 设置订阅

```powershell
az login
az account list
az account set --subscription "<your-subscription-id>"
```

### 2.2 创建资源组

```powershell
$rg = "rg-todomanagement-dev"
$location = "japaneast"
az group create --name $rg --location $location
```

### 2.3 本地克隆仓库

```powershell
git clone https://github.com/[username]/[repo].git
cd [repo]
```

## 步骤 3: 配置基础设施参数

编辑 `infra/parameters.json`:

```json
{
  "location": "japaneast",
  "environment": "dev",
  "projectName": "todomanagement",
  "foundryAgentEndpoint": "",
  "foundryAgentApiKey": "",
  "graphTenantId": "",
  "graphClientId": "",
  "graphClientSecret": ""
}
```

获取 `graphTenantId`:
```powershell
az account show --query tenantId -o tsv
```

## 步骤 4: 部署基础设施 (Bicep)

```powershell
cd infra

az deployment group validate \
  --resource-group $rg \
  --template-file main.bicep \
  --parameters parameters.json

az deployment group create \
  --resource-group $rg \
  --template-file main.bicep \
  --parameters parameters.json

az deployment group show \
  --resource-group $rg \
  --name main \
  --query properties.outputs
```

### 记录关键输出

- functionAppName, functionAppUrl
- staticWebAppName, staticWebAppUrl
- cosmosEndpoint, appRegistrationClientId
- tenantId, foundryResourceName

## 步骤 5: 创建 Entra ID 应用注册 (Web 前端)

```powershell
$appName = "todo-management-web"
$app = az ad app create --display-name $appName | ConvertFrom-Json
$appId = $app.appId

$replyUrls = @(
  "https://[your-swa-url]/"
  "http://localhost:5173/"
)
az ad app update --id $appId --reply-urls $replyUrls

az ad app permission add --id $appId \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions e1fe6dd8-ba31-4d61-89e6-40ba127554c7=Scope 570282fd-fa5c-430b-a940-f708cd10ae6e=Scope

az ad app permission admin-consent --id $appId

echo "应用 ID: $appId"
```

## 步骤 6: 创建 Service Principal (Graph API/日历扫描)

```powershell
$spName = "todo-management-backend"
$sp = az ad sp create-for-rbac --name $spName --role Contributor | ConvertFrom-Json

$graph_tenant_id = $sp.tenant
$graph_client_id = $sp.clientId
$graph_client_secret = $sp.password

az ad app permission add --id $graph_client_id \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions 798ee544-9d2d-430c-9da2-d3a3b914dfd4=Role

az ad app permission admin-consent --id $graph_client_id

echo "后端 SP Client ID: $graph_client_id"
```

## 步骤 7: 更新参数 (Part 2)

将 Entra 值填入 `infra/parameters.json`，重新部署

## 步骤 8: 部署 Function 代码

```powershell
cd ../src/api

copy local.settings.example.json local.settings.json

python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# 本地测试
func start

# 部署到 Azure
func azure functionapp publish [functionAppName] --build remote
```

## 步骤 9: 部署 Web 前端

```powershell
cd ../web

npm install
npm run build

az staticwebapp upload \
  --name [staticWebAppName] \
  --source ./dist
```

## 步骤 10: 配置 Foundry Agent

1. Azure Portal → AI Foundry 资源 → Web UI
2. 新建 Agent Project
3. 配置:
   - 模型: gpt-4o-mini
   - 内置工具: Microsoft Graph + Cosmos DB
   - 自定义工具: `/api/tools/extract-action-items`

## 步骤 11: 验证部署

```powershell
cd ../../infra
.\validate-deployment.ps1 -ResourceGroupName $rg
```

## 步骤 12: 测试应用

1. 打开 SWA URL
2. Entra ID 登录
3. 创建 Todo、搜索、Foundry 聊天
4. 检查 Function 日志

详见 [docs/ARCHITECTURE_GUIDE-zh_CN.md](../docs/ARCHITECTURE_GUIDE-zh_CN.md)。
