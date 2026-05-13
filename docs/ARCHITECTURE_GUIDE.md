# Architecture Guide v3 - Azure Functions + Cosmos DB + Static Web Apps

[English](ARCHITECTURE_GUIDE.md) | [简体中文](ARCHITECTURE_GUIDE-zh_CN.md) | [日本語](ARCHITECTURE_GUIDE-ja_JP.md)

## System Overview

The v3 architecture implements a **cloud-native, serverless, identity-based** design using:
- **Azure Functions** for the backend API and scheduled jobs
- **Azure Cosmos DB** (NoSQL + Gremlin) for data and graph relationships
- **Azure Static Web Apps** for the Vue frontend
- **Azure OpenAI** for vector embeddings and chat models
- **Azure AI Foundry** for agentic AI orchestration with built-in Graph/Cosmos tools
- **Microsoft Entra ID** for authentication and authorization across all services

### High-level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Azure Cloud Environment                   │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Internet → Azure Static Web Apps (SWA)             │   │
│  │  - Vue 3 + Vite frontend                            │   │
│  │  - MSAL browser authentication (Entra ID)           │   │
│  │  - Vite proxy `/api` to Function App                │   │
│  └────────────────┬─────────────────────────────────────┘   │
│                   │                                           │
│  ┌────────────────▼─────────────────────────────────────┐   │
│  │  Azure Functions (Python 3.11)                      │   │
│  │  - HTTP: GET/POST/PATCH/DELETE /todos               │   │
│  │  - HTTP: POST /chat (Foundry proxy)                 │   │
│  │  - HTTP: POST /tools/estimate-hours                 │   │
│  │  - Timer: 0 0 */6 * * * (calendar scan)             │   │
│  │  - Managed Identity: system-assigned               │   │
│  └────────────────┬─────────────────────────────────────┘   │
│                   │                                           │
│  ┌────────────────▼─────────────────────────────────────┐   │
│  │  Azure Cosmos DB                                     │   │
│  │  ├─ SQL API (NoSQL)                                 │   │
│  │  │  ├─ Database: todo-db                            │   │
│  │  │  │  ├─ todos (partition: /owner_id)              │   │
│  │  │  │  ├─ owners (partition: /id)                   │   │
│  │  │  │  └─ projects (partition: /owner_id)           │   │
│  │  │  └─ With vector embeddings (cosmosearch)          │   │
│  │  ├─ Gremlin API (Graph)                             │   │
│  │  │  ├─ Database: todo-graph-db                      │   │
│  │  │  └─ Graph: todo-graph (partition: /owner_id)     │   │
│  │  │     ├─ Vertices: todo nodes                      │   │
│  │  │     └─ Edges: BLOCKED_BY, PRECEDES,              │   │
│  │  │           SUBTASK_OF, SIMILAR_TO                │   │
│  │  └─ Serverless mode (consumption-based)             │   │
│  └────────────────────────────────────────────────────────┘   │
│                   │                                           │
│  ┌────────────────▼─────────────────────────────────────┐   │
│  │  Azure OpenAI Service                                │   │
│  │  ├─ gpt-4o-mini (chat completion)                   │   │
│  │  │  └─ Used for extracing action items from text    │   │
│  │  └─ text-embedding-3-small (embeddings)             │   │
│  │     └─ Used for semantic search in Cosmos           │   │
│  └────────────────────────────────────────────────────────┘   │
│                   │                                           │
│  ┌────────────────▼─────────────────────────────────────┐   │
│  │  Azure AI Foundry (Web UI)                           │   │
│  │  ├─ Agent powered by gpt-4o-mini                    │   │
│  │  ├─ Built-in tools:                                 │   │
│  │  │  ├─ Microsoft Graph (Calendar API)               │   │
│  │  │  └─ Azure Cosmos DB (query + Gremlin)            │   │
│  │  └─ Custom tool endpoint:                           │   │
│  │     └─ POST /api/tools/estimate-hours               │   │
│  │        (vector search over historical todos)        │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  Microsoft Entra ID (Authentication)                 │   │
│  │  ├─ Web: App registration for SPA (MSAL sign-in)     │   │
│  │  │  ├─ Redirect URIs: https://[swa-url]/, local     │   │
│  │  │  ├─ API permissions: User.Read, Calendars.Read    │   │
│  │  │  └─ Delegated (user) scopes                       │   │
│  │  ├─ Functions: Managed Identity (system-assigned)    │   │
│  │  └─ Graph API: Client Credentials (Service App)     │   │
│  │     └─ Permissions: Calendars.Read (app-level)      │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow Layers

### 1. Frontend (SWA) → Backend (Functions)

