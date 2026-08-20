# 講師向け準備ガイド（Foundry Focus・初級者向け）

[English](INSTRUCTOR_PREP_GUIDE_FOUNDRY_FOCUS.md) | [简体中文](INSTRUCTOR_PREP_GUIDE_FOUNDRY_FOCUS-zh_CN.md) | [日本語](INSTRUCTOR_PREP_GUIDE_FOUNDRY_FOCUS-ja_JP.md)

[受講者ガイド](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS-ja_JP.md)

このガイドでは、初級者向けの Todo Management v2 ワークショップにおける、講師側のセットアップを概説します。授業前に、講師はデプロイ、サインインアクセスの構成、共有 Container Apps 環境の準備を完了します。その後、受講者は各自の Foundry リソースとプロジェクトを作成し、独自の embedding と GPT モデルをデプロイし、Cosmos DB MCP ツールと Prompt agent を構築します。

講師の準備は、主に次の 4 つで構成されます。

1. `azd` で Todo アプリ全体をデプロイする。
2. 受講者が Todo アプリへサインインできる権限を構成する。
3. 受講者が所有する Foundry リソース向けに、サブスクリプションアクセス、プロバイダー登録、モデルクォータを準備する。
4. 受講者の Cosmos DB MCP デプロイ向けに、共有 Container Apps 環境を準備する。

講師準備の想定時間: 初回は 90-150 分、手順に慣れた後は 45-60 分。

---

## 0. このバージョンの前提

この Foundry Focus トラックは、次を前提とします。

- 受講者はインフラデプロイのコマンドを実行しない。
- 受講者はラボ中に各自の Cosmos DB MCP Container App を作成する場合があるが、講師が事前に共有 Container Apps 環境とイメージアクセスを準備する。
- Todo アプリ本体は講師が `azd up` でデプロイする。
- 各受講者は一意の名前で Foundry リソース、プロジェクト、埋め込みデプロイ、MCP 接続、Prompt agent を作成する。

このリポジトリには、本トラックに必要な最小限の `azd` サポートが含まれています。

- [../azure.yaml](../azure.yaml)
- [../infra/main.parameters.json](../infra/main.parameters.json)
- [../infra/azd-postprovision.ps1](../infra/azd-postprovision.ps1)

`azd` フローは Bicep インフラをプロビジョニングした後、post-provision フックを実行し、Functions API の公開、Static Web App のビルド/デプロイ、SWA と Functions の連携、ヘルスエンドポイントの検証を行います。

---

## 1. 講師の前提条件

以下の確認は、講師端末または Azure Cloud Shell PowerShell で実行してください。

```powershell
azd version
az version
func --version
python --version
node --version
npm --version
```

必要バージョン:

| ツール                     | 想定値                         |
| -------------------------- | ------------------------------ |
| Azure Developer CLI        | `azd` installed              |
| Azure CLI                  | 対象テナントにサインイン済み   |
| Azure Functions Core Tools | v4                             |
| Python                     | 3.11+                          |
| Node.js                    | 20+                            |
| npm                        | 利用可能                       |

講師に必要な権限:

- Azure サブスクリプション/リソースグループで Contributor または Owner。
- Microsoft Entra のアプリ登録を作成する権限。
- アプリ同意の付与、または Enterprise Application へのユーザー/グループ割り当てを行う権限。
- Azure Container Registry と Container Apps 環境を作成する権限。
- Foundry リソース、プロジェクト、モデル、agent を作成および構成する権限。

受講者アカウント準備の推奨:

- ワークショップ受講者用の Microsoft Entra セキュリティグループを作成または特定する。
- 授業前に受講者全員をそのグループへ追加する。
- Todo アプリのサインイン割り当てと、共有 Container Apps 環境アクセスに同グループを使用する。

---

## 2. azd で Todo アプリ全体をデプロイする

### 2.1 サインインと azd 環境の作成

