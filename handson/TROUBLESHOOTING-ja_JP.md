# 🔧 トラブルシューティング ガイド v3

v3 デプロイ中に問題が発生した場合の対応方法。

---

## 問題 1: Bicep デプロイが失敗する

### 症状

```
az deployment group create が Failed
```

### 診断方法

```powershell
# デプロイの詳細なエラーを確認
az deployment group list --resource-group rg-todomanagement-dev --query "[0].properties.error" -o json
```

### よくある原因と対応

#### 原因 A: graphClientSecret が無効

**エラー:**
```
Invalid client credentials. Credentials are not recent.
```

**対応:**
1. Service Principal を再作成:
```powershell
$sp = az ad sp create-for-rbac --name "todo-backend-new" --role Contributor --json-auth | ConvertFrom-Json
```
2. 新しい clientSecret を parameters.json に入力
3. デプロイ再実行

#### 原因 B: foundryAgentEndpoint が存在しない

**エラー:**
```
Endpoint URL validation failed
```

**対応:**
- Foundry Agent をまだ作成していない場合は、空文字列 `""` を設定
- デプロイ後に Update で対応可能

#### 原因 C: リソース グループ存在しない

**エラー:**
```
The resource group 'rg-todomanagement-dev' could not be found.
```

**対応:**
```powershell
az group create --name rg-todomanagement-dev --location japaneast
```

---

## 問題 2: Function が 401 エラーを返す

### 症状

```
curl https://[functionUrl]/api/health
→ 401 Unauthorized
```

### 診断方法

```powershell
# Function App の環境変数を確認
az functionapp config appsettings list --name [functionAppName] --resource-group rg-todomanagement-dev --output table

# 必須変数の有無を確認:
# - COSMOS_ENDPOINT
# - COSMOS_KEY
# - AZURE_OPENAI_ENDPOINT
# - GRAPH_TENANT_ID
# - GRAPH_CLIENT_ID
# - GRAPH_CLIENT_SECRET
```

### よくある原因と対応

#### 原因 A: GRAPH_CLIENT_SECRET が無効

**確認:**
```powershell
$secret = $(az functionapp config appsettings list --name [functionAppName] --resource-group rg-todomanagement-dev --query "[?name=='GRAPH_CLIENT_SECRET'].value" -o tsv)
echo "Secret: $secret"
```

**対応:**
1. Service Principal を確認:
```powershell
az ad sp list --display-name "todo-backend*" --output table
```
2. 新しい パスワードを生成:
```powershell
az ad sp credential reset --id [object-id]
```
3. Function App の setting を更新:
```powershell
az functionapp config appsettings set --name [functionAppName] --resource-group rg-todomanagement-dev --settings GRAPH_CLIENT_SECRET=[new-secret]
```

#### 原因 B: Cosmos Key が無効

**確認:**
```powershell
az cosmosdb keys list --name [cosmosAccountName] --resource-group rg-todomanagement-dev --type keys
```

**対応:**
Function App の COSMOS_KEY を更新。

---

## 問題 3: Static Web App で 404 が返される

### 症状

```
https://[swa-url]/ にアクセス
→ 404 Not Found
```

### 診断方法

```powershell
# SWA のビルド ログを確認
az staticwebapp show --name [staticWebAppName] --resource-group rg-todomanagement-dev

# デプロイ済みファイルを確認
az staticwebapp show --name [staticWebAppName] --resource-group rg-todomanagement-dev --query "properties" -o json
```

### よくある原因と対応

#### 原因 A: dist/ フォルダが空

**確認:**
```powershell
cd src/web
npm run build
ls dist/
# index.html 存在確認
```

**対応:**
```powershell
az staticwebapp upload --name [staticWebAppName] --source ./dist
```

#### 原因 B: VITE_AZURE_CLIENT_ID が未設定

**確認:**
```powershell
cd src/web
cat .env.local | grep VITE_AZURE_CLIENT_ID
```

**対応:**
1. `.env.local` ファイルを作成
2. VITE_AZURE_CLIENT_ID 等を入力
3. `npm run build` 再実行
4. SWA へ再デプロイ

---

## 問題 4: Foundry Agent チャットが応答しない

### 症状

```
POST /api/chat
→ Timeout または 500 error
```

### 診断方法

