# アーキテクチャ ガイド v3 - Azure Functions + Cosmos DB + Static Web Apps

[English](ARCHITECTURE_GUIDE.md) | [简体中文](ARCHITECTURE_GUIDE-zh_CN.md) | [日本語](ARCHITECTURE_GUIDE-ja_JP.md)

## システム概要

v3 アーキテクチャは**クラウドネイティブ、サーバーレス、ID ベース**の設計を採用しており、以下を統合します：

- **Azure Functions** - バックエンド API と定時ジョブ
- **Azure Cosmos DB** - NoSQL コンテナ + Gremlin グラフ
- **Azure Static Web Apps** - Vue フロントエンド
- **Azure OpenAI** - ベクトル埋め込みとチャットモデル
- **Azure AI Foundry** - ビルトインツール (Graph + Cosmos) とカスタムツール対応
- **Microsoft Entra ID** - 全サービス横断の認証・認可

### 上位レベル アーキテクチャ

```
┌──────────────────────────────────────────────────────────────┐
│               Azure Cloud Environment                        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  SPA (Vue 3 + Vite)
│  ↓ MSAL Entra ID 認証
│
│  ┌────────────────────────────────────────────────────┐   │
│  │ Azure Static Web Apps                             │   │
│  │ - フロントエンド配置                               │   │
│  │ - `/api` proxy → Function App                     │   │
│  └────────────────┬─────────────────────────────────┘   │
│                   ↓
│  ┌────────────────────────────────────────────────────┐   │
│  │ Azure Functions (Python 3.11)                     │   │
│  │ - GET/POST/PATCH/DELETE /todos                   │   │
│  │ - POST /chat (Foundry 代理)                       │   │
│  │ - POST /tools/extract-action-items (カスタム)     │   │
│  │ - Timer: 0 0 */6 * * * (カレンダー スキャン)       │   │
│  └────────────────┬─────────────────────────────────┘   │
│                   ↓
│  ┌────────────────────────────────────────────────────┐   │
│  │ Azure Cosmos DB                                   │   │
│  │ - NoSQL: todos, owners, projects コンテナ         │   │
│  │ - Gremlin: todo-graph (関係グラフ)               │   │
│  │ - Vector: embedding フィールド                   │   │
│  │ - Serverless 料金体系                           │   │
│  └────────────────────────────────────────────────────┘   │
│
│  ┌────────────────────────────────────────────────────┐   │
│  │ Azure OpenAI Service                              │   │
│  │ - gpt-4o-mini (チャット + 抽出)                  │   │
│  │ - text-embedding-3-small (ベクトル)              │   │
│  └────────────────────────────────────────────────────┘   │
│
│  ┌────────────────────────────────────────────────────┐   │
│  │ Azure AI Foundry                                  │   │
│  │ - Web UI Agent (gpt-4o-mini 駆動)                │   │
│  │ - ビルトイン: MS Graph + Cosmos クエリ             │   │
│  │ - カスタムツール: /api/tools/extract-action-items │   │
│  └────────────────────────────────────────────────────┘   │
│
└──────────────────────────────────────────────────────────────┘
```

## データフロー

### 1. SPA → Functions API

```
ユーザー
  ↓ MSAL 認証 (Entra ID)
  ↓
Vue 3 フロントエンド
  ├─ GET /api/health
  ├─ GET /api/todos
  ├─ POST /api/todos (作成)
  ├─ PATCH /api/todos/{id} (更新)
  ├─ DELETE /api/todos/{id} (削除)
  ├─ POST /api/chat (Foundry チャット)
  └─ POST /api/tools/extract-action-items
       ↓
  Azure Functions
       ↓
  Cosmos DB / OpenAI / Graph API
```

### 2. Functions → Cosmos NoSQL

```
POST /api/todos を受け取る
  ↓
1. OpenAI で埋め込みを生成
   text-embedding-3-small(title + description)
2. Todo ドキュメント作成
   { id, owner_id, title, description, embedding: [...], ... }
3. Cosmos NoSQL の "todos" コンテナに upsert
4. Gremlin グラフに同期
   - 頂点作成 (todo ノード)
   - エッジ作成 (BLOCKED_BY, PRECEDES, etc.)
```

### 3. 定時タスク: カレンダー スキャン

```
Timer: 6 時間ごと
  ↓
1. すべてのオーナー取得 (Cosmos から)
2. 各オーナーについて:
   - Graph API 認証 (client credentials)
   - calendarView API コール
   - 出席者の会議抽出
   - OpenAI で行動item 抽出
   - 重複排除後、Cosmos に Todo 作成
   - Gremlin グラフ同期
```

### 4. Foundry Agent 連携

```
ユーザー: Foundry UI にクエリ入力
  ↓
Foundry Agent (gpt-4o-mini)
  ├─ ビルトイン MS Graph ツール
  │  └─ カレンダー API → イベント取得
  ├─ ビルトイン Cosmos ツール
  │  ├─ SQL クエリ → NoSQL データ
  │  └─ Gremlin 検索 → 関連 todos
  └─ カスタムツール
     └─ /api/tools/extract-action-items
        → 会議テキスト → 行動items
  ↓
ツール結果チェーン → 自然言語応答生成
  ↓
Foundry UI に表示
```

## Entra ID と認証

### Web アプリ (SPA)

- プラットフォーム: SPA (MSAL ブラウザ)
- リダイレクト URI: `https://[swa].azurestaticapps.net/`
- スコープ: `User.Read`, `Calendars.Read` (委任)

### Functions (マネージド ID)

- タイプ: システム割り当て
- Cosmos、OpenAI、Graph API 認証に使用
- シークレット不要 (Entra ID トークン自動取得)

### Graph API (Service Principal)

- タイプ: アプリ登録 (client secret)
- スコープ: `Calendars.Read` (アプリケーション)
- カレンダー スキャン ジョブで使用

## セキュリティ

- **シークレット なし**: RuntimeEntra ID/Key Vault 経由で解決
- **Cosmos パーティション化**: `/owner_id` でデータ分離
- **HTTPS 全下行**: 通信完全暗号化
- **グラフで関係を表現**: edges が todo の論理的な関連性を定義

詳細は [DEPLOY_GUIDE-ja_JP.md](../handson/DEPLOY_GUIDE-ja_JP.md) を参照してください。
