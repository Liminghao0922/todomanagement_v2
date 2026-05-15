# Troubleshooting (v2)

[English](TROUBLESHOOTING.md) | [简体中文](TROUBLESHOOTING-zh_CN.md) | [日本語](TROUBLESHOOTING-ja_JP.md)

Symptoms and resolutions for the most common issues encountered while deploying or running Todo Management v2.

---

## 1. Bicep deployment failures

### `InvalidTemplateDeployment: ... region not supported`

The chosen region does not have one of: Cosmos DB serverless, Azure OpenAI capacity, Azure AI Foundry, SWA, Functions Linux Y1.

**Fix.** Pick a region that supports all of them. Confirmed working: `japaneast`, `eastus`, `westus3`. Update `infra/parameters.json` → `location` and re-run `deploy.ps1`.

### `Authorization failed for ... role assignment`

The signed-in user lacks `User Access Administrator`.

**Fix.** Use an account with `Owner` on the subscription, or have an `Owner` perform the role assignments listed in [`DEPLOY_GUIDE.md`](DEPLOY_GUIDE.md) Step 6 / Step 8.

### `Conflict: app registration name already exists`

The SPA app registration name from a previous run still exists.

**Fix.** Delete the stale `todomanagement-spa` from **Microsoft Entra ID → App registrations** and re-deploy, or change `projectName` in `parameters.json`.

---

## 2. Function App / API issues

### `/api/health` returns 502 / 503

Possible causes: cold start, Python deployment failed, app settings missing.

**Fix.**
1. `az functionapp log tail -g $rg -n $func` to see the live log.
2. Confirm the publish succeeded with `func azure functionapp publish $func --python` (no red errors).
3. In the Portal → Function App → **Configuration**, confirm `FUNCTIONS_WORKER_RUNTIME=python`, `COSMOS_ENDPOINT`, `OPENAI_ENDPOINT` are present.

### `azure.cosmos.exceptions.CosmosHttpResponseError: Forbidden ... AAD`

The Function App's managed identity does not have a Cosmos data-plane role.

**Fix.**

```powershell
$mi     = az functionapp identity show -g $rg -n $func --query principalId -o tsv
$cosmos = az cosmosdb list -g $rg --query "[0].name" -o tsv
az cosmosdb sql role assignment create `
  --account-name $cosmos -g $rg `
  --role-definition-id "00000000-0000-0000-0000-000000000002" `
  --principal-id $mi --scope "/"
```

Then restart the Function App. Note that the built-in role `Cosmos DB Built-in Data Contributor` (id `...000000002`) is required for both reads and writes.

### `gremlin_python.driver.protocol.GremlinServerError: 401 Unauthorized`

Gremlin auth uses an AAD token scoped to `https://cosmos.azure.com/.default`. If the token is rejected, the role assignment in the previous section is missing OR `COSMOS_GRAPH_ACCOUNT` points to a different Cosmos account.

**Fix.**
- Confirm `COSMOS_GRAPH_ACCOUNT` is just the **account name** (no `https://`, no `.gremlin.cosmos.azure.com`).
- Confirm the role assignment is on the same Cosmos account that hosts `todo-graph-db`.
- The graph endpoint is constructed as `wss://<account>.gremlin.cosmos.azure.com:443/`.

### `openai.AuthenticationError` or `401` from OpenAI

The Function App can't acquire a token for Azure OpenAI.

**Fix.** Grant the Function App's managed identity the role `Cognitive Services OpenAI User` on the OpenAI resource:

```powershell
$aoai = az cognitiveservices account list -g $rg --query "[?kind=='OpenAI'] | [0].id" -o tsv
az role assignment create `
  --assignee-object-id $mi --assignee-principal-type ServicePrincipal `
  --role "Cognitive Services OpenAI User" --scope $aoai
```

### `openai.NotFoundError: deployment 'gpt-4o-mini' not found`

Deployment name in `OPENAI_DEPLOYMENT_CHAT` (or `_EMBEDDING`) doesn't match what's in Azure OpenAI.

**Fix.** Either rename the deployment in the OpenAI portal to `gpt-4o-mini` / `text-embedding-3-small`, or update the Function App settings to match the actual deployment names. Then restart the Function App.

---

## 3. Foundry / chat issues

### `/api/chat` returns `{"status":"not_configured"}`

The Function App is missing one of `FOUNDRY_PROJECT_ENDPOINT`, `FOUNDRY_AGENT_NAME`, `FOUNDRY_AGENT_VERSION`.

