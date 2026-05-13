# Todo Management

[English](README.md) | [简体中文](README-zh_CN.md) | [日本語](README-ja_JP.md)

Todo Management 全栈示例。当前 v3 架构使用 Azure Functions + Azure Cosmos DB（NoSQL + Gremlin Graph）作为后端，Vue 3 + Vite 前端托管在 Azure Static Web Apps，并集成 Azure AI Foundry。

## 系统总览

该基础设施以**私有、安全、基于身份**为核心设计，不依赖硬编码密钥。

![Architecture](images/01.Architecture.png)

## 架构速览
- 后端: Azure Functions（Python），提供 Todo API、自定义工具端点、定时任务
- 数据层: Azure Cosmos DB Serverless（`todos`/`owners`/`projects` 容器 + `todo-graph` Gremlin 图）
- 前端: Vue 3 + Vite，部署到 Azure Static Web Apps
- AI: Azure OpenAI + Azure AI Foundry（Web UI）
- 身份认证: Microsoft Entra ID 应用注册（`User.Read`、`Calendars.Read`）
- 参考: `docs/ARCHITECTURE_GUIDE-zh_CN.md`

## 仓库结构
- `src/api`: Azure Functions 后端
- `src/web`: Vue 3 SPA（MSAL 登录、Todo/搜索功能）
- `infra`: Bicep 模板、部署脚本、参数文件
- `docs`: 架构与配套文档

## 本地运行
前置: Python 3.11、Azure Functions Core Tools、Node 18+、npm

API（Azure Functions）
```powershell
cd src\api
copy local.settings.example.json local.settings.json
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
func start
# 健康检查: http://localhost:7071/api/health
```

本地运行时，请在 `local.settings.json` 中填写 Cosmos/OpenAI/Graph/Foundry 相关配置。

Web
```powershell
cd src\web
copy .env.example .env.local
npm install
npm run dev  # http://localhost:5173
```

本地开发时，Vite 会把 `/api` 代理到本地 Functions。生产构建执行 `npm run build`，产物输出到 `dist/`。

## 部署
标准部署流程:
1. 运行 `infra/deploy.ps1` 部署基础设施
2. 记录 Function URL、SWA URL、Cosmos Endpoint、Entra App ID、Foundry 资源输出
3. 在 Foundry Web UI 创建 Agent，接入内置 Graph/Cosmos 工具与 `/api/tools/estimate-hours`
4. 部署 Function 代码与 Web 静态资源
5. 验证 Todo CRUD、AI 抽取、定时扫描流程

完整中文部署说明见 `handson/DEPLOY_GUIDE-zh_CN.md`。

## 相关文档
- `docs/ARCHITECTURE_GUIDE-zh_CN.md`
- `handson/DEPLOY_GUIDE-zh_CN.md`
- `infra/README.md`
