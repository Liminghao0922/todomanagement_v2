# 🚀 Todo Management アプリケーション - デプロイメント完全ガイド

[English](DEPLOY_GUIDE.md) | [简体中文](DEPLOY_GUIDE-zh_CN.md) | [日本語](DEPLOY_GUIDE-ja_JP.md)

このドキュメントは、GitHub Template からプロジェクトを Clone し、Azure に デプロイメントするまでの全プロセスを日本語で説明します。

**所要時間：約 30～40 分**

---

## 📋 前提条件

- Azure サブスクリプション権限: `Owner`、または `Contributor` + `User Access Administrator`
- Microsoft Entra ID 側でアプリ登録を作成できる権限
- GitHub アカウント
- Git がインストール済み
- インターネット接続

---

## Step 1️⃣ GitHub Template からプロジェクトを Clone

### 1.1 テンプレートリポジトリにアクセス

1. GitHub で次のリポジトリを開きます（またはご自身の Template Repository）
   - URL: `https://github.com/Liminghao0922/todomanagement`

### 1.2 "Use this template" をクリック

1. リポジトリページの右上にある **"Use this template"** ボタンをクリック
2. **"Create a new repository"** を選択
3. 以下の情報を入力します：

   - **Repository name**: 任意の名前（例：`my-todo-app`）
   - **Description**: 任意（例：`My Todo Management App`）
   - **Visibility**: `Public` または `Private` を選択
   - **Include all branches**: チェック不要
4. **"Create repository from template"** をクリック

---

## Step 2️⃣ Azure Cloud Shell を開く（PowerShell）

### 2.1 Azure Portal にログイン

1. https://portal.azure.com にアクセス
2. Azure アカウントでログイン

### 2.2 Cloud Shell を起動

1. ポータル上部の **Cloud Shell** アイコン（`>_`）をクリック
2. ターミナルが起動します
3. **環境を "PowerShell" に切り替え**（デフォルトが Bash の場合）
   - 左上の環境選択ドロップダウンから **"PowerShell"** を選択

### 2.3 サブスクリプションを確認

```powershell
# 現在のサブスクリプション確認
az account show

# 別のサブスクリプションに切り替える場合
az account set --subscription "<subscription-id>"
```

---

## Step 3️⃣ Cloud Shell 内でリポジトリをダウンロード

### 3.1 リポジトリをクローン

```powershell
# リポジトリをクローン
git clone https://github.com/[your-username]/[your-repo-name].git
cd [your-repo-name]

# 確認
ls
# 出力:
# src/
# infra/
# docs/
# README.md
# など
```

### 3.2 ローカルで事前に設定を変更した場合

ローカルマシンで先に変更してから Push した場合、Cloud Shell で最新のコードを取得します：

```powershell
# Cloud Shell で最新のコードを取得
git pull origin main
```

---

## Step 4️⃣ 基本設定を修正（Cloud Shell 内）

### 4.1 パラメータファイルを編集

```powershell
# パラメータファイルを確認
cat infra/parameters.json
```

**infra/parameters.json** 内容（デフォルト値）：

```json
  {
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "location": {
      "value": "japaneast"    // ← 必要に応じて変更（例：eastus）
    },
    "environment": {
      "value": "dev"   // dev / staging / prod
    },
    "projectName": {
      "value": "todomanagement"   // ← リソース名用
    },
    "postgresqlVersion": {
      "value": "17"
    },
    "postgresqlAdminUsername": {
      "value": "postgres"
    },
    "postgresqlAdminPassword": {
      "value": "Change@Me123!"   // ⚠️ 強力なパスワードに変更！
    },
    "vnetAddressPrefix": {
      "value": "10.0.0.0/16"
    },
    "postgresSubnetPrefix": {
      "value": "10.0.1.0/24"
    },
    "containerAppSubnetPrefix": {
      "value": "10.0.2.0/24"
    }
  }
}
```

### 4.2 Cloud Shell 内で編集（オプション）

PowerShell で直接編集します：

```powershell
# PowerShell で parameters.json を編集
$json = Get-Content infra/parameters.json | ConvertFrom-Json
$json.parameters.location.value = "japaneast"
$json.parameters.environment.value = "handson"
$json.parameters.projectName.value = "mytodoapp001"
$json.parameters.postgresqlAdminPassword.value = "YourStrongPassword@123"
$json | ConvertTo-Json | Set-Content infra/parameters.json
```

**重要な変更項目：**


