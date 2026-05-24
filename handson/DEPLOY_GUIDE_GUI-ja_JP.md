# Todo Management v2 デプロイ ガイド（Azure Portal 手順）

[English](DEPLOY_GUIDE_GUI.md) | [简体中文](DEPLOY_GUIDE_GUI-zh_CN.md) | [日本語](DEPLOY_GUIDE_GUI-ja_JP.md)

このガイドは、初学者向けの手順を採用しています。すべての Azure リソースは Azure Portal UI から作成し、コード操作が必要な箇所はコピー＆ペーストできるブロックに最小化しています。IaC ベースの手順を使う場合は、[DEPLOY_GUIDE.md](DEPLOY_GUIDE.md) を参照してください。

想定所要時間: 90〜120 分。

---

## このガイドで使う用語

| 用語                           | このハンズオンにおける意味                                                                                                               |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **リソース グループ**    | すべての v2 リソースを格納する論理コンテナー（既定名は `rg-todomanagementv2-dev`）。                                                   |
| **Function App**         | `src/api/` をホストする Linux Flex Consumption プラン上の Azure Functions。                                                            |
| **Static Web App (SWA)** | `src/web/` からビルドした Vue 3 SPA をホスト。                                                                                         |
| **Cosmos DB Serverless** | SQL コンテナー（`todos` / `owners` / `projects` / `conversations`）と Gremlin グラフ（`todo-graph-db`/`todo-graph`）を保存。 |
| **Microsoft Foundry**    | `gpt-5.4-mini` と `text-embedding-3-small` を提供。                                                                                  |
| **アプリ登録**           | SPA サインイン用の Entra ID アプリケーションと、必要に応じてサーバーから Foundry へアクセスするための同意設定。                          |
| **マネージド ID**        | Cosmos Gremlin と Azure OpenAI の AAD トークン取得に使う、Function App のシステム割り当て ID。                                           |

---

## フェーズ 1. Azure Portal からインフラを作成する

### 1.1 リソース グループを作成する

1. `https://portal.azure.com` を開いてサインインします。
2. **リソース グループ** を検索し、**+ 作成** を選択します。
3. Subscription には使用するサブスクリプションを選択し、**リソース グループ名** に `rg-todomanagementv2-dev`、**リージョン** に `Japan East`（または Cosmos + Foundry + Functions Linux + SWA をすべてサポートする任意のリージョン）を指定します。
4. **レビューと作成** → **作成** を選択します。

