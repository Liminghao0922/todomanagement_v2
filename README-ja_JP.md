# Todo Management

[English](README.md) | [简体中文](README-zh_CN.md) | [日本語](README-ja_JP.md)

Todo Management のフルスタック サンプルです。現在の v3 アーキテクチャは、Azure Functions + Azure Cosmos DB (NoSQL + Gremlin Graph) をバックエンド、Vue 3 + Vite を Azure Static Web Apps に配置し、Azure AI Foundry と連携します。

## システム概要

このインフラは、**プライベート・セキュア・ID ベース**を前提に設計され、ハードコードされたシークレットを避けます。

![Architecture](images/01.Architecture.png)

## 構成ハイライト
- バックエンド: Azure Functions (Python) で Todo API、カスタムツール API、Timer ジョブを提供
- データ: Azure Cosmos DB Serverless (`todos`/`owners`/`projects` コンテナ + `todo-graph` Gremlin グラフ)
- フロントエンド: Vue 3 + Vite を Azure Static Web Apps にデプロイ
- AI: Azure OpenAI と Azure AI Foundry (Web UI) を利用
- 認証: Microsoft Entra ID アプリ登録 (`User.Read`, `Calendars.Read`)
- 参考: `docs/ARCHITECTURE_GUIDE-ja_JP.md`

## リポジトリ構成
- `src/api`: Azure Functions バックエンド
- `src/web`: Vue 3 SPA (MSAL ログイン、Todo/検索機能)
- `infra`: Bicep テンプレート、デプロイスクリプト、パラメータ
- `docs`: アーキテクチャおよび補足ドキュメント

## ローカル実行
前提: Python 3.11、Azure Functions Core Tools、Node 18+、npm

API (Azure Functions)
```powershell
cd src\api
copy local.settings.example.json local.settings.json
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
func start
# ヘルスチェック: http://localhost:7071/api/health
```

ローカル実行時は `local.settings.json` に Cosmos/OpenAI/Graph/Foundry 設定を入力してください。

Web
```powershell
cd src\web
copy .env.example .env.local
npm install
npm run dev  # http://localhost:5173
```

ローカル開発時、Vite は `/api` をローカル Functions にプロキシします。Azure 配布向けには `npm run build` を実行し、成果物は `dist/` に出力されます。

## デプロイ
標準的なデプロイ手順:
1. `infra/deploy.ps1` でインフラをデプロイ
2. Function URL、SWA URL、Cosmos Endpoint、Entra App ID、Foundry リソース出力を控える
3. Foundry Web UI で Agent を作成し、Built-in Graph/Cosmos ツールと `/api/tools/estimate-hours` を接続
4. Function コードと Web 静的アセットをデプロイ
5. Todo CRUD、AI 抽出、Timer スキャンを検証

詳細は `handson/DEPLOY_GUIDE-ja_JP.md` を参照してください。

## 関連ドキュメント
- `docs/ARCHITECTURE_GUIDE-ja_JP.md`
- `handson/DEPLOY_GUIDE-ja_JP.md`
- `infra/README.md`
