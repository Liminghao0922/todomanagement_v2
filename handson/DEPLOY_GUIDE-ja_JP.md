# Todo Management v3 デプロイメント ガイド

[English](DEPLOY_GUIDE.md) | [简体中文](DEPLOY_GUIDE-zh_CN.md) | [日本語](DEPLOY_GUIDE-ja_JP.md)

GitHub テンプレートから Azure へのライブ アプリケーション展開まで完全ガイド。所要時間: 45～60分。

## 前置条件

- Azure サブスクリプション (Owner または Contributor + User Access Administrator)
- Microsoft Entra ID アプリ登録権限
- GitHub アカウント
- Azure CLI、PowerShell 7+、Git インストール
- Node 18+、npm インストール

## ステップ 1: テンプレートからリポジトリを複製

1. https://github.com/Liminghao0922/todomanagement を開く
2. **Use this template** → **Create new repository** をクリック
3. リポジトリ名: 例 `my-todo-app`
4. 可視性: Public または Private
5. **Create repository from template** をクリック

## ステップ 2: Azure 環境準備

### 2.1 サブスクリプション設定

```powershell
az login
az account list
az account set --subscription "<your-subscription-id>"
```

### 2.2 リソース グループ作成

```powershell
$rg = "rg-todomanagement-dev"
$location = "japaneast"
az group create --name $rg --location $location
```

### 2.3 リポジトリをローカルにクローン

```powershell
git clone https://github.com/[username]/[repo].git
cd [repo]
```

## ステップ 3: インフラ パラメータ設定

`infra/parameters.json` を編集:

```json
{
  "location": "japaneast",
  "environment": "dev",
  "projectName": "todomanagement",
  "foundryAgentEndpoint": "",
  "foundryAgentApiKey": "",
  "graphTenantId": "",
  "graphClientId": "",
  "graphClientSecret": ""
}
```

`graphTenantId` を取得:
```powershell
az account show --query tenantId -o tsv
```

## ステップ 4: インフラデプロイ (Bicep)

```powershell
cd infra

az deployment group validate \
  --resource-group $rg \
  --template-file main.bicep \
  --parameters parameters.json

az deployment group create \
  --resource-group $rg \
  --template-file main.bicep \
  --parameters parameters.json

az deployment group show \
  --resource-group $rg \
  --name main \
  --query properties.outputs
```

### 主要出力を記録

- functionAppName, functionAppUrl
- staticWebAppName, staticWebAppUrl  
- cosmosEndpoint, appRegistrationClientId
- tenantId, foundryResourceName

## ステップ 5: Entra ID アプリ登録 (Web フロント)

```powershell
$appName = "todo-management-web"
$app = az ad app create --display-name $appName | ConvertFrom-Json
$appId = $app.appId

$replyUrls = @(
  "https://[your-swa-url]/"
  "http://localhost:5173/"
)
az ad app update --id $appId --reply-urls $replyUrls

az ad app permission add --id $appId \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions e1fe6dd8-ba31-4d61-89e6-40ba127554c7=Scope 570282fd-fa5c-430b-a940-f708cd10ae6e=Scope

az ad app permission admin-consent --id $appId

echo "アプリ ID: $appId"
```

## ステップ 6: Service Principal 作成 (Graph API/Calendar Scan)

```powershell
$spName = "todo-management-backend"
$sp = az ad sp create-for-rbac --name $spName --role Contributor | ConvertFrom-Json

$graph_tenant_id = $sp.tenant
$graph_client_id = $sp.clientId
$graph_client_secret = $sp.password

az ad app permission add --id $graph_client_id \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions 798ee544-9d2d-430c-9da2-d3a3b914dfd4=Role

az ad app permission admin-consent --id $graph_client_id

echo "バックエンド SP Client ID: $graph_client_id"
```

## ステップ 7: パラメータアップデート (Part 2)

`infra/parameters.json` に Entra 値を入力して再デプロイ

## ステップ 8: Function コード デプロイ

```powershell
cd ../src/api

copy local.settings.example.json local.settings.json

python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# ローカルテスト
func start

# Azure にデプロイ
func azure functionapp publish [functionAppName] --build remote
```

## ステップ 9: Web フロント デプロイ

```powershell
cd ../web

npm install
npm run build

az staticwebapp upload \
  --name [staticWebAppName] \
  --source ./dist
```

## ステップ 10: Foundry Agent 設定

1. Azure Portal → AI Foundry リソース → Web UI
2. 新しい Agent Project 作成
3. 設定:
   - モデル: gpt-4o-mini
   - ビルトインツール: Microsoft Graph + Cosmos DB
   - カスタムツール: `/api/tools/extract-action-items`

## ステップ 11: デプロイ検証

```powershell
cd ../../infra
.\validate-deployment.ps1 -ResourceGroupName $rg
```

## ステップ 12: アプリケーション テスト

1. SWA URL にアクセス
2. Entra ID でサインイン
3. Todo 作成、検索、Foundry チャット
4. Function ログを確認

詳細は [docs/ARCHITECTURE_GUIDE-ja_JP.md](../docs/ARCHITECTURE_GUIDE-ja_JP.md) を参照。
