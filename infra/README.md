# Bicep 模板使用指南 - Todo Management v3

## 概述

当前 `infra` 目录用于部署 v3 架构，核心资源为：

1. Azure Cosmos DB（NoSQL + Gremlin Graph）
2. Azure Functions（Python，承载 API/工具/定时任务）
3. Azure Static Web Apps（Vue 前端）
4. Azure OpenAI（聊天与向量嵌入）
5. Azure AI Services（Foundry handoff 资源）
6. Microsoft Entra ID App Registration（前端登录与 Graph 权限）

## 文件结构

```text
infra/
├── main.bicep
├── parameters.json
├── bicepconfig.json
├── deploy.ps1
├── validate-deployment.ps1
├── setup-github-secrets.ps1
├── setup-github-variables-update.ps1
└── modules/
    ├── cosmos.bicep
    ├── functions.bicep
    ├── swa.bicep
    ├── openai.bicep
    ├── graph-app-registration.bicep
    └── foundry-handoff.bicep
```

## 快速开始

### 前置条件

- Azure CLI（已登录）
- 目标订阅权限（Contributor 或以上）
- PowerShell 7+

### 1. 修改参数

编辑 `parameters.json`，至少确认以下字段：

- `location`
- `environment`
- `projectName`
- `foundryAgentEndpoint`（可后补）
- `foundryAgentApiKey`（可后补）
- `graphTenantId`
- `graphClientId`
- `graphClientSecret`

### 2. 执行部署

```powershell
cd infra
.\deploy.ps1 -ResourceGroupName "rg-todomanagement-dev" -Location "japaneast"
```

### 3. 验证部署

```powershell
.\validate-deployment.ps1 -ResourceGroupName "rg-todomanagement-dev"
```

脚本会检查资源组内的 Cosmos、Function App、Static Web App、Cognitive Services 以及最近一次部署状态。

## 关键输出与后续配置

部署后请记录并用于后续配置：

- Function App URL
- Static Web App URL
- Cosmos Endpoint
- Entra App Client ID / Tenant ID
- Foundry 资源信息

然后在 Foundry Web UI 中完成 Agent 配置，接入：

- 内置工具（Microsoft Graph、Cosmos 查询）
- 自定义工具（`/api/tools/extract-action-items`）

## GitHub Actions 变量建议

配套脚本 `setup-github-variables-update.ps1` 当前聚焦以下变量：

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_REDIRECT_URI`
- `API_PROXY_TARGET`

如需完整流程，请结合仓库根目录 README 与 `handson` 指南执行。
