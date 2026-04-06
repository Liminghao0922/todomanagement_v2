# Infrastructure Architecture Guide

[English](ARCHITECTURE_GUIDE.md) | [简体中文](ARCHITECTURE_GUIDE-zh_CN.md) | [日本語](ARCHITECTURE_GUIDE-ja_JP.md)

## システム概要

このインフラは、**プライベート・セキュア・ID ベース**の構成で、ハードコードされたシークレットを排除することを目的としています。

![Architecture](../images/01.Architecture.png)

## 主要ポイント
- ワークロードは Azure のプライベートネットワーク上で動作
- ACR と PostgreSQL は Private Endpoint / Private DNS を利用
- Container Apps はユーザー割り当てマネージド ID (UAI) で ACR / PostgreSQL にアクセス
- CI/CD は GitHub Actions でビルドとローリング更新を実施

## 主要コンポーネント
- `todomanagement-api`: Todo、プロジェクト、認証関連 API を提供する FastAPI バックエンド
- `todomanagement-web`: 同一オリジンの `/api` を利用する Vue 3 フロントエンド
- PostgreSQL Flexible Server: 本番データを保持し、Microsoft Entra ID 認証を使用
- Azure Container Registry: API / Web イメージを格納
- User Assigned Identity: イメージ pull と DB 接続のために利用

## 認証フロー
- API コンテナは起動時に UAI で PostgreSQL 用トークンを取得します
- Web コンテナはビルド時に Entra 設定を埋め込み、実行時には `API_PROXY_TARGET` を使用します
- GitHub Actions は `AZURE_CREDENTIALS` を使って Azure にログインし、テンプレート workflow から Container Apps を更新します

## リクエストデータフロー
1. ブラウザーが Web Container App にアクセスします
2. フロントエンドは同一オリジンの `/api` を呼び出します
3. Web Container App は `/api` を internal API Container App にプロキシします
4. API Container App は UAI で PostgreSQL トークンを取得し、クエリを実行します
5. 応答は HTTPS でブラウザーに返されます

## セキュリティモデル
- DB パスワードのハードコードを禁止
- Microsoft Entra ID とトークンベース認証を採用
- 最小権限の原則 (例: ACR は AcrPull)
- RBAC と監査ログによりアクセスを追跡可能

## RBAC 概要
- UAI には ACR のイメージ pull に必要な権限を付与します
- PostgreSQL では対応する Entra プリンシパルに最小限の DB 権限を付与します
- GitHub Actions 用 Service Principal には対象リソースグループへのデプロイ権限が必要です

## 推奨読書順
1. `README-ja_JP.md`
2. `handson/DEPLOY_GUIDE-ja_JP.md`
3. `infra/README.md`
4. `.github/workflows/*.yml.template`

## 注記
この文書は日本語版の要約です。詳細は英語の既定文書 `docs/ARCHITECTURE_GUIDE.md` を参照してください。