```
User Browser
    ↓ [MSAL Authentication]
Entra ID → acquires access token
    ↓
SPA (Vue 3)
    ├─ GET /api/health
    ├─ GET /api/todos?pageSize=20&offset=0
    ├─ POST /api/todos (create)
    ├─ PATCH /api/todos/{id} (update)
    ├─ DELETE /api/todos/{id} (delete)
    ├─ POST /api/chat (Foundry proxy)
    └─ POST /api/tools/estimate-hours (custom tool)
         ↓
Azure Functions (local dev: http://localhost:7071/api/...)
         ↓
Cosmos DB / OpenAI / Graph API
```

### 2. Functions → Cosmos DB (NoSQL)

```
Function receives POST /api/todos with { title, description, owner_id ... }
    ↓
1. Generate embedding via OpenAI API
   - Call text-embedding-3-small with (title + description)
2. Create TODO document with embedding field
   - doc = { id: uuid, owner_id, title, description, embedding: [...], ... }
3. Upsert to Cosmos NoSQL container "todos"
4. Sync to Gremlin graph:
   - Create vertex with todo properties
   - Create/update edges for relations (BLOCKED_BY, PRECEDES, etc.)
```

### 3. Functions → Cosmos DB (Gremlin Graph)

```
After todo is created/updated, graph_service synchronizes:
    ↓
1. Upsert vertex (todo node) in graph
   g.V().has('todo','id',todoId).fold()
     .coalesce(unfold(), addV('todo').property('id', todoId)...)
2. For each relation (blockedBy, precedes, subtaskOf, similarTo):
   - Check target todo exists (create if missing)
   - Create/update edge from source → target
3. Query related todos via traversal:
   GET /api/graph/related?owner_id=X&todo_id=Y&relation=SIMILAR_TO
   ↓
   Returns connected todos with properties
```

### 4. Background Task: Calendar Scan → Auto Todo Creation

```
Timer-triggered Function fires every 6 hours
    ↓
1. Query all owners from Cosmos (SELECT id, email FROM owners)
2. For each owner:
   a) Fetch Graph API bearer token (client credentials flow)
   b) Call GET /users/{email}/calendarView?startDateTime=...&endDateTime=...
   c) For each meeting:
      - Extract text from bodyPreview
      - Call OpenAI to extract action items (structured JSON)
      - Deduplicate by (owner_id, meetingId, title)
      - Create todo doc with tags: ["auto", "calendar"]
      - Upsert to Cosmos + sync to Graph
```

### 5. AI Conversation: Foundry Agent Integration

```
User enters query in Foundry Web UI
    ↓
Foundry Agent (gpt-4o-mini) processes request via:
    ↓
1. Built-in Microsoft Graph tool
   → Calls calendar API for user events
2. Built-in Cosmos DB tool (read-only)
   → Executes SQL queries on NoSQL container
   → Or traverses Gremlin graph
3. Custom Function tool: /api/tools/estimate-hours
   → POST { "title": "...", "description": "..." }
   → Returns { "estimatedHours": N, "similarTodos": [...] }
    ↓
Agent chains tool results → generates natural response
    ↓
Response displayed in Foundry UI
```

## Identity & Access Control

### Entra ID App Registration (Frontend)

- **Platform**: SPA (MSAL browser)
- **Client ID**: stored in `.env.VITE_AZURE_CLIENT_ID`
- **Tenant**: directory.microsoft.com
- **Redirect URIs**: `https://[swa].azurestaticapps.net/`, `http://localhost:5173/`
- **Scopes** (delegated): `User.Read`, `Calendars.Read`
- **Token flow**: Authorization Code + PKCE (browser implicit disabled)

### Functions Managed Identity

- **Type**: System-assigned (automatic)
- **Used for**: Authenticating to Cosmos, OpenAI, Graph APIs
- **No secrets stored**: All auth via entra ID token exchange

### Graph API Service Principal (Calendar Scan Job)

- **Type**: App registration with client secret (stored in Key Vault / Function settings)
- **Permissions**: `Calendars.Read` (app-level, not delegated)
- **Flow**: Client credentials → OAuth bearer token → Graph calendarView queries

## Security & Privacy

- **Zero hardcoded secrets**: All credentials resolved at runtime via Entra ID or Key Vault
- **No database passwords**: PostgreSQL auth is now via Entra ID + Cosmos serverless
- **HTTPS everywhere**: SWA → Functions → Cosmos/OpenAI (all encrypted)
- **Cosmos DB partitioning**: Data scoped by `owner_id` to prevent cross-owner data leaks
- **Graph edges represent relationships**: BLOCKED_BY, PRECEDES, SUBTASK_OF link todos logically; queries can filter by edge type

## Deployment & Operations

See [handson/DEPLOY_GUIDE.md](../handson/DEPLOY_GUIDE.md) for step-by-step deployment instructions covering:

1. Infrastructure deployment (Bicep → Functions, Cosmos, SWA, OpenAI, Foundry, Entra registration)
2. Function App code deployment
3. Static Web App build & deploy
4. Foundry agent configuration
5. Local development setup
6. Validation checks
