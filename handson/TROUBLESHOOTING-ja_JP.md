# 🔧 トラブルシューティング ガイド

デプロイ中に問題が発生した場合の対応方法

---

## 問題 1: GitHub Actions が失敗する

### 症状

```
Build and Deploy API to ACR の Workflow が Failed 状態
```

### 診断方法

1. GitHub リポジトリの **Actions** タブをクリック
2. 失敗した Workflow をクリック
3. **Build and deploy to Container App** ステップを展開
4. エラーメッセージを確認

### よくある原因と対応

#### 原因 A: `AZURE_CREDENTIALS` が設定されていない

**エラー:**
```
Error: Unable to locate credentials. Check that AZURE_CREDENTIALS secret is set up correctly.
```

**対応:**
1. GitHub リポジトリ → **Settings** → **Secrets and variables** → **Secrets**
2. `AZURE_CREDENTIALS` が存在することを確認
3. 値が空でないことを確認
4. JSON 形式が正しいことを確認（括弧がペアになっているか など）

#### 原因 B: 変数名が間違っている

**エラー:**
```
Variable ACR_NAME not found
```

**対応:**
1. **Variables** タブで以下を確認：
   - `ACR_NAME`
   - `RESOURCE_GROUP`
   - その他すべての Variable
2. タイプミスがないことを確認（大文字小文字含む）

#### 原因 C: ACR にログインできない

**エラー:**
```
Error response from daemon: Get https://[acr-name].azurecr.io/v2/: denied: authentication required
```

**対応:**
```powershell
# Cloud Shell で Service Principal の権限を確認
az role assignment list --resource-group rg-todomanagement-dev --output table

# 出力に Contributor が表示されることを確認
```

### 解決手順

```powershell
# 1. Service Principal を作り直す
$subscriptionId = $(az account show --query id -o tsv)
$sp = az ad sp create-for-rbac `
  --name "github-todomanagement-ci" `
  --role "Contributor" `
  --scopes "/subscriptions/$subscriptionId/resourceGroups/rg-todomanagement-dev" `
  --json-auth | ConvertFrom-Json

# 2. GitHub の Secret を更新
# GitHub Settings → Secrets → AZURE_CREDENTIALS を更新

# 3. Workflow を再実行
# Actions ページで Re-run Jobs をクリック
```

---

## 問題 2: Web にアクセスできない

### 症状

```
https://todomanagement-web.abc123.japaneast.azurecontainerapps.io
にアクセスすると：

"404 Not Found" または "Connection refused"
```

### 診断方法

```powershell
# 1. Container App の状態確認
az containerapp show `
  -n todomanagement-web `
  -g rg-todomanagement-dev `
  --query "properties.provisioningState"

# 2. Ingress が有効か確認
az containerapp show `
  -n todomanagement-web `
  -g rg-todomanagement-dev `
  --query "properties.configuration.ingress"

# 3. ログを確認
az containerapp logs show `
  -n todomanagement-web `
  -g rg-todomanagement-dev `
  --tail 50
```

### よくある原因と対応

#### 原因 A: Container App がまだデプロイ中

**確認:**
```powershell
az containerapp show `
  -n todomanagement-web `
  -g rg-todomanagement-dev `
  --query "properties.provisioningState"

# 出力: "Provisioning" または "Updating" → まだ準備中
# 出力: "Succeeded" → 完了
```

**対応:**
- 5～10 分待機してから再度アクセス

#### 原因 B: イメージが ACR にない

**確認:**
```powershell
# ACR 内のイメージ確認
az acr repository list --name [acr-name]

# 出力例:
# - todomanagement-api
# - todomanagement-web
```

**対応:**
```powershell
# GitHub Actions を手動で再実行
# Actions ページで該当 Workflow を選択 → Re-run jobs

# 確認: ログで "Successfully pushed image" が表示されるか
```

#### 原因 C: Ingress が有効でない

**確認:**
```powershell
az containerapp show `
  -n todomanagement-web `
  -g rg-todomanagement-dev `
  --query "properties.configuration.ingress.external"

# 出力: true → 有効
# 出力: false または null → 無効
```

**対応:**
```powershell
# Ingress を有効にする
az containerapp ingress enable `
  -n todomanagement-web `
  -g rg-todomanagement-dev `
  --type "external" `
  --target-port 3000