Azure Cloud Shell PowerShell で、まずリポジトリをクローンし、そのフォルダーへ移動します。

```powershell
git clone https://github.com/Liminghao0922/todomanagement_v2.git
Set-Location todomanagement_v2

$subscriptionId = "<subscription-id>"
$location = "japaneast"
$staticWebAppLocation = "eastasia"
$azdEnvName = "foundry-focus-20260806"
$resourceGroup = "rg-todomanagementv2-instructor"

azd auth login
azd env new $azdEnvName
azd env set AZURE_SUBSCRIPTION_ID $subscriptionId
azd env set AZURE_LOCATION $location
azd env set STATIC_WEB_APP_LOCATION $staticWebAppLocation
azd env set AZURE_RESOURCE_GROUP $resourceGroup
```

主要ワークロード リソースには `japaneast`、Static Web Apps には `eastasia` を使用します。`Microsoft.Web/staticSites` は Japan East では利用できません。

成功条件:

- `azd env get-values` に subscription、location、resource group の値が表示される。
- 現在の Azure アカウントが想定テナントにある。

検証:

```powershell
azd env get-values
az account show --output table
```

### 2.2 プロビジョニングのプレビュー

リソース作成前に、プレビューを実行します。

```powershell
azd provision --preview
```

プレビューに想定どおりの `Create` リソースが含まれていることを確認してください。現在のテスト環境（`environment=todomangementv2`）では、次のようなエントリが表示されます。

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

`projectName`、`environment`、resource group が異なる場合、suffix 部分は変わります。リソース構成として、Todo アプリ関連リソース、2 つの Cosmos アカウント、Cosmos DB MCP Toolkit リソースが含まれていることを確認してください。

このガイドの命名規則は、現行 Bicep テンプレートに合わせています。

- `<suffix>` = `uniqueString(resourceGroup().id)`。
- Azure AI Services: `aifoundry-<projectName>-<suffix>`
- Cosmos SQL account: `cossql<projectName><suffix>`
- Cosmos Gremlin account: `cosgr<projectName><suffix>`
- Storage account: `st<projectNameNoDashFirst8><suffix>` (project name lowercased, `-`/`_` removed, then first 8 chars)
- App Service plan: `asp-<projectName>-<env>`
- Function app name: `func-<projectName>-<env>-<suffix>` (preview resource type is shown as `Web App`)
- Static Web App: `swa-<projectName>-<suffix>`
- Container Registry: `acr<projectNameFirst10><shortSuffix>`
- Container App: `mcp-<projectNameFirst12>-<shortSuffix>`
- Container Apps environment: `cae-<projectNameFirst12>-<shortSuffix>`
- Log Analytics workspace: `log-<projectNameFirst12>-mcp-<shortSuffix>`

一部のリソースが既存である場合や、子リソース/変更なしとして表示される場合は、一覧が多少変わることがあります。`azd up` 後のデプロイ出力から、Function App、アプリ登録、エンドポイント、ID を確認してください。

プレビューに想定外のサブスクリプション、リージョン、リソースグループが表示された場合は、続行せずに azd 環境値を修正してください。

### 2.3 フルデプロイを実行

次を実行します。

```powershell
azd up
```

このリポジトリで `azd up` が行う処理:

1. [../infra/main.bicep](../infra/main.bicep) からインフラをプロビジョニングする。
2. [../infra/azd-postprovision.ps1](../infra/azd-postprovision.ps1) を実行し、Entra、RBAC、Cosmos 権限、Foundry RemoteTool 接続を構成する。
3. `azd deploy` を実行する（postdeploy のエントリポイントは [../infra/azd-deploy.ps1](../infra/azd-deploy.ps1)）。
4. Cosmos MCP Toolkit イメージをビルドして有効化し、Foundry Agent を作成または更新する。
5. Python Functions API を公開し、Vue Static Web App をビルド/デプロイする。
6. Static Web App の Production APIs を Function App にリンクしようと試みる。
7. Function App と Static Web App ルート上の `/api/health` を検証する。