```powershell
# Foundry リソースが存在するか確認
az cognitiveservices account list --resource-group rg-todomanagement-dev --output table

# Function ログで Foundry 呼び出しを追跡
func azure functionapp logstream [functionAppName]
```

### よくある原因と対応

#### 原因 A: FOUNDRY_AGENT_ENDPOINT が無効

**確認:**
```powershell
$endpoint = $(az functionapp config appsettings list --name [functionAppName] --resource-group rg-todomanagement-dev --query "[?name=='FOUNDRY_AGENT_ENDPOINT'].value" -o tsv)
echo "Endpoint: $endpoint"
```

**対応:**
1. Foundry Portal で Agent Project を作成
2. 正しい Endpoint URL をコピー
3. parameters.json 更新 → Bicep 再デプロイ

#### 原因 B: FOUNDRY_AGENT_API_KEY が無効

**確認:**
```powershell
# Foundry Portal でキーを再生成
# 新しいキーを parameters.json に入力
# Bicep 再デプロイ
```

---

## 問題 5: 日历扫描 (Timer Trigger) が実行されない

### 症状

```
6 時間ごとの定時実行が見当たらない
```

### 診断方法

```powershell
# Function App の統合ログを確認
az monitor log-analytics query \
  --workspace [log-analytics-workspace-id] \
  --analytics-model-name FunctionAppLogs \
  --query "where FunctionName == 'timer_trigger' | take 10"

# または Function App ログストリーム
func azure functionapp logstream [functionAppName] --tail 100
```

### よくある原因と対応

#### 原因 A: GRAPH_TENANT_ID/CLIENT_ID が無効

**対応:**
1. Service Principal の有効性を確認:
```powershell
az ad sp show --id [client-id]
```
2. Calendars.Read 権限があるか確認:
```powershell
az ad app permission list --id [client-id]
```

#### 原因 B: オーナーが Cosmos に存在しない

**確認:**
```powershell
# Cosmos から owners 取得
# まず todo-db database の owners コンテナ確認
az cosmosdb sql container show --account-name [cosmosAccountName] --database-name todo-db --name owners --resource-group rg-todomanagement-dev
```

**対応:**
- テストデータをコンテナに手動挿入

---

## 問題 6: Cosmos Gremlin クエリが失敗

### 症状

```
GET /api/graph/related
→ 502 Bad Gateway または timeout
```

### 診断方法

```powershell
# Gremlin エンドポイント確認
$gremlinEndpoint = $(az functionapp config appsettings list --name [functionAppName] --resource-group rg-todomanagement-dev --query "[?name=='COSMOS_GREMLIN_ENDPOINT'].value" -o tsv)
echo "Endpoint: $gremlinEndpoint"

# Function ログで graph_service 例外を確認
```

### よくある原因と対応

#### 原因 A: COSMOS_KEY が正しくない

**対応:**
```powershell
az cosmosdb keys list --name [cosmosAccountName] --resource-group rg-todomanagement-dev
```

Key を更新してから Function App の COSMOS_KEY を変更。

#### 原因 B: todo-graph-db または todo-graph が存在しない

**確認:**
```powershell
az cosmosdb gremlin database list --account-name [cosmosAccountName] --resource-group rg-todomanagement-dev
```

**対応:**
Bicep デプロイが完了しているか確認。必要に応じて再実行。

---

## 🆘 最後のリセット

問題が解決しない場合、すべてを削除して再デプロイ:

```powershell
# 1. リソース グループを削除
az group delete --name rg-todomanagement-dev --yes --no-wait

# 2. 削除の確認までしばらく待機（5～10分）

# 3. 新しくデプロイを再実行
az group create --name rg-todomanagement-dev --location japaneast
cd infra
az deployment group create \
  --resource-group rg-todomanagement-dev \
  --template-file main.bicep \
  --parameters parameters.json
```

---

## 📞 ヘルプリソース

- 完全ガイド: `DEPLOY_GUIDE-ja_JP.md`
- アーキテクチャ: `docs/ARCHITECTURE_GUIDE-ja_JP.md`
- Function チュートリアル: https://learn.microsoft.com/ja-jp/azure/azure-functions/
- Cosmos DB Gremlin: https://learn.microsoft.com/ja-jp/azure/cosmos-db/gremlin/
- Azure AI Foundry: https://learn.microsoft.com/ja-jp/azure/ai-services/foundry/

---

**うまくいかない場合は、上記の確認リストを順に進めてください！**