```

#### 原因 D: ファイアウォールルール

**確認:**
```powershell
# NetworkSecurityGroup の確認
az network nsg list -g rg-todomanagement-dev --output table
```

**対応:**
- ほとんどの場合、Container Apps 環境がデフォルトで正しくセットアップされているため、追加のファイアウォール設定は不要です

---

## 問題 3: API に接続できない（Web にはアクセスできる）

### 症状

```
Web アプリは開くが：
- "Cannot fetch todos"
- コンソールに CORS エラー
- Network リクエストが失敗（401 / 403 / 500）
```

### 診断方法

```powershell
# API の URL を確認
az containerapp show `
  -n todomanagement-api `
  -g rg-todomanagement-dev `
  --query "properties.configuration.ingress.fqdn"

# API の健康チェック
curl https://todomanagement-api.abc123.japaneast.azurecontainerapps.io/health

# 出力例:
# {"status":"healthy","service":"Todo Management API","version":"2.0.0"}
```

### よくある原因と対応

#### 原因 A: API プロキシ設定が正しくない

**確認:**
```bash
# Azure では Web Container App に API_PROXY_TARGET が設定されていることを確認
az containerapp show \
  -n todomanagement-web \
  -g <resource-group> \
  --query "properties.template.containers[0].env[?name=='API_PROXY_TARGET']"
```

**対応:**
- ローカル開発: `vite.config.ts` の `/api` proxy が `http://localhost:7071` を向いていることを確認
- Azure 運用: GitHub Variables で `API_PROXY_TARGET` を internal API URL に設定
- 変更後は Web workflow を再実行して再デプロイ

#### 原因 B: CORS が有効でない

**確認:**
```bash
# curl で OPTIONS リクエスト
curl -X OPTIONS https://todomanagement-api.abc123.japaneast.azurecontainerapps.io/api/todos \
  -H "Origin: https://todomanagement-web.abc123.japaneast.azurecontainerapps.io"

# CORS ヘッダーが返されることを確認
```

**対応:**
```python
# src/api/main.py の確認
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # または特定のオリジンを指定
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 原因 C: PostgreSQL に接続できない（API のログに表示）

**ログ確認:**
```powershell
az containerapp logs show `
  -n todomanagement-api `
  -g rg-todomanagement-dev `
  --tail 50

# 出力でエラーを検索:
# "could not connect to"
# "connection refused"
# "authentication failed"
```

**対応:**
```powershell
# PostgreSQL のステータス確認
az postgres flexible-server show `
  -g rg-todomanagement-dev `
  -n postgres-todomanagement-xxxxx `
  --query "state"

# 出力: "Ready" → 正常
# 出力: "Creating" / "Updating" → 準備中

# エンドポイント確認
az postgres flexible-server show `
  -g rg-todomanagement-dev `
  -n postgres-todomanagement-xxxxx `
  --query "fullyQualifiedDomainName"
```

---

## 問題 4: ログイン機能が動作しない

### 症状

```
Login ボタンをクリックしても：
- 何も起こらない
- エラーポップアップが表示される
- "AADSTS700038" など認証エラー
```

### 診断方法

1. Browser DevTools → **Console** タブを開く
2. エラーメッセージを確認

### よくある原因と対応

#### 原因 A: VITE_AZURE_CLIENT_ID が設定されていない

**エラー:**
```
AADSTS700038: The client identifier [00000000-0000-0000-0000-000000000000] is not valid
```

**対応:**
```powershell
# GitHub Variables の確認
# AZURE_CLIENT_ID が正しい値に設定されているか確認

# 取得方法:
# Azure Portal → Microsoft Entra ID → App registrations
# アプリの "Application (client) ID" をコピー
```

#### 原因 B: リダイレクト URI が登録されていない

**確認:**
1. Azure Portal → Microsoft Entra ID → App registrations
2. アプリを選択
3. **Authentication** → **Platform configurations** → **Single-page application**
4. Redirect URI が表示されていることを確認

**対応:**
```
登録する Redirect URI:

開発環境:
http://localhost:5173

Azure 本番:
https://todomanagement-web.abc123.japaneast.azurecontainerapps.io
```

#### 原因 C: テナント ID が間違っている

**確認:**
```powershell
# Azure CLI で確認
az account show --query tenantId

# または Azure Portal で確認:
# Microsoft Entra ID → Properties → Tenant ID
```

**対応:**
- GitHub Variables の `AZURE_TENANT_ID` を正しい ID に更新
- Web アプリを再デプロイ

---

## 問題 5: デプロイスクリプトが実行できない

### 症状

```
.\deploy.ps1 実行時に:
"deploy.ps1 is not recognized as an internal or external command"
または
"Permission denied"
```

### 診断方法

```powershell
# カレントディレクトリ確認
pwd

# infra フォルダにいることを確認
# 出力: C:\Users\xxx\infra （またはパスの末尾に infra）
```

### 対応方法

#### 方法 1: フルパスで実行

