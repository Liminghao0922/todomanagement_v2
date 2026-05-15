# Todo Management v2

[English](README.md) | [简体中文](README-zh_CN.md) | [日本語](README-ja_JP.md)

Full-stack sample for AI-augmented Todo Management. The v2 stack is **serverless and identity-aware**: an Azure Functions (Python) backend talks to Azure Cosmos DB (NoSQL + Gremlin) and Azure OpenAI, a Vue 3 + Vite SPA is hosted on Azure Static Web Apps, and an Azure AI Foundry agent provides an in-app chat experience.

## System Overview

The infrastructure is designed to be **serverless, identity-based, and AI-ready**, with every backend dependency reachable via Microsoft Entra ID.

![Architecture](images/01.Architecture.png)

## Architecture At A Glance
- **Backend**: Azure Functions (Python 3.11, anonymous HTTP auth, system-assigned managed identity) exposing Todo / Project / Conversation / Tool / Chat / Graph endpoints
- **Data**: Azure Cosmos DB serverless account with a SQL database (`todo-db`: `todos`, `owners`, `projects`, `conversations`) and a Gremlin database (`todo-graph-db` / `todo-graph`) holding `BLOCKED_BY`, `PRECEDES`, `SUBTASK_OF`, `SIMILAR_TO` edges
- **AI**: Azure OpenAI (`gpt-4o-mini` for chat, `text-embedding-3-small` for vector search) and an Azure AI Foundry agent invoked from the Function App via the `azure.ai.projects` SDK
- **Frontend**: Vue 3 + Vite SPA on Azure Static Web Apps (Todos, Todo Edit, Projects, and a Cytoscape-based Project Graph view), with MSAL sign-in
- **Identity**: Microsoft Entra ID app registration for the SPA (`User.Read`, `Calendars.Read`); managed identity on the Function App used for Gremlin (Cosmos data plane), Foundry, and OpenAI when AAD mode is enabled
- **Reference**: `docs/ARCHITECTURE_GUIDE.md`

## Repository Structure
- `src/api`: Azure Functions backend (`function_app.py` HTTP routes, `functions/` CRUD modules, `services/` for Cosmos / OpenAI / Foundry / Gremlin)
- `src/web`: Vue 3 SPA (MSAL sign-in, Todos / Projects / Project graph / Chat features)
- `infra`: Bicep templates and `deploy.ps1` for Cosmos, Functions, SWA, OpenAI, Foundry, and the Graph app registration
- `docs`: architecture and supporting documentation
- `handson`: step-by-step deployment / quick reference / troubleshooting guides
- `foundry-agent-config.json`: reference Foundry agent definition (instructions, built-in tools, custom `estimate_hours` tool)

## Local Run
Prerequisites: Python 3.11, Azure Functions Core Tools v4, Node 18+, npm.

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
Edit `local.settings.json` to point at a real Cosmos DB account (or the local Cosmos emulator), Azure OpenAI deployment, and Foundry project endpoint. The Functions code auto-creates missing Cosmos databases / containers when `COSMOS_AUTO_CREATE=true`.

Web
```powershell
cd src\web
copy .env.example .env.local
npm install
npm run dev  # http://localhost:5173
```
During local development, Vite proxies `/api` to the local Functions host. For production, run `npm run build` (output in `dist/`) and deploy to Azure Static Web Apps; SWA forwards `/api/*` to the linked Function App.

## HTTP API Surface
All endpoints are served under `/api` (see `src/api/function_app.py`):

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness probe |
| GET / POST | `/todos` | List / create todos (vector + keyword search via `?search=`) |
| PATCH / DELETE | `/todos/{todo_id}` | Update / delete a todo |
| POST | `/generate-todos` | Seed demo todos (auto-creates a project if needed) |
| POST | `/owners` | Create an owner |
| GET / POST | `/projects` | List / create projects |
| GET / PATCH / DELETE | `/projects/{project_id}` | Read / update / delete a project |
| POST | `/tools/estimate-hours` | Vector-search-based effort estimation (Foundry custom tool) |
| POST | `/chat` | Foundry agent proxy + transcript persistence |
| GET | `/conversations` | List saved chat transcripts |
| GET / DELETE | `/conversations/{doc_id}` | Read / delete a transcript |
| GET | `/graph/related` | Traverse Gremlin edges (`?todoId=...&relation=SIMILAR_TO`) |

The user identity is resolved from `x-user-id` header / `userId` query / JSON body, defaulting to `demo-user` for local dev.

## Deployment
The IaC flow lives under `infra/`:

1. Run `infra/deploy.ps1` — provisions Cosmos (SQL + Gremlin, serverless), Azure OpenAI (with `gpt-4o-mini` and `text-embedding-3-small` deployments), the Function App + plan + storage, the Static Web App, the Foundry-handoff resource, and the Microsoft Graph app registration.
2. Record the outputs (Function URL, SWA URL, Cosmos endpoints, Entra App ID / tenant, Foundry resource).
3. Configure the Foundry agent in the Azure AI Foundry portal using `foundry-agent-config.json` as a reference (built-in Microsoft Graph + Cosmos tools, custom `estimate_hours` REST tool pointing at `<function-app>/api/tools/estimate-hours`).
4. Deploy Function code (`func azure functionapp publish ...`) and the Web build (SWA CLI or GitHub Actions).
5. Validate Todo CRUD, vector search, Project graph, and the Foundry chat round-trip.

See `handson/DEPLOY_GUIDE.md` for the full English walkthrough.

## Related Docs
- `docs/ARCHITECTURE_GUIDE.md`
- `handson/DEPLOY_GUIDE.md`
- `handson/QUICK_REFERENCE.md`
- `handson/TROUBLESHOOTING.md`
- `infra/README.md`