| 項目                      | 説明                        | 例                                 |
| ------------------------- | --------------------------- | ---------------------------------- |
| `location`                | Azure リージョン            | japaneast / eastus / westeurope    |
| `environment`             | 環境識別子                  | dev (開発) / staging / prod (本番) |
| `projectName`             | リソース名の接頭辞          | myapp / mycompany-todo             |
| `postgresqlAdminPassword` | PostgreSQL 管理者パスワード | Str0ng@Password2024!               |

### 4.3 ⚠️ PostgreSQL パスワードについて

**重要な注釈**：

- **初期化時のみ使用**: `postgresqlAdminPassword` は PostgreSQL サーバー作成時**のみ**必要です
- **アプリケーションアクセス**: このプロジェクトは **ユーザー割り当てマネージド ID（UAI）** を使用しています
  - ✅ アプリケーションはパスワード**なし**で PostgreSQL にアクセス
  - ✅ より安全な認証方式です
  - ✅ 認証情報を環境変数に保存する必要なし
- **パスワード要件**: 以下の条件を満たす必要があります
  - 8 文字以上
  - 大文字を含む
  - 小文字を含む
  - 数字を含む
  - 記号を含む

**例**: `Str0ng@Password2024!`

---

## Step 5️⃣ インフラストラクチャをデプロイ

### 5.1 変数を設定

```powershell
# 変数を設定
$resourceGroupName = "rg-todomanagement-dev"
$location = "japaneast"
```

### 5.2 デプロイスクリプトを実行 （**所要時間**： 10 min~20min）

```powershell
# infra ディレクトリに移動
cd infra

# PowerShell スクリプトを実行
# Windows PowerShell では以下のコマンドで実行可能にする
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

# デプロイを実行
.\deploy.ps1 -ResourceGroupName $resourceGroupName -Location $location
```

> **注意**：Cloud Shell の PowerShell では実行ポリシーが既に設定されているため、そのまま実行できます。

### 5.3 デプロイ完了を確認

`deploy.ps1` が実行完了したら、出力した情報を記録してください。

```powershell
# 出力例：
==========================================
Infrastructure Details
==========================================
PostgreSQL Server: postgres-todomanagement-4eg3h7exlf4p6
PostgreSQL Hostname: postgres-todomanagement-4eg3h7exlf4p6.postgres.database.azure.com
Container Registry Login Server: acrtodomanagement4eg3h7exlf4p6.azurecr.io
Container Registry Name: acrtodomanagement4eg3h7exlf4p6
Container App Environment: cae-todomanagement-dev
Database Name: tododb
API_URL: https://todomanagement-api.internal.calmhill-4a670c14.japaneast.azurecontainerapps.io
WEB_URL: https://todomanagement-web.calmhill-4a670c14.japaneast.azurecontainerapps.io

Web App Authentication:
  AZURE_CLIENT_ID: xxxxxxxx-1338-4d64-a90c-19ae2cc9eff9
  AZURE_TENANT_ID: xxxxxxxx-b5a9-466f-xxxx-d14b03f7ae76
User Assigned Identity:
  USER_ASSIGNED_IDENTITY_CLIENT_ID: xxxxxxxx-239e-4e1b-b759-5e601fcc4d8a
  USER_ASSIGNED_IDENTITY_RESOURCE_ID: /subscriptions/xxxxxxxx-c1ec-xxxx-9ee7-22103870844b/resourceGroups/rg-todomanagement-xxxxxxxx/providers/Microsoft.ManagedIdentity/userAssignedIdentities/uai-todomanagement-dev
  USER_ASSIGNED_IDENTITY_NAME: uai-todomanagement-dev

==========================================
Next Steps:
  1. Configure GitHub Actions for CI/CD


==========================================
Deployment Completed!
==========================================
```

---

## Step 6️⃣ Service Principal と Azure 資格情報を作成（GitHub Actions 用）

> **権限メモ**:
> - このリポジトリでは `infra/main.bicep` 内で Microsoft Graph の `applications` リソースを作成します。
> - また、ACR に対する RBAC ロール割り当ても作成します。
> - そのため、Azure RBAC では `Owner`、または `Contributor` + `User Access Administrator` が必要です。
> - 加えて、Microsoft Entra ID ではアプリ登録を作成できる権限が必要です。テナント設定で一般ユーザーのアプリ登録作成が許可されていない場合は、`Application Administrator`、`Cloud Application Administrator`、または同等権限を使ってください。

### 6.1 Cloud Shell で Service Principal を作成

Cloud Shell で以下を実行：

```powershell
# 変数を設定
$subscriptionId = $(az account show --query id -o tsv)
$spName = "github-todomanagement-ci"

# Service Principal を作成
$sp = az ad sp create-for-rbac `
  --name $spName `
  --role "Owner" `
  --scopes "/subscriptions/$subscriptionId/resourceGroups/$resourceGroupName" `
  --json-auth | ConvertFrom-Json

# JSON 形式で出力（後で使用）
$sp | ConvertTo-Json
```