**Fix.** Set the three settings (see [QUICK_REFERENCE.md §7](QUICK_REFERENCE.md#7-azure-ai-foundry)) and restart the Function App.

### `azure.core.exceptions.HttpResponseError: agent_reference 'todo-agent/1' not found`

The agent name or version in the app settings does not match what exists under the Foundry project.

**Fix.** In the Foundry portal, open **Agents**, copy the exact agent name + active version, and update `FOUNDRY_AGENT_NAME` / `FOUNDRY_AGENT_VERSION`.

### Foundry agent's `estimate_hours` tool returns 502

The Foundry agent calls the public Function URL, but the Function App is asleep, redirecting, or rejecting CORS.

**Fix.**
- Ensure the Function App URL in the tool definition matches `<function-app>.azurewebsites.net/api/tools/estimate-hours` exactly (no trailing slash).
- The endpoint is anonymous in v2 — no key needed.
- Add a CORS rule in the Function App (`*` for testing): `az functionapp cors add -g $rg -n $func --allowed-origins "*"`.

### Conversations not persisted to Cosmos

The `/api/chat` handler best-effort writes to the `conversations` container.

**Fix.**
- Confirm the container `conversations` exists in `todo-db` with partition key `/owner_id`.
- If you need automatic creation, set `COSMOS_AUTO_CREATE=true` and restart the Function App.

---

## 4. Web (Static Web App) issues

### MSAL: `AADSTS50011: redirect URI mismatch`

The redirect URI configured in the SPA does not match what the SPA sent.

**Fix.**

```powershell
$swa = az staticwebapp list -g $rg --query "[0].defaultHostname" -o tsv
$cid = az ad app list --display-name "todomanagement-spa" --query "[0].appId" -o tsv

az ad app update --id $cid `
  --set "spa.redirectUris=['https://$swa/','http://localhost:5173/']"
```

Then sign out + sign back in.

### `/api/*` returns 404 from the SWA

The SWA is not proxying to the Function App.

**Fix.** Ensure `src/web/staticwebapp.config.json` contains:

```json
{
  "navigationFallback": { "rewrite": "/index.html" },
  "routes": [
    { "route": "/api/*", "rewrite": "https://<function-app>.azurewebsites.net/api/*" }
  ]
}
```

Rebuild and re-deploy with `swa deploy`.

### "MSAL config missing" on first load

`.env.local` (dev) or the production `.env` was not picked up at build time.

**Fix.** Confirm the three `VITE_AZURE_*` variables exist before running `npm run build`. Then redeploy.

---

## 5. Cosmos data issues

### Vector search returns no results

`list_todos` falls back to in-process cosine similarity over `embedding` fields. If todos were created before the embedding deployment was reachable, they have `null` embeddings and are skipped.

**Fix.** Re-create the todos, or run `/api/generate-todos` to seed fresh items with embeddings.

### Project graph is empty

Either the Gremlin DB doesn't exist, the partition key on `todo-graph` isn't `/owner_id`, or no relations were created yet.

**Fix.**
- Confirm the graph exists in **Cosmos Data Explorer** under the Gremlin account.
- Run `/api/generate-todos` to seed sample relations.
- Tail the Function App log for `graph_service` warnings.

---

## 6. Local-development issues

### `func start` exits with `ModuleNotFoundError`

The virtual environment isn't activated, or `requirements.txt` wasn't installed in it.

**Fix.**

```powershell
cd src/api
.\.venv\Scripts\activate
pip install -r requirements.txt
func start
```

### CORS error during `npm run dev`

The Vite dev server runs on `http://localhost:5173` but calls the Function App at `http://localhost:7071`.

**Fix.** Add the dev origin in `local.settings.json`:

```json
"Host": {
  "CORS": "http://localhost:5173",
  "CORSCredentials": true
}
```

Restart `func start`.

---

## 7. Where to look next

- Architecture & data flow: [`docs/ARCHITECTURE_GUIDE.md`](../docs/ARCHITECTURE_GUIDE.md)
- Step-by-step deploy: [`handson/DEPLOY_GUIDE.md`](DEPLOY_GUIDE.md) (IaC), [`handson/DEPLOY_GUIDE_GUI.md`](DEPLOY_GUIDE_GUI.md) (Portal)
- Most-used commands: [`handson/QUICK_REFERENCE.md`](QUICK_REFERENCE.md)
- Function source: `src/api/function_app.py` (entry routes) and `src/api/services/*.py`
