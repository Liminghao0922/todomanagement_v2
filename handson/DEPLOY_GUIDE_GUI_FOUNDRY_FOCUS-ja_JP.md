# Todo Management v2 ハンズオン（Foundry Focus・初級者向け）

[English](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS.md) | [简体中文](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS-zh_CN.md) | [日本語](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS-ja_JP.md)

この版は Foundry 操作に集中する構成です。インフラは講師が事前準備します。

想定時間: 60-90 分

## 1. 受講前に講師から受け取るもの

- Todo アプリ URL
- Foundry プロジェクト URL
- Agent 名とバージョン
- テスト用アカウントとサインイン方法
- 期待される出力例

この版では受講者の Cloud Shell 操作は不要です。

## 2. 学習目標

- Agent instructions が応答に与える影響を理解する。
- Foundry Tools で Cosmos DB データを操作する。
- Trace とツール呼び出しを読み解く。
- プロンプト/指示調整で応答品質を改善する。

## 3. 手順

### 3.1 サインインとアプリ確認

1. Todo アプリ URL を開く。
2. 配布アカウントでサインインする。
3. `Todos` と `Projects` ページが開くことを確認する。
4. 1 つのプロジェクトを開き、グラフ表示を確認する。

### 3.2 Foundry Agent Playground を開く

1. 配布された Foundry URL を開く。
2. 指定された Agent を開く。
3. 次のツールが接続済みであることを確認する。
   - Azure Cosmos DB
   - （任意）Work IQ Calendar

### 3.3 Cosmos ツール呼び出し演習

以下を順に実行します。

1. `List all databases in my Cosmos DB account.`
2. `List containers in database todo-db.`
3. `Find todos that mention MVP or validation.`
4. `Show high-priority tasks for Current Project.`

期待結果:

- Agent がツール呼び出しを実行する。
- Cosmos DB 由来のデータが返る。

### 3.4 Trace の確認

1. 対象会話の `Traces` を開く。
2. ツール呼び出しの引数と結果を確認する。
3. 呼び出し理由を説明する。
4. 応答が期待どおりか確認する。

### 3.5 プロンプト/指示の調整

次のいずれかを試して比較します。

- 出力形式（長さ/構造）を制約する。
- ツール根拠の明示を要求する。
- 実行可能な優先順位提案を要求する。

同じ質問を再実行し、品質差分を確認します。

## 4. 完了条件

- Cosmos ツール呼び出しを意図的に実行できる。
- Trace 1 件を最後まで説明できる。
- プロンプト変更で応答品質を改善できる。

## 5. 任意チャレンジ

Work IQ Calendar が有効な場合:

- 直近会議の要約を依頼する。
- 会議予定を考慮したタスク優先順位を依頼する。

## 6. トラブル時の対応（受講者向け）

- サインイン失敗: 講師へ連絡（アカウント/テナント設定）。
- ツール失敗: Trace 確認を先に進め、復旧は講師が対応。
- 結果が空: 質問を具体化し、期間/条件を明示する。