**出力をコピーしてメモしておきます**（次のステップで使用）：

```json
{
  "clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "subscriptionId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  ...
}
```

---

## Step 7️⃣ GitHub Secrets & Variables を設定

### 7.1 GitHub リポジトリの Settings を開く

1. GitHub リポジトリのページを開く
2. **Settings** → **Secrets and variables** → **Actions** をクリック
  ![1775016195315](images/DEPLOY_GUIDE-ja_JP/1775016195315.png)

### 7.2 Secret を追加

**New repository secret** をクリック

**Name**: `AZURE_CREDENTIALS`
**Value**: Step 6.1 でコピーした JSON 全体をペースト

```json
{
  "clientId": "...",
  "clientSecret": "...",
  "subscriptionId": "...",
  "tenantId": "...",
  ...
}
```

**Add secret** をクリック

![1775017571109](images/DEPLOY_GUIDE-ja_JP/1775017571109.png)

### 7.3 Variables を追加

**Settings** → **Secrets and variables** → **Actions** をクリック

![1775016195315](images/DEPLOY_GUIDE-ja_JP/1775016195315.png)

以下の Variables を追加します：


| Variable Name                        | Value                                                       | 説明                                                           |
| ------------------------------------ | ----------------------------------------------------------- | -------------------------------------------------------------- |
| `ACR_NAME`                           | `acrtodomanagementxxxxx`                                    | デプロイ出力から取得                                           |
| `RESOURCE_GROUP`                     | `rg-todomanagement-dev`                                     | デプロイ出力から取得                                           |
| `CONTAINER_APP_ENVIRONMENT`          | `cae-[projectName]-[environment]`                           | デプロイ出力の `Container App Environment` から取得。workflow の `--environment` に使用 |
| `POSTGRES_SERVER`                    | `postgres-todomanagement-xxxxx.postgres.database.azure.com` | デプロイ出力の`postgresqlHostname` から取得（FQDN 形式）       |
| `DATABASE_TYPE`                      | `postgresql`                                                | PostgreSQL を強制使用                                          |
| `POSTGRES_DB`                        | `tododb`                                                    | デフォルト                                                     |
| `POSTGRES_USER`                      | `uai-<project>-<env>`                                       | Microsoft Entra ID / UAI のプリンシパル名（`postgres` は不可） |
| `AZURE_CLIENT_ID`                    | `[Microsoft Entra ID App ID]`                               | Azure Portal から取得                                          |
| `AZURE_TENANT_ID`                    | `[租户 ID]`                                                 | Azure Portal から取得                                          |
| `AZURE_REDIRECT_URI`                 | `https://[web-app-url]`                                     | デプロイ後に取得                                               |
| `API_PROXY_TARGET`                   | `https://[api-app-url]`                                     | Web から internal API Container App へのリバースプロキシ先     |
| `USER_ASSIGNED_IDENTITY_CLIENT_ID`   | `[UAI Client ID]`                                           | デプロイ出力から取得                                           |
| `USER_ASSIGNED_IDENTITY_RESOURCE_ID` | `/subscriptions/.../userAssignedIdentities/...`             | デプロイ出力から取得。workflow の`--registry-identity` に使用  |

補足：

- Web Container App の実行時設定で必要なのは `API_PROXY_TARGET` のみです
- `CONTAINER_APP_ENVIRONMENT` は API / Web 両方の workflow の `az containerapp up --environment` で使用します
- `USER_ASSIGNED_IDENTITY_CLIENT_ID` は API Container App が PostgreSQL に Microsoft Entra 認証するために使います
- `USER_ASSIGNED_IDENTITY_RESOURCE_ID` は GitHub Actions のデプロイ時に使われ、アプリ実行時には不要です

**追加方法**：

1. **Variables** タブをクリック
2. **New repository variable** をクリック
3. **Name** に変数名を入力
4. **Value** に値を入力
5. **Add variable** をクリック

![1775016383501](images/DEPLOY_GUIDE-ja_JP/1775016383501.png)

---

## Step 8️⃣ GitHub Actions Workflow ファイルをコピー・有効化

### 8.1 Workflow テンプレートファイルをコピー

このテンプレートリポジトリでは、CI/CD Workflow ファイルが `.template` 後缀を持っています。
これは、テンプレートリポジトリ自身では Workflow が **自動実行されないようにするため**です。

**必要な操作**：