📖 参考: [https://learn.microsoft.com/azure/azure-resource-manager/management/manage-resource-groups-portal](https://learn.microsoft.com/azure/azure-resource-manager/management/manage-resource-groups-portal)

![リソース グループの作成](image/DEPLOY_GUIDE_GUI/01-create-rg.png)

---

### 1.2 NoSQL 用の Cosmos DB アカウントを作成する

1. **Azure Cosmos DB** を検索し、**+ 作成** を選択します。
2. API は **Azure Cosmos DB for NoSQL** を選択します。
3. **Basics** では次を設定します。
   - **ワークロードの種類**: `Learning`
   - **リソース グループ**: `rg-todomanagementv2-dev`
   - **アカウント名**: `cosmos-todomanagement-<unique>`（小文字英字と数字のみ）
   - **可用性ゾーン**: `無効`
   - **場所**: リソース グループと同じ
   - **容量モード**: **Serverless**
4. **グローバル配布** では次を設定します。

   - **Geo 冗長性**: `無効`
   - **マルチリージョン書き込み**: `無効`
5. **ネットワーク** では次を設定します。

   - **ネットワーク接続**: `すべてのネットワーク`。必要に応じて後で制限します。
6. **バックアップ ポリシー** は既定値のままで問題ありません。
7. **セキュリティ** では次を設定します。

   - **キーベースの認証**: `無効`。認証には Entra ID を使用します。
   - **データ暗号化**: `サービス マネージド キー`
8. **レビュー + 作成** → **作成** を選択します。
   ![Cosmos DB アカウントの作成](image/DEPLOY_GUIDE_GUI/02-create-cosmos.png)
   デプロイ完了後:
9. アカウントを開き、**データ エクスプローラー** → **New Database** を選択して ID に `todo-db` を入力します。その後、次の 4 つのコンテナーを作成します。

   | Container         | Partition key       |
   | ----------------- | ------------------- |
   | `todos`           | `/owner_id`         |
   | `owners`          | `/id`               |
   | `projects`        | `/owner_id`         |
   | `conversations`   | `/owner_id`         |

![Cosmos コンテナー](image/DEPLOY_GUIDE_GUI/03-cosmos-containers.png)
📖 参考: [https://learn.microsoft.com/ja-jp/azure/cosmos-db/quickstart-portal](https://learn.microsoft.com/ja-jp/azure/cosmos-db/quickstart-portal)

---

### 1.3 Gremlin API 用の Azure Cosmos DB アカウントを作成する

1. **Azure Cosmos DB** を検索し、**+ 作成** を選択します。
2. API は **Azure Cosmos DB for Apache Gremlin** を選択します。
   ![Azure Cosmos DB for Apache Gremlin の選択](image/DEPLOY_GUIDE_GUI/04-cosmosgre-select-api.png)
3. **Basics** では次を設定します。
   - **ワークロードの種類**: `Learning`
   - **リソース グループ**: `rg-todomanagementv2-dev`
   - **アカウント名**: `cosmos-todomanagement-<unique>`（小文字英字と数字のみ）
   - **可用性ゾーン**: `無効`
   - **場所**: リソース グループと同じ
   - **容量モード**: **Serverless**
4. **グローバル配布** では次を設定します。

   - **Geo 冗長性**: `無効`
   - **マルチリージョン書き込み**: `無効`
5. **ネットワーク** では次を設定します。

   - **ネットワーク接続**: `すべてのネットワーク`。必要に応じて後で制限します。
6. **バックアップ ポリシー** は既定値のままで問題ありません。
7. **セキュリティ** では次を設定します。
   - **データ暗号化**: `サービス マネージド キー`
8. **レビュー + 作成** → **作成** を選択します。
   ![Gremlin Cosmos DB アカウントの作成](image/DEPLOY_GUIDE_GUI/05-create-cosmosgre.png)
   デプロイ完了後:
9. アカウントを開き、**データ エクスプローラー** → **New Graph** を選択して次を設定します。

   - **Database id**: `todo-graph-db`
   - **Graph id**: `todo-graph`
   - **Partition key**: `/owner_id`
     ![グラフの作成](image/DEPLOY_GUIDE_GUI/06-create-cosmosgre-graph.png)

---

### 1.4 Foundry リソースを作成し、モデルをデプロイする

1. **Microsoft Foundry** → **Foundry** → **+ 作成** を選択します。
2. **基本情報** で次を設定します。
   - **リソース グループ**: `rg-todomanagementv2-dev`
   - **名前**: `foundry-todomanagement-<unique>`（小文字英字と数字のみ）
   - **リージョン**: リソース グループと同じ
3. **確認と作成** → **作成** を選択します。

![Foundry リソースの作成](image/DEPLOY_GUIDE_GUI/07-create-foundry-resource.png)
デプロイ完了後:
4. Foundry リソースを開き、**Foundry ポータルに移動** を選択して `Project endpoint` をコピーし、控えておきます。
5. **ビルド** → **モデル** → **基本モデルをデプロイする** を開き、`text-embedding-3-small` を検索します。
6. `text-embedding-3-small` を選択し、**デプロイ** → **既定の設定** を選びます。
![text-embedding-3-small のデプロイ](image/DEPLOY_GUIDE_GUI/08-deploy-embedding-model.png)
7. **ビルド** → **モデル** → **基本モデルをデプロイする** を開き、`gpt-5.4-mini` を検索します。
8. `gpt-5.4-mini` を選択し、**デプロイ** → **既定の設定** を選びます。
![gpt-5.4-mini のデプロイ](image/DEPLOY_GUIDE_GUI/09-deploy-gpt-model.png)

---

### 1.5 Function App と Storage を作成する

1. **関数アプリ** を検索し、**+ 作成** を選択します。
2. `フレックス従量課金` を選択します。
3. **基本** で次を設定します。
   - **リソース グループ**: `rg-todomanagementv2-dev`
   - **関数アプリ名**: `func-todomanagement` とし、**Secure unique default hostname** を有効にします。
   - **リージョン**: リソース グループと同じ
   - **ランタイム スタック**: `Python` 3.11
   - **インスタンス サイズ**: `2048 MB`
   - **ゾーン冗長**: `無効`
4. **Storage** では、新しいストレージ アカウント `satodomanagement<unique>`（小文字 + 数字、最大 24 文字）を作成します。
5. **Azure OpenAI** は既定値のままにします。
6. **ネットワーク** は パブリック アクセスを有効にします。
7. **監視** では Application Insights を有効化し、必要に応じて新しいコンポーネントを作成します。
8. **Durable Functions** は既定値のままにします。
9. **デプロイ** は既定値のままにします。
10. **認証** では Authentication type を `マネージド ID` に変更します。
    ![Function 認証の設定](image/DEPLOY_GUIDE_GUI/10-set-function-authentication.png)
11. **確認および作成** → **作成** を選択します。
    ![Function App 作成完了](image/DEPLOY_GUIDE_GUI/11-create-function-app.png)
12. デプロイ完了後、Function App を開き、**設定** → **ID** → **ユーザー割り当て済み** → **func-todomanagement-uami** に進み、**クライアント ID** と **オブジェクト (プリンシパル) ID** をコピーして保存します。
    ![Function UAMI client id のコピー](image/DEPLOY_GUIDE_GUI/copy-function-uami-client-id.png)

📖 参考: [https://learn.microsoft.com/azure/azure-functions/functions-create-function-app-portal](https://learn.microsoft.com/azure/azure-functions/functions-create-function-app-portal)

---

### 1.6 Static Web App を作成する

1. **静的 Web アプリ** を検索し、**+ 作成** を選択します。
2. **基本** で次を設定します。
   - **リソース グループ**: `rg-todomanagementv2-dev`
   - **名前**: `stapp-todomanagement-<unique>`
   - **プランの種類**: `Standard`
   - **デプロイの詳細**: **Other** を選択
3. **デプロイ構成** では **デプロイ トークン** を選択します。
4. **詳細設定** では、**Azure Functions API とステージング環境のリージョン** に `East Asia` を選択します。
5. **確認および作成** → **作成** を選択します。
   ![Static Web App の作成](image/DEPLOY_GUIDE_GUI/12-create-swa.png)
6. デプロイ完了後、SWA を開いて次の情報をコピーし、フェーズ 4 のために保存します。
   - **デプロイ トークンの管理**
   - **URL**

📖 参考: [https://learn.microsoft.com/azure/static-web-apps/getting-started](https://learn.microsoft.com/azure/static-web-apps/getting-started)

---

## フェーズ 2. ID と権限を構成する

### 2.1 Microsoft Entra ID に SPA を登録する

1. **Microsoft Entra ID** → **アプリの登録** → **+ 新規登録** を開きます。
2. **名前** に `todomanagementv2-spa` を入力します。
3. **サポートされているアカウントの種類** は `シングル テナントのみ` を選択します。
4. **リダイレクト URI** は `シングルページ アプリケーション (SPA)` → `https://<swa>.azurestaticapps.net/` を指定します。
5. **登録** を選択します。

作成後:
6. 任意。ローカル実行も行う場合は、**Authentication** → **+ リダイレクト URI の追加** に `http://localhost:5173/` を追加して保存します。
7. **概要** ページから次をコピーします。

- **アプリケーション (クライアント) ID** → `CLIENT_ID` として保存
- **ディレクトリ (テナント) ID** → `TENANT_ID` として保存

📖 参考: [https://learn.microsoft.com/entra/identity-platform/quickstart-register-app](https://learn.microsoft.com/entra/identity-platform/quickstart-register-app)

![SPA アプリ登録](image/DEPLOY_GUIDE_GUI/register-an-application.png)

---

### 2.2 Function App のマネージド ID に Cosmos、Foundry、Cosmos MCP Toolkit へのアクセス権を付与する

1. Function App のユーザー割り当てマネージド ID に `Cosmos DB Built-in Data Contributor` ロールを割り当てます。
   a. Azure Portal で **Cloud Shell** を開き、現在のセッションが PowerShell でない場合は **PowerShell** に切り替えます。
   ![PowerShell へ切り替え](image/DEPLOY_GUIDE_GUI/cloudshell-switch-to-powershell.png)
   b. 次のコマンドを実行します。

   ```bash
   az cosmosdb sql role assignment create \
    --account-name "<your-cosmos-db-account-name>" \
    --resource-group "<your-resource-group-name>" \
    --role-definition-id "00000000-0000-0000-0000-000000000002" \
    --principal-id "<your-azure-function-uami-id>" \
    --scope "/"

   az cosmosdb sql role assignment create \
    --account-name "<your-cosmos-gremlin-db-account-name>" \
    --resource-group "<your-resource-group-name>" \
    --role-definition-id "00000000-0000-0000-0000-000000000002" \
    --principal-id "<your-azure-function-uami-id>" \
    --scope "/"
   ```

   ![Function App への Cosmos DB Built-in Data Contributor ロール割り当て](image/DEPLOY_GUIDE_GUI/assign-cosmos-role-to-func.png)
   📖 参考: [https://learn.microsoft.com/azure/cosmos-db/how-to-setup-rbac](https://learn.microsoft.com/azure/cosmos-db/how-to-setup-rbac)
2. Foundry の **project** → **アクセス制御 (IAM)** → **+ 追加** → **ロールの割り当ての追加**を開きます。

   - **ロール** は `Azure AI User`
   - **アクセスの割り当て先** は **マネージド ID** を選び、**func-todomanagement-uami** を指定します。
     ![Function App への Foundry User ロール割り当て](image/DEPLOY_GUIDE_GUI/assign-foundry-role-to-func.png)
3. Function App のマネージド ID に `MCP Tool Executor` ロールを付与します。
   a. Azure Portal で **Cloud Shell** を開き、現在のセッションが PowerShell でない場合は **PowerShell** に切り替えます。
   ![Bash へ切り替え](image/DEPLOY_GUIDE_GUI/cloudshell-switch-to-bash.png)
   b. 次のコマンドを実行します。

   ```powershell
   $TenantDomain = "<Specify your tenant id>"
   $ResourceName = "Azure Cosmos DB MCP Toolkit API"
   $AppRoleName = "Mcp.Tool.Executor"
   $PrincipalName = "foundry-todomanagement-v2/projects/proj-default"
   $Resource = az ad sp list --display-name $ResourceName --query "{ AppRoleId: [0] .appRoles [?value=='$AppRoleName'].id | [0], ObjectId:[0] .id }" -o json | ConvertFrom-Json

   $Principal = az ad sp list --display-name $PrincipalName --query "{ ObjectId: [0] .id }" -o json | ConvertFrom-Json


   $spObjectId = $Resource.ObjectId 
   $body = @{
      principalId = $Principal.ObjectId
      resourceId = $Resource.ObjectId 
      appRoleId = $Resource.AppRoleId
   } | ConvertTo-Json

   az rest --method POST `
      --url "https://graph.microsoft.com/v1.0/servicePrincipals/$spObjectId/appRoleAssignedTo" `
      --headers "Content-Type=application/json" `
      --body $body 2>&1

   ```

---

## フェーズ 3. Foundry Agent を構成する

### 3.1 Cosmos DB 向け MCP ツールをデプロイする

1. GitHub リポジトリ [https://github.com/AzureCosmosDB/MCPToolKit#option-a-deploy-to-azure-button](https://github.com/AzureCosmosDB/MCPToolKit#option-a-deploy-to-azure-button) を開きます。
2. **Deploy to Azure** を選択します。
   - **リソース グループ**: `rg-todomanagementv2-dev`
   - **リージョン**: リソース グループと同じ
   - Cosmos Endpoint: 手順 1.2 で作成した Cosmos DB アカウントのエンドポイント。例: `https://cosmos-todomanagement-v2.documents.azure.com:443/`
   - Azure AI Service Endpoint: Foundry プロジェクトのエンドポイント。例: `https://foundry-todomanagement-v2.services.ai.azure.com/api/projects/proj-default`
   - Embedding Deployment Name: `text-embedding-3-small`
3. **確認と作成** → **作成** を選択します。
   ![Cosmos MCP のデプロイ](image/DEPLOY_GUIDE_GUI/3-01-depoly-cosmos-mcp.png)
4. MCP Server アプリケーションをデプロイします。
   a. Azure Portal で **Cloud Shell** を開き、現在のセッションが PowerShell でない場合は **PowerShell** に切り替えます。
   ![PowerShell へ切り替え](image/DEPLOY_GUIDE_GUI/cloudshell-switch-to-powershell.png)
   b. 次のコマンドでリポジトリをクローンします。

   ```powershell
   git clone https://github.com/AzureCosmosDB/MCPToolKit.git
   cd MCPToolKit
   ```

   c. スクリプトを変更します。Cloud Shell から PowerShell スクリプトを実行するため、Docker は利用できません。

   ```powershell
    copy ./scripts/Deploy-Cosmos-MCP-Toolkit.ps1 ./scripts/Deploy-Cosmos-MCP-Toolkit-CloudShellVersion.ps1
   ```

   **エディター** を開き、`Deploy-Cosmos-MCP-Toolkit-CloudShellVersion.ps1` を編集します。
   851 行目へ移動し、次の内容に変更します。

   ```powershell
   az acr login --name $ACR_NAME --resource-group $script:ACR_RESOURCE_GROUP --expose-token
   ```

   870 行目へ移動し、870〜882 行をコメントアウトします。
   そのうえで、870 行目を次のコマンドに置き換えます。

   ```powershell
   az acr build -r $ACR_NAME --platform linux/amd64 -f Dockerfile.runtime . -t $IMAGE_TAG
   ```

   ![スクリプトの修正](image/DEPLOY_GUIDE_GUI/3-02-modify-script.png)

   d. リポジトリ ルートでデプロイ スクリプトを実行します。

   ```powershell
   .\scripts\Deploy-Cosmos-MCP-Toolkit-CloudShellVersion.ps1 -ResourceGroup "rg-todomanagementv2-dev"
   ```
5. デプロイ結果をテストします。
   a. **コンテナー アプリ** を検索し、新しく作成されたコンテナー アプリ **mcp-toolkit-app** を開きます。
   b. **アプリケーション URL** を選択して、MCP アプリを新しいタブで開きます。
   c. Azure Portal で **Cloud Shell** を開き、現在のセッションが Bash でない場合は **Bash** に切り替えます。
   ![Bash へ切り替え](image/DEPLOY_GUIDE_GUI/cloudshell-switch-to-bash.png)
   d. 次のコマンドを実行して client id と tenant id を取得し、保存します。

   ```bash
   az ad app list --display-name "Azure Cosmos DB MCP Toolkit API" --query "[0].appId" -o tsv
   az account show --query "tenantId" -o tsv
   ```

   e. MCP アプリに client ID と tenant ID を入力し、**Sign In with Microsoft Entra** を選択します。
   ![Entra でサインイン](image/DEPLOY_GUIDE_GUI/3-04-sign-in-with-entra.png)
   f. **Test Tool** → **Select Tool** で `List Databases` を選択し、**Invoke Selected Tool** を実行して正しい結果が返ることを確認します。
   ![List Databases ツールのテスト](image/DEPLOY_GUIDE_GUI/3-05-test-tool.png)

📖 参考: [https://github.com/AzureCosmosDB/MCPToolKit](https://github.com/AzureCosmosDB/MCPToolKit)

---

### 3.2 Agent を作成する

1. Foundry プロジェクトを開き、**エージェント** → **エージェントの作成** を選択し、**エージェント名**を `todomanagement-agent` にして作成します。
   ![エージェントの作成](image/DEPLOY_GUIDE_GUI/3-06-create-agent.png)
2. 次の情報を設定します。
   - **モデル**: `gpt-5.4-mini`
   - **手順**: [../prompt/todomanagement-agent.instructions.md](../prompt/todomanagement-agent.instructions.md) の内容を入力
3. **ツール**:
   1. **Web search** ツールを削除します。
   2. **Azure Cosmos DB** ツールを追加します。
      a. **追加** → **すべてのツールを参照する** を選択
      ![すべてのツールを参照](image/DEPLOY_GUIDE_GUI/agent-add-tool.png)
      b. **カタログ** で `Azure Cosmos DB` を検索し、そのツールを選択して **作成** を選択
      ![Azure Cosmos DB ツールの選択](image/DEPLOY_GUIDE_GUI/agent-search-cosmos-tool.png)
      c. **ツールをエンドポイントに接続する**
      ![ツールの接続](image/DEPLOY_GUIDE_GUI/agent-connect-tool.png)
      d. Azure Cosmos DB ツールを接続
      - **名前**: `AzureCosmosDB`
      - **リモート MCP サーバー エンドポイント**: `<container-application-url>/mcp`。例: `https://mcp-toolkit-app.livelyforest-279726ad.japaneast.azurecontainerapps.io/mcp`
      - **認証**: `Microsoft Entra`
      - **種類**: `プロジェクト マネージド ID`
      - **対象ユーザー**: `<entra-app-client-id>` を 対象ユーザー として入力します。この値は `az ad app list --display-name "Azure Cosmos DB MCP Toolkit API" --query "[0].appId" -o tsv` の出力です。
        ![ツールの接続](image/DEPLOY_GUIDE_GUI/agent-connect-tool-02.png)
        e. **Connect** を選択します。
4. **メモリ** → **作成** → **メモリ ストアを作成する** を選択します。
5. Agent を **保存** し、**名前**（例: `todomanagement-agent`）と **バージョン**（例: `3`）を控えます。
6. Agent をテストします。
   1. **プレイグラウンド** に次のメッセージを入力します。ツール呼び出しの承認を求められたら許可します。
      `Cosmos DB アカウント内のすべてのデータベースを一覧表示する`
      ![Cosmos DB ツールのテスト](image/DEPLOY_GUIDE_GUI/agent-test-cosmos-tool.png)
      📖 参考: [https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/tool-catalog](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/tool-catalog)

---

## フェーズ 4. アプリケーションを構成してデプロイする

### 4.1 Function App のアプリケーション設定を行う

Function App の **設定** → **環境変数** → **+ 追加** で、次の変数を追加します。

| 名前                             | 値                                                                                                            |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `COSMOS_AUTH_MODE`             　| `aad`                                                                                                       |
| `COSMOS_AUTO_CREATE`           　| `true`                                                                                                      |
| `COSMOS_ENDPOINT`              　| `https://<cosmos>.documents.azure.com:443/`、手順 1.2 のエンドポイント                                      |
| `COSMOS_DATABASE`              　| `todo-db`                                                                                                   |
| `COSMOS_GREMLIN_ENDPOINT`      　| `https://<cosmos>.documents.azure.com:443/`、手順 1.3 のエンドポイント                                      |
| `COSMOS_GRAPH_DATABASE`        　| `todo-graph-db`                                                                                             |
| `COSMOS_GRAPH_NAME`            　| `todo-graph`                                                                                                |
| `FOUNDRY_AGENT_ENDPOINT`       　| `https://<foundry>.services.ai.azure.com/api/projects/proj-default`、手順 1.4 のプロジェクト エンドポイント |
| `FOUNDRY_EMBEDDING_DEPLOYMENT` 　| `text-embedding-3-small`                                                                                    |
| `FOUNDRY_AGENT_NAME`           　| `todomanagement-agent`、手順 3.2 の agent 名                                                                |
| `FOUNDRY_AGENT_VERSION`        　| 例:`1`、手順 3.2 の agent バージョン                                                                        |

**適用** を選択します。

> Cosmos アカウント キーを使いたい場合は、`COSMOS_AUTH_MODE=key` に設定し、RBAC の代わりに `COSMOS_KEY=<primary key>` を追加してください。

![Function App 設定](image/DEPLOY_GUIDE_GUI/function-app-settings.png)

---

### 4.2 リポジトリの準備

テンプレートから自分のリポジトリを作成します。詳しくは [Creating a repository from a template (GitHub Docs)](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template) を参照してください。

1. テンプレート リポジトリ [https://github.com/Liminghao0922/todomanagement_v2](https://github.com/Liminghao0922/todomanagement_v2) を開きます。
2. **Use this template** → **Create a new repository** を選択します。
3. 次を設定します。
   - **Repository name**: 例 `my-todo-app-v2`
   - **Visibility**: `Public`（このワークショップ フローでは推奨）
4. **Create repository from template** を選択します。
5. リポジトリが作成されるまで待ちます。

---

### 4.3 GitHub Actions の構成

最初に Azure 資格情報とリソース情報を GitHub Actions に設定し、その後でワークフロー ファイルを有効化します。これにより、初回実行が空振りまたは失敗するのを避けられます。

#### 4.3.1 Azure サービス プリンシパルと資格情報を作成する

参考: [Create an Azure service principal (MS Learn)](https://learn.microsoft.com/en-us/azure/developer/github/publish-docker-container)

1. Azure Portal で **Azure Cloud Shell** を開きます。
2. 次のコマンドを実行し、リソース グループにスコープを限定したサービス プリンシパルを作成します。

   ```powershell
   # Check current subscription
   az account show

   # Switch to a different subscription (if needed)
   # Replace `<subscription-id>` with your subscription ID from Phase 1 summary (Step 1.9).
   az account set --subscription "<subscription-id>"

   # Set variables
   $subscriptionId = $(az account show --query id -o tsv)
   $spName = "github-todomanagementv2-ci"
   # Replace with your resource group name from Phase 1 summary (Step 1.9) if you changed it.
   $resourceGroupName = "rg-todomanagementv2-dev"
   # Create service principal
   $sp = az ad sp create-for-rbac `
   --name $spName `
   --role "Owner" `
   --scopes "/subscriptions/$subscriptionId/resourceGroups/$resourceGroupName" `
   --json-auth | ConvertFrom-Json

   # Output as JSON (for later use)
   $sp | ConvertTo-Json
   ```

3. JSON 出力（`{...}` 全体）をコピーします。

**注意:** この JSON 出力は機密情報です。安全に保管してください。

---

#### 4.3.2 GitHub Actions Secret を追加する

1. GitHub リポジトリで **Settings** を開きます。
2. 左メニューから **Secrets and variables** > **Actions** > **New repository secret** を選び、次のリポジトリ Secret を追加します。
   | 変数                                | 値                                                 | 参照       |
   | ----------------------------------- | -------------------------------------------------- | ---------- |
   | `AZURE_CREDENTIALS`               | アプリケーション資格情報の JSON                    | 手順 4.3.1 |
   | `AZURE_STATIC_WEB_APPS_API_TOKEN` | Static Web App の**Manage deployment token** | 手順 1.6   |

 ![AZURE_CREDENTIALS secret の追加](image/DEPLOY_GUIDE_GUI/github-add-cred.png)

---

#### 4.3.3 GitHub Repository Variables を追加する

参考: [Using variables in GitHub Actions (GitHub Docs)](https://docs.github.com/en/actions/learn-github-actions/variables)

GitHub リポジトリの **Settings** > **Secrets and variables** > **Actions** で **Variables** を選択し、次のリポジトリ変数を追加します。

| 変数                   | 値                                          | 参照     |
| ---------------------- | ------------------------------------------- | -------- |
| `AZURE_CLIENT_ID`    | Entra ID アプリの Client ID                 | 手順 2.1 |
| `AZURE_TENANT_ID`    | Entra ID テナント ID                        | 手順 2.1 |
| `AZURE_REDIRECT_URI` | Static Web App の URL                       | 手順 1.6 |
| `FUNCTION_APP_NAME`  | Function App 名。例:`func-todomanagement` | 手順 1.5 |

---

#### 4.3.4 ワークフロー ファイルを準備する

参考: [GitHub Actions documentation](https://docs.github.com/en/actions)

Secret と変数の設定後に、ワークフロー ファイルを有効化します。

このリポジトリでは、CI/CD ワークフロー ファイルはテンプレートとして用意されています。

- `.github/workflows/build-deploy-api.yml.template` → `build-deploy-api.yml` にリネーム
- `.github/workflows/build-deploy-web.yml.template` → `build-deploy-web.yml` にリネーム

ファイル作成手順:

1. Azure Portal で **Azure Cloud Shell** を開きます。
2. 次のコマンドを実行します。

```powershell
git clone <your-repo-url>
cd my-todo-app

# Copy templates without .template extension
cp .github/workflows/build-deploy-api.yml.template .github/workflows/build-deploy-api.yml
cp .github/workflows/build-deploy-web.yml.template .github/workflows/build-deploy-web.yml

# Commit and push
git add .github/workflows/*.yml
git commit -m "Enable API and Web build-deploy workflows"
git push origin main
```

---

#### 4.3.5 GitHub Actions ワークフローを実行する

1. リポジトリの **Actions** タブを開きます。
2. 次の 2 つのワークフローが表示されるはずです。
   - `Build and Deploy API to ACR`
   - `Build and Deploy Web to ACR`
3. ワークフローが表示されない場合は、次を確認してください。
   - `.github/workflows/build-deploy-api.yml` と `.github/workflows/build-deploy-web.yml` が `main` にコミットされていること
4. ワークフローは `main` ブランチへのコミット時に自動実行されます。
5. 各ワークフローを開いて実行状況を確認します。
   - **red X**（失敗）または **green checkmark**（成功）を確認
   - 通常、両方とも 5〜10 分以内に完了します

**ワークフロー失敗時の確認ポイント:**

- **AZURE_CREDENTIALS** が正しい JSON であること
- すべての変数が入力されていること
- Azure リソースが存在し、名前が完全一致していること

---

## フェーズ 5. エンドツーエンドで検証する

1. `https://<swa>.azurestaticapps.net` を開き、MSAL でサインインします。
2. **Todos** ページで **Generate to Test Todos**（デモ用シード処理）をクリックし、Todo が生成されることを確認します。
   ![Todos のエンドツーエンド確認](image/DEPLOY_GUIDE_GUI/e2e-check-verify-todos.png)
3. **Projects** を開き、シード済みプロジェクトを選択して **View Graph** を開き、Gremlin グラフ由来のエッジが Cytoscape で描画されることを確認します。
   ![Project のエンドツーエンド確認](image/DEPLOY_GUIDE_GUI/e2e-check-verify-projects-01.png)
   ![Project Graph のエンドツーエンド確認](image/DEPLOY_GUIDE_GUI/e2e-check-verify-projects-02.png)
4. **Chat** で `今日、何を優先すべきでしょうか？` のようなメッセージを送信し、Foundry agent が応答し、必要に応じて `Azure Cosmos DB` ツールを呼び出すことを確認します。
   ![Chat のエンドツーエンド確認](image/DEPLOY_GUIDE_GUI/e2e-check-verify-chat.png)
   ![Chat ツール呼び出しの確認](image/DEPLOY_GUIDE_GUI/e2e-check-verify-chat-tool-call.png)

---

## フェーズ 6. クリーンアップ

```powershell
az group delete --name rg-todomanagementv2-dev --yes --no-wait
```

不要になった場合は、**Microsoft Entra ID → App registrations** から Entra ID アプリ登録 `todomanagement-spa` を手動で削除してください。

---

## 関連ドキュメント

- [handson/DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)
- [docs/ARCHITECTURE_GUIDE.md](../docs/ARCHITECTURE_GUIDE.md)
