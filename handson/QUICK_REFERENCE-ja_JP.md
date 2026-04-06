# 📋 デプロイメント クイックリファレンス

**5分で全体を把握するための参考表**

---

## 🎯 全体フロー図

```
┌─────────────────────────────────────────────────────┐
│ 1️⃣ GitHub Template をクローン                       │
│    (Use this template)                              │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 2️⃣ Azure Cloud Shell (PowerShell) を開く          │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 3️⃣ リポジトリをダウンロード（git clone）          │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 4️⃣ infra/parameters.json を修正                    │
│    - location, environment, password など          │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 5️⃣ インフラ デプロイ実行                           │
│    - az group create                                │
│    - ./deploy.ps1                                   │
│    ⏱️ 15～20分                                       │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 6️⃣ 環境変数ファイル (.env.local) 作成            │
│    - src/api/.env.local.example → .env.local        │
│    - src/web/.env.example → .env.local              │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 7️⃣ Entra ID Service Principal 作成                │
│    (GitHub Actions 用認証)                          │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 8️⃣ GitHub Secrets & Variables 設定                │
│    - AZURE_CREDENTIALS (Secret)                     │
│    - ACR_NAME, RESOURCE_GROUP ほか (Variables)    │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 9️⃣ Git Commit & Push                               │
│    (コードをメインブランチに)                       │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 🔟 GitHub Actions 自動実行                          │
│    - API イメージ構築・デプロイ                     │
│    - Web イメージ構築・デプロイ                     │
│    ⏱️ 各 5～10 分                                    │
└────────────────────┬────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────┐
│ 1️⃣1️⃣ Web アプリケーションにアクセス               │
│    https://[your-web-app-url]                       │
│    ✅ 完了！                                         │
└─────────────────────────────────────────────────────┘
```

---

## 🔑 重要な設定値

### infra/parameters.json

```json
{
  "location": "japaneast",              // ← Region
  "environment": "dev",                 // ← dev/staging/prod
  "projectName": "todomanagement",     // ← Resource prefix
  "postgresqlAdminPassword": "Strong@Pass123!"  // ⚠️ 強力に
}
```

### GitHub Actions Variables (9 個)

| 番号 | Variable Name | 取得元 |
|------|---|---|
| 1 | `ACR_NAME` | デプロイ出力 |
| 2 | `RESOURCE_GROUP` | `rg-todomanagement-dev` |
| 3 | `POSTGRES_SERVER` | デプロイ出力 |
| 4 | `POSTGRES_DB` | `tododb` |
| 5 | `POSTGRES_USER` | `postgres` |
| 6 | `AZURE_CLIENT_ID` | Microsoft Entra ID App |
| 7 | `AZURE_TENANT_ID` | Microsoft Entra ID Tenant |
| 8 | `AZURE_REDIRECT_URI` | Web App URL |
| 9 | `API_PROXY_TARGET` | internal API Container App URL |

### GitHub Secrets (1 個)

| Secret Name | 内容 |
|---|---|
| `AZURE_CREDENTIALS` | Service Principal JSON |

---

## ⚡ 実行コマンド（Azure Cloud Shell - PowerShell）

### ステップ 5: インフラ デプロイ

```powershell
# リソースグループ作成
az group create --name rg-todomanagement-dev --location japaneast

# infra フォルダに移動
cd infra

# デプロイスクリプト実行
.\deploy.ps1 -ResourceGroupName "rg-todomanagement-dev" -Location "japaneast"
```

### ステップ 7: Service Principal 作成

```powershell
$subscriptionId = $(az account show --query id -o tsv)
$sp = az ad sp create-for-rbac `
  --name "github-todomanagement-ci" `
  --role "Contributor" `
  --scopes "/subscriptions/$subscriptionId/resourceGroups/rg-todomanagement-dev" `
  --json-auth | ConvertFrom-Json

# JSON 出力（GitHub Secrets に貼り付け）
$sp | ConvertTo-Json
```

### ステップ 11: Web アプリ URL 取得

```powershell
az containerapp show `
  -n todomanagement-web `
  -g rg-todomanagement-dev `
  --query "properties.configuration.ingress.fqdn" `
  -o tsv
```

---

## 📝 .env ファイルテンプレート

### src/api/.env.local.example

```env
DATABASE_TYPE=postgresql
POSTGRES_SERVER=postgres-todomanagement-xxxxx.postgres.database.azure.com
POSTGRES_PORT=5432
POSTGRES_DB=tododb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=[Set during deploy]
ENVIRONMENT=development
```

### src/web/.env.local

```env
VITE_AZURE_CLIENT_ID=[from Entra ID]
VITE_AZURE_AUTHORITY=https://login.microsoftonline.com/[tenant-id]
VITE_AZURE_REDIRECT_URI=http://localhost:5173
```

`/api` はコード側で固定されており、ローカルでは Vite dev proxy、Azure では nginx reverse proxy が internal API Container App に転送します。

---

## 🚨 よくあるエラーと対応

| エラー | 原因 | 対応 |
|---|---|---|
| `AZURE_CREDENTIALS not found` | Secret が未設定 | GitHub Settings で Secret を追加 |
| `ResourceGroup not found` | Variable が間違い | Variable を確認・修正 |
| `Container App deployment failed` | イメージが ACR にない | Actions ログを確認、rebuild 実行 |
| Web にアクセス不可 | Ingress が有効でない | `az containerapp show` で確認 |
| API 接続エラー | CORS 設定 | `src/api/main.py` CORS確認 |

---

## ✅ チェックリスト

- [ ] GitHub Template クローン完了
- [ ] Cloud Shell PowerShell 起動
- [ ] parameters.json 修正完了
- [ ] `az group create` 実行
- [ ] `./deploy.ps1` 実行完了（15～20分待機）
- [ ] .env ファイル作成
- [ ] Service Principal JSON コピー
- [ ] GitHub Secrets に AZURE_CREDENTIALS 設定
- [ ] GitHub Variables 9 個すべて設定
- [ ] `git push` 完了
- [ ] GitHub Actions 実行完了（各 5～10分）
- [ ] Web App URL にアクセス可能
- [ ] ログイン機能確認

---

## 📞 デバッグコマンド

```powershell
# ========== 確認コマンド ==========

# デプロイ状態確認
az deployment group list -g rg-todomanagement-dev --query "[].properties.outputs" -o json

# Container App ステータス
az containerapp show -n todomanagement-web -g rg-todomanagement-dev

# ログ確認
az containerapp logs show -n todomanagement-web -g rg-todomanagement-dev --tail 50

# API ヘルスチェック
curl https://todomanagement-api.abc123def.japaneast.azurecontainerapps.io/health

# PostgreSQL 接続確認
az postgres flexible-server list -g rg-todomanagement-dev --output table

# ========== クリーンアップ ==========

# すべてを削除
az group delete --name rg-todomanagement-dev --yes --no-wait
```

---

## 📚 詳細参照

- **完全ガイド**: `DEPLOY_GUIDE-ja_JP.md`
- **アーキテクチャ**: `docs/ARCHITECTURE_GUIDE-ja_JP.md`
- **インフラ補足**: `infra/README.md`
- **本体ドキュメント**: `README.md`

---

**所要時間合計：約 30～40 分**

**難易度：⭐⭐⭐（中程度）**

**最終確認：Web にアクセスして Login ボタンが動作することを確認！✅**