フェーズを分けて実行する場合は、インフラに `azd provision`、アプリケーション コンポーネントに `azd deploy` を使用します。

provision と deploy のフックでは、次の出力が想定されます。

- Todo app URL
- Function URL
- Foundry resource name
- Foundry project name
- Foundry project endpoint
- Entra App Registration client ID
- Tenant ID

成功条件:

- `azd up` がプロビジョニング失敗なしで完了する。
- Function のヘルスエンドポイントが `healthy` を返す。
- ブラウザーで Todo app URL が開ける。
- Static Web App の `/api/health` が `healthy` を返す、または SWA API リンクを手動で完了するようにスクリプトが警告する。

### 2.4 SWA API リンク失敗時の手動対応

フックが API リンクの警告を出した場合は、Azure Portal で次を実施してください。

1. Static Web App を開く。
2. **Settings** -> **APIs** に移動する。
3. **Production** 行で **Link** を選択する。
4. 次を設定する。
   - Backend resource type: **Function App**
   - Subscription: workshop subscription
   - Resource name: deployed Function App
   - Backend slot: **Production**
5. **Link** を選択する。

検証:

```powershell
$todoAppUrl = "<static-web-app-url-from-azd-output>"
Invoke-RestMethod "$todoAppUrl/api/health"
```

期待結果:

```json
{
  "status": "healthy",
  "service": "Todo Management Functions API"
}
```

---

## 3. デプロイ値を記録する

`azd up` の後、後続セットアップと受講者配布資料のために値を収集します。

```powershell
$resourceGroup = (azd env get-value AZURE_RESOURCE_GROUP)

$deploymentName = az deployment group list `
  --resource-group $resourceGroup `
  --query "max_by([].{name:name,timestamp:properties.timestamp}, &timestamp).name" `
  --output tsv

$outputs = az deployment group show `
  --resource-group $resourceGroup `
  --name $deploymentName `
  --query properties.outputs `
  --output json | ConvertFrom-Json

$functionAppName = $outputs.functionAppName.value
$functionAppUrl = $outputs.functionAppUrl.value
$staticWebAppName = $outputs.staticWebAppName.value
$staticWebAppUrl = $outputs.staticWebAppUrl.value
$cosmosAccountName = $outputs.cosmosAccountName.value
$cosmosEndpoint = $outputs.cosmosEndpoint.value
$cosmosAccountId = az cosmosdb show `
  --resource-group $resourceGroup `
  --name $cosmosAccountName `
  --query id `
  --output tsv
$clientId = $outputs.appRegistrationClientId.value
$tenantId = $outputs.tenantId.value
$foundryResourceName = $outputs.foundryResourceName.value
$foundryProjectName = $outputs.foundryProjectName.value
$foundryProjectResourceId = $outputs.foundryProjectResourceId.value
$foundryProjectEndpoint = $outputs.foundryProjectEndpoint.value
$cosmosMcpAcrName = $outputs.cosmosMcpAcrName.value
$cosmosMcpAcrLoginServer = $outputs.cosmosMcpAcrLoginServer.value
$cosmosMcpImageRepository = $outputs.cosmosMcpImageRepository.value
$cosmosMcpImageTag = $outputs.cosmosMcpImageTag.value
$cosmosMcpImage = $outputs.cosmosMcpImage.value

