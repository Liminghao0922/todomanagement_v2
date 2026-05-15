# Architecture Guide v2 — Azure Functions + Cosmos DB + Static Web Apps + AI Foundry

[English](ARCHITECTURE_GUIDE.md) | [简体中文](ARCHITECTURE_GUIDE-zh_CN.md) | [日本語](ARCHITECTURE_GUIDE-ja_JP.md)

## System Overview

The v2 architecture implements a **cloud-native, serverless, AI-augmented** Todo platform built around six Azure services:

- **Azure Functions** — Python HTTP backend for Todo / Project / Conversation / Graph / Tool endpoints
- **Azure Cosmos DB (serverless)** — SQL containers for transactional data plus a Gremlin graph for task relations
- **Azure Static Web Apps** — Vue 3 + Vite SPA with MSAL sign-in
- **Azure OpenAI** — `gpt-4o-mini` and `text-embedding-3-small` deployments
- **Azure AI Foundry** — agent that orchestrates Microsoft Graph + Cosmos + the custom `estimate_hours` tool, invoked from the Function App via the `azure.ai.projects` SDK
- **Microsoft Entra ID** — SPA sign-in plus a managed identity on the Function App for Cosmos (Gremlin), Foundry, and AAD-mode OpenAI

### High-level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       Azure Cloud Environment                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User Browser                                                    │
│       │  MSAL (Authorization Code + PKCE)                        │
│       ▼                                                          │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Azure Static Web Apps (SWA)                               │  │
│  │  - Vue 3 + Vite SPA                                        │  │
│  │  - Pages: Todos, Todo Edit, Projects, Project Graph        │  │
│  │  - SWA-managed routing forwards /api/* to Function App     │  │
│  └─────────────────────────┬──────────────────────────────────┘  │
│                            │ HTTPS /api/*                        │
│                            ▼                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Azure Functions (Python 3.11, Linux Consumption)          │  │
│  │  - HTTP routes (anonymous auth, see API surface table)     │  │
│  │  - System-assigned managed identity                        │  │
│  │  - Calls Cosmos / OpenAI / Foundry / Gremlin via SDKs      │  │
│  └─────┬────────────────┬─────────────────┬──────────────────┘  │
│        │                │                 │                      │
│        ▼                ▼                 ▼                      │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────────────────┐   │
│  │ Cosmos DB    │ │ Azure OpenAI │ │ Azure AI Foundry       │   │
│  │ (serverless) │ │              │ │                        │   │
│  │              │ │ - gpt-4o-mini│ │ - Agent (gpt-4o-mini)  │   │
│  │ SQL: todo-db │ │ - text-      │ │ - Built-in tools:      │   │
│  │  • todos     │ │   embedding- │ │    Microsoft Graph     │   │
│  │  • owners    │ │   3-small    │ │    Cosmos query/Gremlin│   │
│  │  • projects  │ │              │ │ - Custom REST tool:    │   │
│  │  • conver-   │ │              │ │    estimate_hours      │   │
│  │    sations   │ │              │ │ - Server-side          │   │
│  │              │ │              │ │   conversations        │   │
│  │ Gremlin:     │ │              │ │                        │   │
│  │  todo-graph- │ │              │ │                        │   │
│  │  db /        │ │              │ │                        │   │
│  │  todo-graph  │ │              │ │                        │   │
│  └──────────────┘ └──────────────┘ └────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Microsoft Entra ID                                        │  │
│  │  - SPA app registration (User.Read, Calendars.Read)        │  │
│  │  - Function App system-assigned managed identity           │  │
│  │  - Optional Graph app registration (Calendars.Read app)    │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Components

### Frontend (`src/web`)
Vue 3 + Vite SPA with these pages:
- `TodosPage.vue` — list, filter, vector-search, and bulk-generate todos
- `TodoEditPage.vue` — create / edit / delete one todo, including relation fields (`blockedBy`, `precedes`, `subtaskOf`, `similarTo`)
- `ProjectsPage.vue` — list / create / edit projects
- `ProjectGraphPage.vue` — Cytoscape-rendered relation graph for a project's todos

Authentication is handled by `@azure/msal-browser` (`src/api/auth.ts`). Required `.env.local` values:

```
VITE_AZURE_CLIENT_ID=<spa-app-registration-client-id>
VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/<tenant-id>
VITE_AZURE_REDIRECT_URI=http://localhost:5173
```

In production, SWA serves `/api/*` from the linked Function App; locally, Vite proxies to `http://localhost:7071`.

### Backend (`src/api`)
`function_app.py` exposes the routes below; concrete handlers live under `functions/`, and shared dependencies under `services/`.

| Method | Route | Module / Function |
| --- | --- | --- |
| GET | `/api/health` | inline |
| GET / POST | `/api/todos` | `crud_todos.list_todos` / `create_todo` |
| PATCH / DELETE | `/api/todos/{todo_id}` | `crud_todos.update_todo` / `delete_todo` |
| POST | `/api/generate-todos` | `crud_todos.generate_todos` |
| POST | `/api/owners` | `crud_owners.create_owner` |
| GET / POST | `/api/projects` | `crud_projects.list_projects` / `create_project` |
| GET / PATCH / DELETE | `/api/projects/{project_id}` | `crud_projects.get_project` / `update_project` / `delete_project` |
| POST | `/api/tools/estimate-hours` | `estimate_hours.estimate` |
| POST | `/api/chat` | `services.foundry_service.chat_with_foundry` (+ `crud_conversations.upsert_conversation`) |
| GET | `/api/conversations` | `crud_conversations.list_conversations` |
| GET / DELETE | `/api/conversations/{doc_id}` | `crud_conversations.get_conversation` / `delete_conversation` |
| GET | `/api/graph/related` | `services.graph_service.query_related` |

User identity (`_resolve_user_id`) is taken from the `x-user-id` header, the `userId` query parameter, or the JSON body, falling back to `demo-user`. The HTTP layer is currently `AuthLevel.ANONYMOUS`; SWA + Entra ID handles user auth in front of it.

### Data (`infra/modules/cosmos.bicep`, `services/cosmos_service.py`)
A single Cosmos DB account in **serverless** mode hosts both APIs:

- SQL database `todo-db`
  - `todos` (partition `/owner_id`) — Todo documents with full metadata, optional `embedding[]`, and relation arrays
  - `owners` (partition `/id`) — Owner records
  - `projects` (partition `/owner_id`) — Project records
  - `conversations` (partition `/owner_id`) — Persisted chat transcripts (best-effort backup of the Foundry server-side conversation)
- Gremlin database `todo-graph-db` / graph `todo-graph` (partition `/owner_id`)
  - Vertices: `todo` (with `id`, `owner_id`, `title`, `status`, `priority`)
  - Edges: `BLOCKED_BY`, `PRECEDES`, `SUBTASK_OF`, `SIMILAR_TO`

`cosmos_service.py` supports three auth modes via `COSMOS_AUTH_MODE`:
- `key` — primary key only
- `aad` — `DefaultAzureCredential` only
- `auto` (default) — primary key when present, otherwise AAD

When `COSMOS_AUTO_CREATE=true` (default for local dev), the service creates missing databases / containers on first use; in Azure with AAD-only credentials the data plane cannot create resources, so Bicep is the source of truth.

### Azure OpenAI (`services/embedding_service.py`)
- Chat deployment: `gpt-4o-mini` (used by the Foundry agent for chat / extraction)
- Embedding deployment: `text-embedding-3-small` (used by `embed_text` for `create_todo`, `update_todo`, `list_todos?search=...`, and `tools/estimate-hours`)

The Function App authenticates with the deployment key by default (`AZURE_OPENAI_KEY`). For an AAD-only deployment, swap in `DefaultAzureCredential` and grant the managed identity `Cognitive Services OpenAI User`.

### Azure AI Foundry (`services/foundry_service.py`, `foundry-agent-config.json`)
The chat endpoint instantiates `AIProjectClient(endpoint=FOUNDRY_PROJECT_ENDPOINT, credential=DefaultAzureCredential())`, derives the underlying OpenAI client, creates a server-side conversation on the first turn (`openai_client.conversations.create()`), then issues `responses.create(...)` with an `agent_reference` extra body pointing at the configured agent (`FOUNDRY_AGENT_NAME`, `FOUNDRY_AGENT_VERSION`).

The reference agent definition (`foundry-agent-config.json`) tells the agent to:
- Use the built-in Microsoft Graph calendar tool to understand availability and deadlines
- Use the built-in Cosmos DB tools (SQL query + Gremlin traversal) to read and modify todos/projects
- Extract action items from pasted meeting notes as structured JSON
- Call the custom `estimate_hours` REST tool (POST `<function-app>/api/tools/estimate-hours`) for vector-search-backed effort estimation

After every successful response, `function_app.py.chat` calls `crud_conversations.upsert_conversation` to persist the user / assistant turn pair into the `conversations` container as a UI-friendly transcript backup.

### Identity & Networking
- **SPA app registration**: SPA platform; redirect URIs include the SWA hostname and `http://localhost:5173`; delegated scopes `User.Read`, `Calendars.Read`. Handled by `infra/modules/graph-app-registration.bicep`.
- **Function App managed identity** (system-assigned): used by `DefaultAzureCredential` in `foundry_service`, `graph_service` (Gremlin AAD token for `https://cosmos.azure.com/.default`), and any AAD-mode Cosmos / OpenAI calls. Grant the identity `Cognitive Services OpenAI User`, `Cosmos DB Built-in Data Contributor`, and the Foundry project's data plane role.
- **No VNet integration today**: all services use public endpoints with HTTPS / WSS. Adding Private Endpoints + VNet integration is the next hardening step.

## Data Flow

### 1. SPA → Functions
```
User → MSAL sign-in → Entra ID
     → SPA calls /api/* (same-origin via SWA, or Vite proxy locally)
     → Function App resolves user_id and dispatches to handlers
     → Handlers fan out to Cosmos / OpenAI / Foundry / Gremlin
```

### 2. Create / Update Todo (vector + graph sync)
```
POST /api/todos
  ├─ embed_text(title + description)         (OpenAI text-embedding-3-small)
  ├─ container.create_item(doc with embedding)  (Cosmos NoSQL, partition /owner_id)
  └─ upsert_todo_vertex(doc)                  (Cosmos Gremlin, AAD token)
       ├─ Upsert vertex(label=todo, id, owner_id, title, status, priority)
       └─ For each relation array (BLOCKED_BY, PRECEDES, SUBTASK_OF, SIMILAR_TO):
            create target vertex if missing, then upsert edge
```
Gremlin failures are logged but **non-fatal** — the SQL write is the source of truth.

### 3. Search Todos
```
GET /api/todos?search=<text>
  ├─ Query SQL container by owner_id (and optional status)
  ├─ embed_text(search) → query_vector
  ├─ Compute cosine_similarity(query_vector, item.embedding) per item
  └─ Sort by _semanticScore desc, then page (offset / pageSize)
```
If embeddings are unavailable, the response falls back to the unsorted SQL ordering.

### 4. Estimate Hours (Foundry custom tool)
```
POST /api/tools/estimate-hours { title, description, category?, complexity? }
  ├─ embed_text(query) (or keyword fallback)
  ├─ Cosmos query: todos with IS_DEFINED(actualHours) AND owner_id = uid
  ├─ Score each candidate via cosine similarity (+ category/complexity boost)
  └─ Return avg / min / max / sampleSize / similarTodos[] / reasoning
```

### 5. Chat with Foundry
```
POST /api/chat { message, conversationId?, conversationDocId? }
  ├─ AIProjectClient.get_openai_client()
  ├─ openai_client.conversations.create()  (first turn only)
  ├─ openai_client.responses.create(
  │      input=f"[user_id={uid}] {message}",
  │      conversation=conversation_id,
  │      extra_body={ agent_reference: { name, version, type: "agent_reference" } })
  ├─ Foundry agent runs: built-in MS Graph + Cosmos tools, custom estimate_hours
  └─ crud_conversations.upsert_conversation(uid, conversation_id, user_msg, answer, doc_id)
```
When `FOUNDRY_PROJECT_ENDPOINT` is unset, the endpoint returns `status="not_configured"` with HTTP 200 so the SPA can render an inline hint instead of an error.

### 6. Graph Traversal
```
GET /api/graph/related?todoId=...&relation=SIMILAR_TO
  └─ g.V().has('todo','id',todoId).has('owner_id', uid)
        .outE(relation).inV()
        .project('id','title','status','priority')
```
The `ProjectGraphPage` Cytoscape view queries this endpoint per relation type to render an interactive graph.

## Configuration Reference

Function App settings (set by `infra/modules/functions.bicep`):

| Setting | Used by | Notes |
| --- | --- | --- |
| `COSMOS_ENDPOINT`, `COSMOS_KEY`, `COSMOS_DATABASE_NAME` | `cosmos_service` | SQL data plane |
| `COSMOS_AUTH_MODE` | `cosmos_service` | `auto` (default), `key`, or `aad` |
| `COSMOS_AUTO_CREATE` | `cosmos_service` | Auto-create DB / containers on first use |
| `COSMOS_GREMLIN_ENDPOINT`, `COSMOS_GREMLIN_DATABASE`, `COSMOS_GREMLIN_GRAPH` | `graph_service` | WSS endpoint + AAD token for Gremlin |
| `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, `AZURE_OPENAI_CHAT_DEPLOYMENT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | `embedding_service`, agent definition | OpenAI deployments |
| `FOUNDRY_PROJECT_ENDPOINT` (or `FOUNDRY_AGENT_ENDPOINT`), `FOUNDRY_AGENT_NAME`, `FOUNDRY_AGENT_VERSION` | `foundry_service` | Foundry agent reference |
| `GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET` | reserved for future Graph-API server flows | Currently provisioned but not consumed by code |

## Security & Operations

- **No hardcoded credentials in source**: all secrets are runtime app settings; Bicep wires them to deployed resource keys (`listKeys()`).
- **Per-owner isolation**: every Cosmos query is partitioned by `owner_id`, and Gremlin traversals are constrained to `has('owner_id', ownerId)`.
- **Resilient AI calls**: embedding / Gremlin / Foundry failures fall back to the next-best behaviour (keyword scoring, log + continue, "not_configured" status) so a degraded AI tier never blocks CRUD.
- **HTTPS / WSS everywhere**: SWA → Functions → Cosmos / OpenAI / Foundry use TLS; Gremlin uses WSS with an AAD-issued bearer token.
- **Telemetry**: enable Application Insights on the Function App for end-to-end tracing of HTTP, Cosmos, and Foundry SDK calls.

## Deployment & Operations

See [handson/DEPLOY_GUIDE.md](../handson/DEPLOY_GUIDE.md) for the full step-by-step guide. The summary order is:

1. Bicep deploy (`infra/deploy.ps1`) — Cosmos, OpenAI, Functions, SWA, Foundry-handoff, Graph app registration
2. Configure the Foundry agent (web UI) using `foundry-agent-config.json` as a reference
3. Publish Function code (`func azure functionapp publish ...`)
4. Build and deploy the Web app (SWA CLI or GitHub Actions)
5. Smoke-test the SPA: sign in → create todos → vector search → open Project Graph → chat with the agent

## Out-of-the-box Limitations and Next Steps

- **No timer-triggered jobs yet** (calendar scan / nightly digest). Add a `@app.timer_trigger` and reuse `services/foundry_service` or Microsoft Graph SDK with the provisioned Graph app registration.
- **Public endpoints** for Cosmos / OpenAI / Foundry. Add Private Endpoints + Function App VNet integration for production hardening.
- **Cosmos still uses primary keys** in the default Bicep wiring. Switch to `COSMOS_AUTH_MODE=aad` and grant the managed identity the `Cosmos DB Built-in Data Contributor` role to remove the last data-plane key.
