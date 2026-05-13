# Todo Management

[English](README.md) | [简体中文](README-zh_CN.md) | [日本語](README-ja_JP.md)

Full-stack sample for Todo Management that is evolving to an AI-ready architecture. The v3 path uses Azure Functions + Azure Cosmos DB (NoSQL + Graph) backend and Vue 3 + Vite frontend hosted on Azure Static Web Apps, with Azure AI Foundry integration.

## System Overview

The infrastructure is designed to be **private, secure, and identity-based**, with no hardcoded secrets.

![Architecture](images/01.Architecture.png)


## Architecture At A Glance
- Backend: Azure Functions (Python) exposing Todo APIs and custom tool endpoints
- Data: Azure Cosmos DB serverless with SQL containers (`todos`, `owners`, `projects`) and Gremlin graph (`todo-graph`)
- Frontend: Vue 3 + Vite hosted on Azure Static Web Apps
- AI: Azure OpenAI deployments and Azure AI Foundry (web UI) with built-in Graph/Cosmos tools and custom Function tools
- Identity: Microsoft Entra ID app registration with `User.Read` and `Calendars.Read` delegated scopes
- Reference: `docs/ARCHITECTURE_GUIDE.md`

## Repository Structure
- `src/api`: Azure Functions backend (Todo APIs, tool endpoints, timer jobs)
- `src/web`: Vue 3 SPA (MSAL sign-in, Todo/search features)
- `infra`: Bicep templates, deployment scripts, and parameters
- `docs`: architecture and supporting documentation

## Local Run
Prerequisites: Python 3.11, Azure Functions Core Tools, Node 18+, npm.

API (Azure Functions)
```powershell
cd src\api
copy local.settings.example.json local.settings.json
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
func start
# Health check: http://localhost:7071/api/health
```
For local emulation, configure Cosmos/OpenAI values in `local.settings.json`.

Web
```powershell
cd src\web
copy .env.example .env.local
npm install
npm run dev  # http://localhost:5173
```
During local development, Vite proxies `/api` to local Functions. For production, run `npm run build` (output in `dist/`) and deploy to Azure Static Web Apps.

## Deployment
The standard deployment flow is:
1. Deploy infrastructure from `infra/deploy.ps1`
2. Record outputs for Function URL, SWA URL, Cosmos endpoint, Entra App ID, and Foundry resource
3. Configure Azure AI Foundry agent in web UI using built-in Graph/Cosmos tools and custom tool endpoint `/api/tools/estimate-hours`
4. Deploy Function code and Web static assets
5. Validate Todo CRUD, AI extraction, and timer-based calendar scanning pipeline

See `handson/DEPLOY_GUIDE.md` for the full English guide.

## Related Docs
- `docs/ARCHITECTURE_GUIDE.md`
- `handson/DEPLOY_GUIDE.md`
- `infra/README.md`
