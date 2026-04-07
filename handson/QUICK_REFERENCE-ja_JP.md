# 📋 v3 デプロイメント クイックリファレンス

**5分で全体を把握するための参考表**

---

## 🎯 全体フロー（v3 構成）

```
┌─────────────────────────────────────────────────────┐
│ 1️⃣ GitHub Template をクローン                       │
│    (Use this template)                              │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 2️⃣ ローカル環境または Cloud Shell (PowerShell)    │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 3️⃣ リポジトリをダウンロード（git clone）          │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 4️⃣ infra/parameters.json を修正                    │
│    - location, environment, graphTenantId,         │
│    - graphClientId, graphClientSecret              │
│    - foundryAgentEndpoint, API Key                 │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 5️⃣ Bicep デプロイ実行                              │
│    - az deployment group create                     │
│    ⏱️ 10～15分                                       │
│    出力: Function URL, SWA URL, Cosmos Endpoint   │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 6️⃣ Entra ID アプリ登録新規作成                     │
│    - Web アプリ用（SPA）                           │
│    - Backend 用（Service Principal）              │
│    - スコープ: User.Read, Calendars.Read          │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 7️⃣ Function コード デプロイ                        │
│    - func azure functionapp publish                 │
│    ⏱️ 3～5 分                                        │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 8️⃣ Web フロント ビルド＆デプロイ                   │
│    - npm run build                                  │
│    - az staticwebapp upload                         │
│    ⏱️ 2～5 分                                        │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 9️⃣ Foundry Agent 設定                              │
│    - Portal で新しい Agent Project を作成          │
│    - ビルトインツール＆カスタムツール接続          │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 🔟 デプロイ検証                                     │
│    - ./validate-deployment.ps1                      │
│    - Function Health, Cosmos, SWA確認              │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 1️⃣1️⃣ アプリに アクセス                             │
│    https://[your-swa-url]                           │
│    ✅ 完了！Todo 作成・AI チャット可能              │
└─────────────────────────────────────────────────────┘
```

---

## 🔑 重要な設定値

### infra/parameters.json

```json
{
  "location": "japaneast",
  "environment": "dev",
  "projectName": "todomanagement",
  "foundryAgentEndpoint": "https://...",
  "foundryAgentApiKey": "[secret]",
  "graphTenantId": "[Entra tenant ID]",
  "graphClientId": "[Service Principal client ID]",
  "graphClientSecret": "[Service Principal secret]"
}
```

### デプロイ出力（記録する）

| 項目 | 値の例 | 用途 |
|------|--------|------|
| functionAppName | `func-todomanagement-xxxxx` | コード デプロイ対象 |
| functionAppUrl | `https://func-todomanagement-xxxxx.azurewebsites.net` | API Endpoint |
| staticWebAppName | `swa-todomanagement-xxxxx` | Web ビルド デプロイ対象 |
| staticWebAppUrl | `https://[uuid].azurestaticapps.net` | ユーザー向け URL |
| cosmosEndpoint | `https://cosmos-todomanagement-xxxxx.documents.azure.com:443/` | Cosmos 接続 |
| appRegistrationClientId | `[UUID]` | Web フロント MSAL 設定 |
| tenantId | `[UUID]` | Entra ID テナント |
| foundryResourceName | `cog-todomanagement-xxxxx` | Foundry Agent ホスト |

---

## ⚡ コマンド クイック集

### Step 5: Bicep デプロイ

```powershell
cd infra
az deployment group create \
  --resource-group rg-todomanagement-dev \
  --template-file main.bicep \
  --parameters parameters.json
```

### Step 6: Entra ID 設定（Web アプリ）

```powershell
$appId = az ad app create --display-name "todo-web" | ConvertFrom-Json | Select -ExpandProperty appId
az ad app update --id $appId --reply-urls "https://[swa-url]/" "http://localhost:5173/"
az ad app permission add --id $appId --api 00000003-0000-0000-c000-000000000000 --api-permissions e1fe6dd8-ba31-4d61-89e6-40ba127554c7=Scope
```

### Step 6: Service Principal（Backend）