[ordered]@{
  resourceGroup = $resourceGroup
  functionAppName = $functionAppName
  functionAppUrl = $functionAppUrl
  staticWebAppName = $staticWebAppName
  staticWebAppUrl = $staticWebAppUrl
  cosmosAccountName = $cosmosAccountName
  cosmosResourceGroup = $resourceGroup
  cosmosResourceId = $cosmosAccountId
  cosmosEndpoint = $cosmosEndpoint
  clientId = $clientId
  tenantId = $tenantId
  foundryResourceName = $foundryResourceName
  foundryProjectName = $foundryProjectName
  foundryProjectResourceId = $foundryProjectResourceId
  foundryProjectEndpoint = $foundryProjectEndpoint
  cosmosMcpAcrName = $cosmosMcpAcrName
  cosmosMcpAcrLoginServer = $cosmosMcpAcrLoginServer
  cosmosMcpImageRepository = $cosmosMcpImageRepository
  cosmosMcpImageTag = $cosmosMcpImageTag
  cosmosMcpImage = $cosmosMcpImage
} | ConvertTo-Json | Out-File .\handson\foundry-focus-class-values.json -Encoding utf8
```

成功条件:

- [foundry-focus-class-values.json](foundry-focus-class-values.json) が [handson](.) 配下に作成される、または講師限定の配布資料にコピーされている。
- 値が空でない。

シークレットやデプロイトークンは受講者と共有しないでください。

---

## 4. Todo アプリの受講者ログイン権限を構成する

Bicep デプロイにより SPA アプリ登録は作成されます。講師は、受講者がデプロイ済み Todo アプリにサインインできることを確認する必要があります。

### 4.1 Redirect URI を確認する

Microsoft Entra 管理センターで実施:

1. **Microsoft Entra ID** -> **App registrations** を開く。
2. `$clientId` の Application (client) ID で検索する。
3. **Authentication** を開く。
4. 次の SPA redirect URI が存在することを確認する。

   - `$staticWebAppUrl`
   - `http://localhost:5173/`

末尾スラッシュ付きのみ存在する場合は、末尾スラッシュなしの値も追加してください。

成功条件:

- テスト受講者が redirect URI mismatch エラーなしでサインインを完了できる。

### 4.2 API 同意を付与または確認する

同じアプリ登録で実施:

1. **API permissions** を開く。
2. `User.Read` や、カレンダー シナリオ有効時のカレンダー関連権限など、アプリに必要な Microsoft Graph delegated permissions を確認する。
3. テナントでユーザー同意が許可されていない場合は **Grant admin consent** を選択する。

成功条件:

- 同意プロンプトが受講者サインインを妨げない。
- テスト受講者がデプロイ済み Todo app URL からサインインできる。

### 4.3 Enterprise Application に受講者を割り当てる

Todo アプリへのアクセス対象を制御したい場合に使用します。

1. **Microsoft Entra ID** -> **Enterprise applications** を開く。
2. デプロイで作成された app registration の表示名、または Application ID `$clientId` で検索する。
3. **Properties** を開く。
4. **Assignment required?** を **Yes** に設定する。
5. **Users and groups** -> **+ Add user/group** を開く。
6. ワークショップ受講者のセキュリティグループ、または個別受講者アカウントを追加する。

**Assignment required?** を **No** のままにすると、同意と redirect URI が正しければテナント内ユーザーはサインインできます。教室運用では、受講者グループを使った assignment-required を推奨します。

成功条件:

- 割り当て済み受講者アカウントでサインインできる。
- Assignment required 有効時、未割り当てアカウントはアプリにアクセスできない。

### 4.4 受講者ログインのスモークテスト

受講者レベルのテストアカウントを使用します。

1. プライベートブラウザー ウィンドウで `$staticWebAppUrl` を開く。
2. サインインする。
3. **Todos** と **Projects** ページが読み込まれることを確認する。
4. **Generate 50 Test Todos** を 1 回選択して授業データを投入する。あるいは授業前に講師アカウントでデータ投入しておく。

成功条件:

- 受講者がサインインできる。
- Todo データが読み込まれる。
- `AADSTS` の redirect/consent/assignment エラーが表示されない。

---

## 5. 受講者の Cosmos DB MCP デプロイ向け Container Apps 環境を準備する

目的は、受講者が Container Apps 環境の作成や MCP イメージのビルドを行わずに、各自の Cosmos DB MCP Container App をデプロイできるようにすることです。