```powershell
# infra ディレクトリに移動
cd infra

# 実行ポリシーを確認（Windows 環境の場合）
Get-ExecutionPolicy

# RemoteSigned に設定（必要な場合）
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

# スクリプト実行
.\deploy.ps1
```

#### 方法 2: PowerShell で明示的に実行

```powershell
powershell -ExecutionPolicy Bypass -File ".\deploy.ps1"
```

#### 方法 3: Cloud Shell では通常すでに設定済み

```powershell
# Cloud Shell 内の場合、そのまま実行可
.\deploy.ps1 -ResourceGroupName "rg-todomanagement-dev" -Location "japaneast"
```

---

## 問題 6: Git コマンドが失敗する

### 症状

```
git push 時に:
"fatal: Authentication failed"
または
"Please make sure you have the correct access rights"
```

### 診断方法

```bash
# Git の設定確認
git config --list

# リモート確認
git remote -v
```

### 対応方法

#### 方法 1: SSH キーを設定（推奨）

```bash
# SSH キーの生成
ssh-keygen -t ed25519 -C "your-email@example.com"

# GitHub に SSH キーを登録
# https://github.com/settings/keys

# リモート URL を SSH に変更
git remote set-url origin git@github.com:your-username/your-repo.git

# 確認
git remote -v
```

#### 方法 2: Personal Access Token を使用

```bash
# GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
# Generate new token で "repo" スコープを選択

# リモート URL を更新
git remote set-url origin https://[token]@github.com/your-username/your-repo.git
```

---

## 問題 7: Azure リソースがリソースグループに表示されない

### 症状

```
Azure Portal で リソースグループを開くと：
- PostgreSQL が見つからない
- Container App が見つからない
- リソースが1つもない
```

### 診断方法

```powershell
# Azure CLI で確認
az resource list -g rg-todomanagement-dev --output table

# リソースグループの確認
az group show -n rg-todomanagement-dev

# デプロイの状態確認
az deployment group list -g rg-todomanagement-dev --query "[].properties.provisioningState" -o table
```

### 対応方法

#### 原因 A: デプロイがまだ実行中

**状態確認:**
```
provisioningState: "Running" / "Updating"
```

**対応:**
- 15～20 分待機
- `az deployment group show` で状態を定期的に確認

#### 原因 B: デプロイが失敗している

**確認:**
```powershell
# 最後のデプロイの詳細を表示
$deployment = az deployment group list -g rg-todomanagement-dev --query "[0]" | ConvertFrom-Json
$deployment.properties.outputs
```

**対応:**
```powershell
# エラーメッセージを確認
# 通常は以下を確認:
# - パスワード要件を満たしているか
# - リージョンが正しいか
# - クォータに達していないか

# 修正後、スクリプトを再実行
.\deploy.ps1 -ResourceGroupName "rg-todomanagement-dev" -Location "japaneast"
```

---

## クリーンアップ：すべてを削除

失敗を繰り返す場合、一度すべて削除してやり直すことをお勧めします。

```powershell
# ⚠️ 注意：すべてのリソースが削除されます

# リソースグループを削除
az group delete `
  --name rg-todomanagement-dev `
  --yes `
  --no-wait

# 確認
az group show -n rg-todomanagement-dev

# 出力: "not found" になれば完全に削除済み
```

---

## 詳細なログ確認

```powershell
# ========== Azure Container App ログ ==========

# Web アプリのログ（最新 50 行）
az containerapp logs show `
  -n todomanagement-web `
  -g rg-todomanagement-dev `
  --tail 50

# API のログ（最新 100 行）
az containerapp logs show `
  -n todomanagement-api `
  -g rg-todomanagement-dev `
  --tail 100

# ========== GitHub Actions ログ ==========

# GitHub Actions の URL:
# https://github.com/[your-username]/[your-repo]/actions

# クリックして詳細ログを表示


# ========== PostgreSQL ログ ==========

az postgres flexible-server log list `
  -g rg-todomanagement-dev `
  -n postgres-todomanagement-xxxxx

# ========== ACR ログ ==========

az acr repository show `
  -n [acr-name] `
  --image-names todomanagement-web:latest
```

---

## サポートが必要な場合

1. **ドキュメント確認**
  - `DEPLOY_GUIDE-ja_JP.md` - 全体ガイド
  - `QUICK_REFERENCE-ja_JP.md` - クイックリファレンス
  - `docs/ARCHITECTURE_GUIDE-ja_JP.md` - アーキテクチャ

2. **GitHub Issues**
   - https://github.com/Liminghao0922/todomanagement/issues

3. **Azure Support**
   - Azure Portal → Help + support

---

**楽しいデプロイを！🚀**

作成日：2026-03-30