ローカルマシンで以下のコマンドを実行してください：

```bash
# Workflow ファイルをコピーして、テンプレートサフィックスを削除
cd ..
cp .github/workflows/build-deploy-web.yml.template .github/workflows/build-deploy-web.yml
cp .github/workflows/build-deploy-api.yml.template .github/workflows/build-deploy-api.yml

# コピーが成功したか確認
ls -la .github/workflows/

# 出力例：
# build-deploy-web.yml
# build-deploy-web.yml.template
# build-deploy-api.yml
# build-deploy-api.yml.template
```

**Windows PowerShell 版**：

```powershell
# Workflow ファイルをコピー
Copy-Item ".github/workflows/build-deploy-web.yml.template" ".github/workflows/build-deploy-web.yml"
Copy-Item ".github/workflows/build-deploy-api.yml.template" ".github/workflows/build-deploy-api.yml"

# コピー確認
Get-ChildItem ".github/workflows/"
```

### 8.2 なぜテンプレート化しているのか？

- ✅ **テンプレートリポジトリ上での誤実行防止**
  - テンプレートリポジトリ自体は Workflow を実行しない
  - ユーザーが明示的にコピーしてから実行される
- ✅ **ユーザーの意識的な操作**
  - ユーザーが自分で Workflow を有効化することで理解が深まる
- ✅ **カスタマイズの自由度**
  - ユーザーが必要に応じて Workflow を修正してからコミット可能

---

## Step 9️⃣ コードをコミット・プッシュ

### 9.1 設定ファイルを修正（ローカル）

ローカルマシンで以下を実行：

```bash
# ローカルで parameter.json を編集（必要に応じて）
# または .env ファイルが追加されていることを確認

# 変更を確認
git status

# 出力例：
# On branch main
# Changes not staged for commit:
#   modified: infra/parameters.json
```

### 9.2 コミット・プッシュ

```bash
# 変更をステージング（Workflow ファイルと設定ファイル含む）
git add .

# コミット
git commit -m "Enable GitHub Actions workflows and configure infrastructure parameters"

# メインブランチにプッシュ
git push origin main

# ユーザー名とPATを入力し、Pushを完了する

```

確認：

```bash
# リモート確認
git log --oneline
# 出力に最新のコミットが表示されます
```

---

## Step 🔟 GitHub Actions で自動デプロイ

### 🔟.1 Workflow の実行を確認

1. GitHub リポジトリのページから **Actions** タブをクリック
2. 以下のワークフローが表示されます：
   - `Build and Deploy API to ACR`
   - `Build and Deploy Web to ACR`

### 🔟.2 Workflow の自動実行を待つ

**トリガー条件**：

- `main` ブランチへの `push` 時に自動実行
- `src/api/` または `.github/workflows/build-deploy-api.yml` が変更された場合 → API ワークフロー実行
- `src/web/` または `.github/workflows/build-deploy-web.yml` が変更された場合 → Web ワークフロー実行

### 🔟.3 実行状況を確認

```
Actions ページで以下を確認：

✅ チェックマーク
├─ Checkout code
├─ Log in to Azure
├─ Build and push image to ACR
└─ Deploy to Container App
```

**所要時間**：API & Web で各 5～10 分

### 🔟.4 Workflow が失敗した場合

❌ エラーが表示された場合：

1. **Workflow をクリック**して詳細を確認
2. **失敗したステップ** をクリック
3. **エラーログ** を確認
4. よくあるエラー：
   - `AZURE_CREDENTIALS` が設定されていない
   - `RESOURCE_GROUP` Variable が間違っている
   - Container App Environment 名が一致していない

---

## Step 1️⃣1️⃣ Web アプリケーションにアクセス

### 11.1 Container App URL を取得

Cloud Shell で実行：

```powershell
# Web Container App の URL を取得
az containerapp show `
  -n todomanagement-web `
  -g $resourceGroupName `
  --query "properties.configuration.ingress.fqdn" `
  -o tsv

# 出力例：
# todomanagement-web.abc123def.japaneast.azurecontainerapps.io
```

完全な URL：

```
https://todomanagement-web.abc123def.japaneast.azurecontainerapps.io
```

### 11.2 ブラウザでアクセス

1. 上記 URL をブラウザのアドレスバーにコピー・ペースト
2. **Enter** キーを押す
3. Todo Management アプリケーションが表示されます ✅

### 11.3 機能を確認

- **🔐 Login ボタン**をクリック
- Microsoft Entra ID で認証
- Todo リストが表示される
- New Todo の作成、編集、削除が可能

**楽しいデプロイを！🚀**

作成日：2026-04-02
バージョン：1.0
