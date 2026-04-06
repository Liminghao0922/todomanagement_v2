# Todo Management

[English](README.md) | [简体中文](README-zh_CN.md) | [日本語](README-ja_JP.md)

FastAPI + PostgreSQL バックエンドと Vue 3 + Vite フロントエンドで構成されたフルスタック サンプルです。Azure Container Apps、ACR、Microsoft Entra ID、ユーザー割り当てマネージド ID (UAI)、プライベート ネットワークを利用し、平文シークレットを持たない構成を実現します。

## システム概要

このインフラは、**プライベート・セキュア・ID ベース**の設計を採用し、ハードコードされたシークレットを排除しています。

![Architecture](images/01.Architecture.png)

## 構成ハイライト
- コンテナ: `todomanagement-api` (FastAPI) と `todomanagement-web` (Vite/Vue)
- インフラ: VNet サブネット、PostgreSQL Flexible Server (Entra ID 認証)、ACR Private Endpoint、Container Apps Environment、Log Analytics、UAI
- CI/CD: GitHub Actions でイメージを ACR に push し、`az containerapp up` でローリング更新
- 参考: `docs/ARCHITECTURE_GUIDE-ja_JP.md`

## リポジトリ構成
- `src/api`: FastAPI サービス (ローカル SQLite、運用 PostgreSQL)
- `src/web`: Vue 3 SPA (MSAL ログイン、Todo/検索機能)
- `infra`: Bicep テンプレート、デプロイスクリプト、パラメータ
- `docs`: アーキテクチャおよび補足ドキュメント

## ローカル実行
前提: Python 3.11、pip、Node 18+、npm

API
```powershell
cd src\api
copy .env.local.example .env.local
python -m venv .venv; .\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
# ヘルスチェック: http://localhost:8000/health
```

ローカル PostgreSQL を利用する場合は、`.env.local` に `DATABASE_TYPE=postgresql` と `POSTGRES_*` を設定してください。

Web
```powershell
cd src\web
copy .env.example .env.local
npm install
npm run dev  # http://localhost:5173
```

ローカル開発時、Vite は `/api` をローカルのバックエンドへ自動プロキシします。本番ビルドは `npm run build` で実行し、成果物は `dist/` に出力されます。Azure では、Web Container App の `API_PROXY_TARGET` を使って同一オリジンの `/api` を internal API Container App に転送します。

## デプロイ
標準的なデプロイ手順は次のとおりです。
1. `infra/deploy.ps1` でインフラをデプロイする
2. ACR、PostgreSQL ホスト名、Container Apps Environment、UAI ID などの出力を記録する
3. `.github/workflows/*.yml.template` から workflow ファイルを初期化する
4. GitHub Secret `AZURE_CREDENTIALS` と必要な Variables を設定する
5. GitHub Actions を実行し、API と Web アプリを検証する

詳細は `handson/DEPLOY_GUIDE-ja_JP.md` を参照してください。

## 関連ドキュメント
- `docs/ARCHITECTURE_GUIDE-ja_JP.md`
- `handson/DEPLOY_GUIDE-ja_JP.md`
- `infra/README.md`