受講者には、ビルド済みイメージ、割り当て済み Container Apps 環境、一意な Container App 名を提供します。

### 5.1 azd でデプロイ済みの ACR イメージを確認して再利用する

別の ACR を作成したり、MCP Toolkit イメージを手動ビルドしたりしないでください。`azd up` フローで、すでに次が実行されています。

1. ワークショップ用 ACR の作成。
2. その ACR で `mcp-toolkit:<tag>` のビルド。
3. 講師 MCP Container App 上でのイメージ有効化。

セクション 3 で記録した値を使用します。

| 値         | 取得元                         |
| ---------- | ------------------------------ |
| Registry   | `$cosmosMcpAcrLoginServer`   |
| Repository | `$cosmosMcpImageRepository`  |
| Tag        | `$cosmosMcpImageTag`         |
| Full image | `$cosmosMcpImage`            |

ACR の Admin user は無効のままです。各ワークショップ Container Apps 環境は、それぞれの system-assigned managed identity を使用し、この ACR に対して `AcrPull` を付与されます。受講者は Container App 作成時に、レジストリ認証として環境の system identity を選択します。

既存イメージを検証:

```powershell
az acr repository show-tags `
  --name $cosmosMcpAcrName `
  --repository $cosmosMcpImageRepository `
  --output table
```

成功条件:

- `az acr repository show-tags` に `$cosmosMcpImageTag` が表示される。
- 講師が Portal でテスト Container App 作成時にイメージを選択できる。

### 5.2 共有 Container Apps 環境を作成する

共有する各 Container Apps 環境で system-assigned identity を有効化し、その identity にワークショップ ACR への `AcrPull` を付与します。この環境 identity は共有イメージの pull 専用です。各受講者の Container App は、Cosmos DB と Foundry ランタイムアクセス用に、別途その Container App 自身の system-assigned identity を有効化します。

推奨サイジング:

- 1 つの Container Apps 環境あたり受講者は最大 8 名。
- 受講者 1 名に対し一意の Container App 名を割り当てる。
- 大人数クラスは複数環境を使用する。
- 各受講者 MCP アプリは `0.5` vCPU、`1 GiB` メモリ、レプリカ最大 1 を使用する。

`environmentCount = Ceiling(participantCount / 8)` を使います。各環境を system-assigned identity 付きで作成します。以下のコマンドは Azure Resource Manager を直接使用するため、Azure CLI の `containerapp` 拡張機能は不要です。

```powershell
$participantCount = 24
$participantsPerEnvironment = 8
$environmentCount = [Math]::Ceiling($participantCount / $participantsPerEnvironment)
$environmentPrefix = "cae-todomanagement-workshop"