```powershell
$sp = az ad sp create-for-rbac --name "todo-backend" --role Contributor | ConvertFrom-Json
echo "Client ID: $($sp.clientId)"
echo "Tenant: $($sp.tenant)"
echo "Secret: $($sp.password)"
```

### Step 7: Function デプロイ

```powershell
cd ../src/api
func azure functionapp publish [functionAppName] --build remote
```

### Step 8: Web ビルド＆デプロイ

```powershell
cd ../web
npm run build
az staticwebapp upload --name [staticWebAppName] --source ./dist
```

### Step 10: デプロイ検証

```powershell
cd ../../infra
.\validate-deployment.ps1 -ResourceGroupName rg-todomanagement-dev
```

---

## 📝 環境設定ファイル テンプレート

### src/api/local.settings.json

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "...",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "COSMOS_ENDPOINT": "https://cosmos-todomanagement-xxxxx.documents.azure.com:443/",
    "COSMOS_DATABASE_NAME": "todo-db",
    "COSMOS_GREMLIN_ENDPOINT": "wss://cosmos-todomanagement-xxxxx.gremlin.cosmos.azure.com:443/",
    "COSMOS_GREMLIN_DATABASE": "todo-graph-db",
    "AZURE_OPENAI_ENDPOINT": "https://openai-todomanagement-xxxxx.openai.azure.com/",
    "AZURE_OPENAI_CHAT_DEPLOYMENT": "gpt-4o-mini",
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "text-embedding-3-small",
    "FOUNDRY_AGENT_ENDPOINT": "https://[foundry-instance].../api/agents/...",
    "FOUNDRY_AGENT_API_KEY": "[API key]",
    "GRAPH_TENANT_ID": "[tenant-id]",
    "GRAPH_CLIENT_ID": "[service-principal-client-id]",
    "GRAPH_CLIENT_SECRET": "[service-principal-secret]"
  }
}
```

### src/web/.env.local

```env
VITE_AZURE_CLIENT_ID=[appRegistrationClientId]
VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/[tenantId]
VITE_AZURE_REDIRECT_URI=http://localhost:5173
```

---

## 🚨 よくあるエラーと対応

| エラー | 原因 | 対応 |
|---|---|---|
| `Cosmos Endpoint not found` | 環境変数未設定 | local.settings.json を確認 |
| Function returns 401 | Entra ID 認証失敗 | GRAPH_CLIENT_ID/SECRET を確認 |
| SWA blank page | Build 失敗 | `npm run build` ログを確認 |
| Foundry chat error | API Key 無効 | Foundry Portal で Key を再生成 |
| Meeting extraction empty | Graph API 権限不足 | Service Principal に Calendars.Read スコープ確認 |

---

## ✅ チェックリスト

- [ ] GitHub Template クローン完了
- [ ] parameters.json 修正完了（Graph/Foundry 除く）
- [ ] `az group create` 実行
- [ ] Bicep デプロイ($az deployment group create$) 完了
- [ ] 出力値を記録
- [ ] Entra ID アプリ登録 ×2 作成
- [ ] Function コード デプロイ完了
- [ ] Web ビルド＆デプロイ完了
- [ ] Foundry Agent 設定完了
- [ ] `validate-deployment.ps1` 実行 ✓
- [ ] SWA URL にアクセス可能
- [ ] Entra ID ログイン機能確認
- [ ] Todo 作成確認
- [ ] AI Foundry チャット動作確認

---

## 📞 デバッグコマンド（v3）

```powershell
# Function Status
az functionapp show --name [functionAppName] --resource-group rg-todomanagement-dev

# Cosmos Databases
az cosmosdb sql database list --account-name [cosmosAccountName] --resource-group rg-todomanagement-dev

# Function Logs
func azure functionapp logstream [functionAppName]

# SWA Status
az staticwebapp show --name [staticWebAppName] --resource-group rg-todomanagement-dev

# 全削除
az group delete --name rg-todomanagement-dev --yes --no-wait
```

---

**所要時間合計：約 45～60 分**

**難易度：⭐⭐⭐（中程度、Entra ID 複数登録が必要）**

**最終確認：SWA にアクセス → Login → Todo 作成 → AI チャット ✅**
