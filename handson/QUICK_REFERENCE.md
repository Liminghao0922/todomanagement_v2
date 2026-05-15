# Quick Reference (v2)

[English](QUICK_REFERENCE.md) | [简体中文](QUICK_REFERENCE-zh_CN.md) | [日本語](QUICK_REFERENCE-ja_JP.md)

A condensed cheat sheet of the most useful commands for Todo Management v2.

---

## 1. Local Development

### 1.1 API (Azure Functions, Python 3.11)

```powershell
cd src/api
copy local.settings.example.json local.settings.json   # one-time
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
func start                                             # http://localhost:7071/api/health
```

`local.settings.json` minimum keys:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "COSMOS_ENDPOINT": "https://<cosmos>.documents.azure.com:443/",
    "COSMOS_DATABASE": "todo-db",
    "COSMOS_AUTH_MODE": "key",
    "COSMOS_KEY": "<primary-key>",
    "COSMOS_GRAPH_ACCOUNT": "<cosmos>",
    "COSMOS_GRAPH_DATABASE": "todo-graph-db",
    "COSMOS_GRAPH_NAME": "todo-graph",
    "OPENAI_ENDPOINT": "https://<aoai>.openai.azure.com/",
    "OPENAI_DEPLOYMENT_CHAT": "gpt-4o-mini",
    "OPENAI_DEPLOYMENT_EMBEDDING": "text-embedding-3-small",
    "OPENAI_API_VERSION": "2024-08-01-preview"
  }
}
```

### 1.2 Web (Vue 3 + Vite)

```powershell
cd src/web
copy .env.example .env.local                           # one-time
npm install
npm run dev                                            # http://localhost:5173
```

`.env.local`:

```text
VITE_AZURE_CLIENT_ID=<spa client id>
VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/<tenant id>
VITE_AZURE_REDIRECT_URI=http://localhost:5173
VITE_API_BASE_URL=http://localhost:7071
```

---

## 2. Infrastructure (Bicep)

```powershell
cd infra
.\deploy.ps1   -ResourceGroupName rg-todomanagement-dev -Location japaneast
.\validate-deployment.ps1 -ResourceGroupName rg-todomanagement-dev
```

Re-deploy individual modules after editing:

```powershell
az deployment group create -g rg-todomanagement-dev `
  --template-file modules/functions.bicep `
  --parameters projectName=todomanagement environment=dev location=japaneast
```

---

## 3. Function App lifecycle

```powershell
$rg   = "rg-todomanagement-dev"
$func = az functionapp list -g $rg --query "[0].name" -o tsv

# Publish
cd src/api
func azure functionapp publish $func --python

# Logs (live)
func azure functionapp logstream $func

# Restart
az functionapp restart -g $rg -n $func

# App settings
az functionapp config appsettings list -g $rg -n $func -o table
az functionapp config appsettings set  -g $rg -n $func --settings KEY=value
```

---

## 4. Static Web App lifecycle

```powershell
$rg  = "rg-todomanagement-dev"
$swa = az staticwebapp list -g $rg --query "[0].name" -o tsv
$tok = az staticwebapp secrets list -g $rg -n $swa --query "properties.apiKey" -o tsv

cd src/web
npm run build
swa deploy ./dist --deployment-token $tok --env production
```

---

## 5. Cosmos DB

### 5.1 Switch the Function App to AAD auth

```powershell
$mi     = az functionapp identity show -g $rg -n $func --query principalId -o tsv
$cosmos = az cosmosdb list -g $rg --query "[0].name" -o tsv

az cosmosdb sql role assignment create `
  --account-name $cosmos -g $rg `
  --role-definition-id "00000000-0000-0000-0000-000000000002" `
  --principal-id $mi --scope "/"

az functionapp config appsettings set -g $rg -n $func `
  --settings COSMOS_AUTH_MODE=aad
az functionapp config appsettings delete -g $rg -n $func `
  --setting-names COSMOS_KEY
```

### 5.2 Inspect a container

```powershell
az cosmosdb sql container show -g $rg --account-name $cosmos `
  --database-name todo-db --name todos -o json
```

### 5.3 Query in Data Explorer

```sql
SELECT TOP 10 c.id, c.title, c.status, c.priority, c.created_at
FROM c
ORDER BY c.created_at DESC
```

---

## 6. Azure OpenAI

```powershell
$aoai = az cognitiveservices account list -g $rg `
  --query "[?kind=='OpenAI'] | [0].name" -o tsv

# List deployments
az cognitiveservices account deployment list -g $rg -n $aoai -o table

# Re-create chat deployment
az cognitiveservices account deployment create -g $rg -n $aoai `
  --deployment-name gpt-4o-mini `
  --model-name gpt-4o-mini `
  --model-version "2024-07-18" `
  --model-format OpenAI `
  --sku-capacity 30 --sku-name "Standard"
```

---

## 7. Azure AI Foundry

```powershell
# Reload Foundry settings on the Function App after editing the agent
az functionapp config appsettings set -g $rg -n $func --settings `
  FOUNDRY_PROJECT_ENDPOINT=https://<hub>.services.ai.azure.com/api/projects/prj-todomanagement `
  FOUNDRY_AGENT_NAME=todo-agent `
  FOUNDRY_AGENT_VERSION=1
az functionapp restart -g $rg -n $func
```

Smoke-test `/api/chat`:

```powershell
$base = "https://$func.azurewebsites.net"
curl -X POST "$base/api/chat" `
  -H "Content-Type: application/json" `
  -H "x-user-id: demo-user" `
  -d '{"message":"Estimate hours for Migrate API to Functions"}'
```

---

## 8. Useful HTTP endpoints

| Endpoint | Method | Notes |
| --- | --- | --- |
| `/api/health` | GET | Liveness check |
| `/api/todos?owner_id=demo-user&search=keyword` | GET | List + vector search |
| `/api/todos` | POST | Create todo |
| `/api/todos/{id}?owner_id=demo-user` | PATCH / DELETE | Update / delete |
| `/api/generate-todos` | POST | Demo seeding (dev only) |
| `/api/projects?owner_id=demo-user` | GET / POST | Projects collection |
| `/api/projects/{id}?owner_id=demo-user` | GET / PATCH / DELETE | Project ops |
| `/api/tools/estimate-hours` | POST | Custom tool consumed by Foundry |
| `/api/chat` | POST | Foundry agent entry point |
| `/api/conversations?owner_id=demo-user` | GET | List recent transcripts |
| `/api/conversations/{doc_id}?owner_id=demo-user` | GET / DELETE | Single transcript |
| `/api/graph/related?owner_id=demo-user&todo_id={id}` | GET | Gremlin neighbors |

User identity precedence: `x-user-id` header → `userId` query → JSON body field → fallback `demo-user`.

---

## 9. Cleanup

```powershell
az group delete -n rg-todomanagement-dev --yes --no-wait
# Manually delete the SPA app registration in Microsoft Entra ID portal.
```

---

## See Also

- [`handson/DEPLOY_GUIDE.md`](DEPLOY_GUIDE.md)
- [`handson/DEPLOY_GUIDE_GUI.md`](DEPLOY_GUIDE_GUI.md)
- [`handson/TROUBLESHOOTING.md`](TROUBLESHOOTING.md)
- [`docs/ARCHITECTURE_GUIDE.md`](../docs/ARCHITECTURE_GUIDE.md)