1..$environmentCount | ForEach-Object {
  $environmentName = "{0}-{1:D2}" -f $environmentPrefix, $_
  $environmentResourceId = "/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.App/managedEnvironments/$environmentName"
  $environmentBody = @{
    location = $location
    identity = @{
      type = "SystemAssigned"
    }
    properties = @{}
  }
  $environmentBodyFile = Join-Path $HOME "$environmentName.json"

  try {
    $environmentBody | ConvertTo-Json -Depth 10 | Set-Content $environmentBodyFile -Encoding utf8
    az rest `
      --method put `
      --url "https://management.azure.com$($environmentResourceId)?api-version=2024-03-01" `
      --headers "Content-Type=application/json" `
      --body "@$environmentBodyFile" `
      --output none
  }
  finally {
    Remove-Item $environmentBodyFile -ErrorAction SilentlyContinue
  }
}
```

すべての環境が `Succeeded` になり、`identity.principalId` が空でないことを確認した後、各環境の system identity に `AcrPull` を付与します。

```powershell
$acrId = az acr show `
  --name $cosmosMcpAcrName `
  --resource-group $resourceGroup `
  --query id `
  --output tsv

1..$environmentCount | ForEach-Object {
  $environmentName = "{0}-{1:D2}" -f $environmentPrefix, $_
  $environmentResourceId = "/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.App/managedEnvironments/$environmentName"
  $environmentPrincipalId = az rest `
    --method get `
    --url "https://management.azure.com$($environmentResourceId)?api-version=2024-03-01" `
    --query identity.principalId `
    --output tsv

  if ([string]::IsNullOrWhiteSpace($environmentPrincipalId)) {
    throw "System identity is not ready for $environmentName. Confirm provisioning and rerun this role-assignment block."
  }

  az role assignment create `
    --assignee-object-id $environmentPrincipalId `
    --assignee-principal-type ServicePrincipal `
    --role AcrPull `
    --scope $acrId
}
```

PUT 応答は最初 `Waiting` になる場合があります。Azure 側のプロビジョニング完了後、すべての環境が準備完了で system-assigned identity を持つことを確認してください。

```powershell
1..$environmentCount | ForEach-Object {
  $environmentName = "{0}-{1:D2}" -f $environmentPrefix, $_
  $environmentResourceId = "/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.App/managedEnvironments/$environmentName"

  az rest `
    --method get `
    --url "https://management.azure.com$($environmentResourceId)?api-version=2024-03-01" `
    --query "{Name:name,State:properties.provisioningState,Location:location,Identity:identity}" `
    --output json
}
```

割り当て例:

| 受講者範囲 | 環境                               | Container App 名                          |
| ---------- | ---------------------------------- | ------------------------------------------ |
| 1-8        | `cae-todomanagement-workshop-01` | `mcp-toolkit-p01` to `mcp-toolkit-p08` |
| 9-16       | `cae-todomanagement-workshop-02` | `mcp-toolkit-p09` to `mcp-toolkit-p16` |

Container App 名は、共有環境内で一意である必要があります。各受講者について、割り当て環境 1 つと一意の Container App 名 1 つを記録してください。

授業前にクォータと現在使用量を確認:

```powershell
1..$environmentCount | ForEach-Object {
  $environmentName = "{0}-{1:D2}" -f $environmentPrefix, $_
  $environmentResourceId = "/subscriptions/$subscriptionId/resourceGroups/$resourceGroup/providers/Microsoft.App/managedEnvironments/$environmentName"

  az rest `
    --method get `
    --url "https://management.azure.com$($environmentResourceId)/usages?api-version=2024-03-01" `
    --query "value[].{Name:name.localizedValue,Current:currentValue,Limit:limit}" `
    --output table
}
```

環境が app 数または consumption-core のクォータ上限に近づいた場合は、授業前に新しい環境を追加し、受講者グループを移動してください。

成功条件:

- すべての環境が `Succeeded` を報告する。
- すべての環境で `identity.type` が `SystemAssigned` で、`identity.principalId` が空でない。
- すべての環境 system identity がワークショップ ACR に対して `AcrPull` を持つ。
- 授業前に環境の使用量/クォータ確認が完了している。
- 受講者が、自分に割り当てられた環境にのみ Container App を作成できる。

### 5.3 受講者アクセスを付与する

各受講者または受講者グループに、次を付与します。

| スコープ                            | ロール                         | 理由                                                                                                     |
| ----------------------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------- |
| ワークショップ ACR                  | Owner                          | このラボのフローで、受講者が Portal 上で共有イメージを参照/選択できるようにする                         |
| 割り当て済み Container Apps 環境    | Container Apps Contributor     | 事前作成済み環境に、受講者が自分の MCP Container App を作成できるようにする                             |
| 受講者リソースグループ              | Owner or Contributor           | 割り当てられた Container App リソースを受講者が作成できるようにする                                     |
| 共有 Cosmos DB account              | User Access Administrator と DocumentDB Account Contributor | Container App identity に対する Cosmos DB SQL data-plane role assignment を受講者が作成できるようにする |

これらの広い権限は一時的なトレーニング ラボでは許容できますが、本番ガイダンスとして再利用しないでください。

各受講者は Container App 作成後に system-assigned identity を有効化します。受講者に共有リソースへのロール割り当て権限がない場合、ラボ中に講師が次の割り当てを実施します。

- 共有 Cosmos account で、その identity に `Cosmos DB Built-in Data Reader` を割り当てる。
- 受講者の Foundry resource で、その identity に `Foundry User` を割り当てる。
- 受講者の Enterprise Application で、Foundry project managed identity に `MCP Tool Executor` を割り当てる。

受講者 Container App の system identity には `AcrPull` は不要です。レジストリ認証には Container Apps 環境の system identity を使用します。

受講者には app registration 作成権限も必要です。受講者が Enterprise Application ロールへのユーザーまたは managed identity 割り当てを実行できない場合、講師がその割り当てを行います。

`User Access Administrator`と`DocumentDB Account Contributor` は受講者アカウントまたは受講者グループに割り当てます。Container App identity には割り当てないでください。Container App identity には、上記の実行時ロールのみを付与します。

成功条件:

- テスト受講者が割り当て済みの Container Apps 環境のみ選択できる。
- テスト受講者が、レジストリ認証として割り当て環境の system identity を選択できる。
- テスト受講者がワークショップ ACR イメージを選択できる。
- テスト受講者が新規環境を作成せず、一意名で Container App を作成できる。
- テスト受講者が共有 Cosmos DB account に対して `az cosmosdb sql role assignment create` を実行できる。

### 5.4 各受講者に渡す値

受講者ごとの配布表を準備してください。

| 項目                                | 例                                                        |
| ----------------------------------- | --------------------------------------------------------- |
| Todo アプリ URL                     | `$staticWebAppUrl`                                        |
| Foundry リージョン                  | `$location`                                               |
| Registry                            | `$cosmosMcpAcrLoginServer`                                |
| Image                               | `$cosmosMcpImageRepository`                               |
| Tag                                 | `$cosmosMcpImageTag`                                      |
| 割り当て済み Container Apps 環境    | `cae-todomanagement-workshop-01`                          |
| 環境リソースグループ                | `rg-todomanagement-instructor`                            |
| 環境リージョン                      | `japaneast`                                               |
| 環境 identity principal ID          | 割り当て済み環境の system identity principal ID           |
| 一意な Container App 名             | `mcp-toolkit-p01`                                         |
| 受講者 ID                           | `p01`                                                     |
| Cosmos endpoint                     | `$cosmosEndpoint`                                         |
| Cosmos account name                 | `$cosmosAccountName`                                      |
| Cosmos resource group               | `$resourceGroup`                                          |
| Cosmos resource ID                  | `$cosmosAccountId`                                        |
| Tenant ID                           | `$tenantId`                                               |

デプロイトークン、アプリ シークレット、ACR パスワード、講師資格情報は受講者に渡さないでください。

---

## 6. 授業前の Foundry 準備

受講者ラボでは、受講者ごとの Foundry リソース、プロジェクト、モデルデプロイを作成します。授業前に、サブスクリプション アクセス、モデル可用性、クォータを準備してください。

1. Bicep で作成した Foundry resource、`proj-todomanagement` project、モデルデプロイは、講師所有の Todo アプリ用として保持する。
2. ワークショップ サブスクリプションで `Microsoft.CognitiveServices` が登録済みであることを確認する。
3. 各受講者が自分の受講者リソースグループで Contributor または Owner を持つことを確認する。
4. 講師指定の Foundry region で、`text-embedding-3-small` と `gpt-5.4-mini` が利用可能であることを確認する。
5. 受講者全員分のデプロイに十分なモデルクォータがあることを確認する。
6. 受講者アカウントで、`aifoundry-todomanagement-p01` の作成、`proj-todomanagement-p01` の作成、`text-embedding-3-small-p01` のデプロイが可能であることをテストする。
7. 受講者が `text-embedding-3-small` デプロイ後、MCP Container App 作成前に `gpt-5.4-mini` をデプロイできることを確認する。
8. テスト用 Foundry resource を削除するか、講師ドライラン用に確保しておく。

成功条件:

- Foundry Playground で `List all databases in my Cosmos DB account.` を実行すると `todo-db` が返る。
- Todo app の Copilot パネルで `What should I prioritize today?` に回答が返る。

---

## 7. 最終講師ドライラン

受講者用テストアカウントを使用します。

### Todo App

1. `$staticWebAppUrl` を開く。
2. サインインする。
3. **Todos** を開く。
4. 生成済みデータが存在することを確認する。
5. **Projects** -> **View Graph** を開く。
6. Copilot に質問する: `What should I prioritize today?`

### Participant MCP Setup

1. 受講者手順に従ってテスト用 Container App を 1 つ作成する。
2. 割り当て済みの共有 Container Apps 環境を使用する。
3. ワークショップ ACR イメージを選択する。
4. 必要な環境変数を構成する。
5. MCP テスト UI を開く。
6. サインインして `List Databases` を呼び出す。
7. `todo-db/todos` に対して検索文字列 `adoption-plan` で `Vector Search` を呼び出す。
8. `OPENAI_ENDPOINT` が受講者リソースの `https://<resource>.openai.azure.com/` エンドポイントを使用しており、埋め込み呼び出しが `401 Unauthorized` なしで成功することを確認する。

### Foundry

1. 受講者専用の Foundry resource と project を作成する。
2. 受講者専用の `text-embedding-3-small` デプロイを作成する。
3. その resource で未提供の場合は `gpt-5.4-mini` をデプロイする。
4. その project で Prompt agent と MCP 接続を作成する。
5. 質問する: `List containers in database todo-db.`
6. Trace を開く。
7. Cosmos DB ツール呼び出しが可視化されることを確認する。

ドライランは、上記 3 領域すべてが成功した場合のみ合格です。

---

## 8. 当日の進行計画

| 時間      | アクティビティ                                                            | 担当              |
| --------- | ------------------------------------------------------------------------- | ----------------- |
| 0-10 min  | アーキテクチャと準備済みリソースを説明する                                | 講師              |
| 10-30 min | 受講者が Foundry resource、project、embedding deployment を作成する       | 受講者            |
| 30-55 min | 受講者が準備済み環境で Cosmos DB MCP Container App をデプロイ/利用する    | 受講者            |
| 55-75 min | 受講者が Prompt agent を作成し Cosmos DB MCP ツールを接続する             | 講師のガイド      |
| 75-85 min | Trace 読解演習を実施する                                                   | 受講者            |
| 85-90 min | Prompt チューニングとまとめ                                                | 受講者            |

---

## 9. 障害時対応

| 症状                                                 | 講師アクション                                                                   |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------- |
| プロビジョニング中に `azd up` が失敗する             | 授業前にインフラを修正する。受講者参加中にライブデバッグは行わない                |
| SWA API リンクが失敗する                              | Static Web App -> APIs -> Function App を手動リンクする                           |
| 受講者がサインインできない                            | Enterprise Application の割り当て、同意、redirect URI を確認する                  |
| 受講者が ACR イメージを選択できない                  | ACR Owner 割り当てと Admin user 設定を確認する                                    |
| 受講者が Container Apps 環境を選択できない           | 環境スコープでの Container Apps Contributor 割り当てを確認する                    |
| MCP ツールでデータベースを一覧表示できない           | Cosmos endpoint、managed identity/app role、tenant/client ID を確認する            |
| Foundry ツール呼び出しが失敗する                     | 準備済みのバックアップ agent または事前取得済み trace を使って講義フローを継続する |

授業前に、少なくとも 1 つの正常動作するテスト受講者アカウントと、1 つの正常動作する MCP Container App を準備しておいてください。
