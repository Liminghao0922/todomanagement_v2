# 講師向け準備ガイド（Foundry Focus・初級者向け）

[English](INSTRUCTOR_PREP_GUIDE_FOUNDRY_FOCUS.md) | [简体中文](INSTRUCTOR_PREP_GUIDE_FOUNDRY_FOCUS-zh_CN.md) | [日本語](INSTRUCTOR_PREP_GUIDE_FOUNDRY_FOCUS-ja_JP.md)

[受講者ガイド](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS-ja_JP.md)

この版は初級者向けです。講師が事前に可能な限り準備し、受講者は Foundry と Cosmos DB ツール操作に集中します。

## 1. 設計方針

- 受講者の作業は Portal/UI 中心にする。
- 受講者の Cloud Shell や長いコマンド操作を避ける。
- 共有リソースは講師が事前に構築する。
- インフラ障害対応は講師が担当する。

## 2. 既存ラボからのスコープ変更

- 講師担当:
  - リソース展開
  - コンテナーイメージのビルド/デプロイ
  - RBAC と ID 設定
  - 接続確認とスモークテスト
- 受講者担当:
  - Foundry Agent 操作
  - Cosmos DB へのツール呼び出し
  - プロンプト/指示の調整

## 3. 講師の事前準備

- クラス開始前に環境一式を展開する。
- URL、権限、ロールを検証する。
- Cosmos DB にサンプルデータを投入する。
- 受講者アカウントで Playground 利用を確認する。

推奨権限（必要な場合のみ）:

- 受講者の作業 RG に対する Owner（最低でも Contributor+）
- アプリ登録を残す場合は Entra ID の Application Developer

Foundry 集中型にする場合、受講者のインフラ作成権限は不要です。

## 4. デプロイ方式

### 方式 A（推奨）: 講師が共有環境を事前構築

既存の講師ガイドの共有環境方式を利用し、受講者は準備済みリソースを使います。

### 方式 B: 講師が azd で一括展開

講師が事前に次を実行します。

```powershell
azd up
```

`azd up` は、個別に実行できる 2 つのフェーズを順番に実行します。`azd provision` はインフラストラクチャ、ID、RBAC、Entra、Foundry connection を構成し、`azd deploy` は MCP イメージ、Agent、Function、Static Web App をデプロイして正常性を確認します。

命名ルール（現行の Bicep テンプレートに統一）:

- `<suffix>` = `uniqueString(resourceGroup().id)`。
- Azure AI Services: `aifoundry-<projectName>-<suffix>`
- Cosmos SQL アカウント: `cossql<projectName><suffix>`
- Cosmos Gremlin アカウント: `cosgr<projectName><suffix>`
- Storage アカウント: `st<projectNameNoDashFirst8><suffix>`（`projectName` を小文字化し、`-`/`_` を除去して先頭 8 文字を使用）
- App Service Plan: `asp-<projectName>-<env>`
- Function App 名: `func-<projectName>-<env>-<suffix>`（preview のリソース種別表示は `Web App`）
- Static Web App: `swa-<projectName>-<suffix>`
- Container Registry: `acr<projectNameFirst10><shortSuffix>`
- Container App: `mcp-<projectNameFirst12>-<shortSuffix>`
- Container Apps 環境: `cae-<projectNameFirst12>-<shortSuffix>`
- Log Analytics ワークスペース: `log-<projectNameFirst12>-mcp-<shortSuffix>`

現在のサンプル環境（`projectName=todomanagement`, `environment=todomangementv2`）で `azd provision --preview` を実行すると、次のような `Create` が表示されます。

```text
Create : Container App                      : mcp-todomanageme-oit3m2
Create : Container Apps Environment         : cae-todomanageme-oit3m2
Create : Azure AI Services                  : aifoundry-todomanagement-oit3m2mzmum7y
Create : Azure AI Services Model Deployment : gpt-5.4-mini
Create : Azure AI Services Model Deployment : text-embedding-3-small
Create : Foundry project                    : proj-todomanagement
Create : Container Registry                 : acrtodomanageoit3m2
Create : Azure Cosmos DB                    : cosgrtodomanagementoit3m2mzmum7y
Create : Azure Cosmos DB                    : cossqltodomanagementoit3m2mzmum7y
Create : Log Analytics workspace            : log-todomanageme-mcp-oit3m2
Create : Storage account                    : sttodomanaoit3m2mzmum7y
Create : App Service plan                   : asp-todomanagement-todomangementv2
Create : Web App                            : func-todomanagement-todomangementv2-oit3m2mzmum7y
Create : Static Web App                     : swa-todomanagement-oit3m2mzmum7y
```

注意:

- 受講者作業ではありません。
- 出力値（URL/ID）を配布資料にまとめます。
- 事前検証後は環境を固定します。

## 5. 事前検証チェックリスト

- Todo Web アプリが開けてサインインできる。
- Function health が healthy を返す。
- Cosmos DB にサンプルデータがある。
- Foundry のモデルが配備済みである。
- Agent が Cosmos ツールを呼び出せる。
- 任意ツール（例: Work IQ Calendar）も検証済みである。
- 受講者が CLI なしで完走できる。

## 6. 受講者に配布する情報

- Todo アプリ URL
- Foundry プロジェクト URL
- Agent 名とバージョン
- 推奨テストプロンプト
- 期待される出力例

初級者向けでは、受講者にビルド/デプロイコマンドを実行させません。

## 7. 推奨進行（60-90 分）

1. 10 分: 全体像説明
2. 15 分: Foundry UI 説明（モデル、ツール、トレース）
3. 25 分: Cosmos ツール呼び出し演習
4. 15 分: プロンプト/指示の調整
5. 10 分: まとめと Q and A

## 8. 当日のフォールバック

インフラ問題が発生した場合:

- 講師が検証済みの予備環境へ切り替える。
- 受講者は Foundry 操作のみ継続する。
- デプロイ/デバッグ工程はスキップする。
