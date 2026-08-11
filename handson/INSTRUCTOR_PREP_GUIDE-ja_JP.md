# 講師向け準備ガイド

[English](INSTRUCTOR_PREP_GUIDE.md) | [简体中文](INSTRUCTOR_PREP_GUIDE-zh_CN.md) | [日本語](INSTRUCTOR_PREP_GUIDE-ja_JP.md)

[参加者ガイド](DEPLOY_GUIDE_GUI-ja_JP.md)

ワークショップの前に、このガイドに沿って準備してください。参加者は GitHub アカウントを用意する必要がなく、コンテナーのビルドも行いません。講師は次の項目を準備します。

- 共有 Azure Container Registry (ACR)
- ビルド済みの Cosmos DB MCP Toolkit イメージ
- 参加者の MCP Toolkit アプリ用の共有 Container Apps 環境
- Todo Management v2 のパブリック リポジトリ URL
- 参加者が必要とするイメージと環境の値

Todo アプリケーション自体は、引き続き Azure Functions と Azure Static Web Apps で動作します。共有コンテナー イメージは Cosmos DB MCP Toolkit 専用です。

Container Apps 環境は講師が事前に作成しておくことで、当日の作業時間を大きく短縮できます。

準備時間の目安は 30 分から 45 分です。

---

## 前提条件

- リソース グループと ACR を作成できる Azure サブスクリプション
- ワークショップ用 ACR でロールを割り当てるためのアクセス許可
- Container Apps 環境を作成し、その環境でロールを割り当てるためのアクセス許可
- Azure Cloud Shell へのアクセス
- この Todo Management v2 リポジトリへのアクセス
- 参加者アカウントの一覧
- 参加者アカウント側: 参加者のリソース グループに対する **Owner**（少なくとも Contributor 以上）
- 参加者アカウント側: Microsoft Entra ID の **Application Developer**

> このガイドでは `az acr build` を使用します。コンテナーのビルドは ACR 内で実行されるため、Cloud Shell に Docker は必要ありません。

---

## 1. ワークショップ用 ACR の作成

**Azure Cloud Shell** を開いて **PowerShell** に切り替え、ワークショップ用の値を設定します。

```powershell
$subscriptionId = "<subscription-id>"
$location = "japaneast"
$resourceGroup = "rg-todomanagement-instructor"
$acrName = "<globally-unique-lowercase-name>"
$imageRepository = "mcp-toolkit"
$imageTag = "workshop-$(Get-Date -Format yyyyMMdd)"

az account set --subscription $subscriptionId
az acr check-name --name $acrName
```

ACR 名はグローバルに一意である必要があります。使用できる文字は小文字の英字と数字のみで、長さは 5 文字から 50 文字です。

リソース グループとレジストリを作成します。

```powershell
az group create `
  --name $resourceGroup `
  --location $location

az acr create `
  --resource-group $resourceGroup `
  --name $acrName `
  --sku Basic `
  --admin-enabled false

az acr update `
  --resource-group $resourceGroup `
  --name $acrName `
  --admin-enabled true
```

参加者が Portal で Container App を作成するときに ACR イメージ参照エラーを回避するため、ワークショップでは ACR 作成後に **Admin user を有効化**します。

---

## 2. MCP Toolkit イメージのビルド

講師は準備中に GitHub を使用できます。参加者はこれらのコマンドを実行しません。

```powershell
git clone https://github.com/AzureCosmosDB/MCPToolKit.git
Set-Location MCPToolKit
```

ランタイム イメージでは、ビルド済みの .NET 出力が必要です。.NET 9 SDK が利用できることを確認してから、発行します。

```powershell
dotnet --version
dotnet publish `
  src/AzureCosmosDB.MCP.Toolkit/AzureCosmosDB.MCP.Toolkit.csproj `
  --configuration Release `
  --output src/AzureCosmosDB.MCP.Toolkit/bin/publish
```

`dotnet --version` で .NET 9 が表示されない場合は、続行する前に講師環境へ .NET 9 SDK をインストールしてください。

MCP Toolkit リポジトリのルートから、リモート ACR ビルドを実行します。

```powershell
az acr build `
  --registry $acrName `
  --image "${imageRepository}:${imageTag}" `
  --file Dockerfile.runtime `
  --platform linux/amd64 `
  .
```

このコマンドはビルド コンテキストをアップロードし、Azure でビルドを実行して、イメージをワークショップ用 ACR にプッシュします。

---

## 3. イメージの確認

```powershell
$loginServer = az acr show `
  --resource-group $resourceGroup `
  --name $acrName `
  --query loginServer `
  --output tsv

az acr repository show-tags `
  --name $acrName `
  --repository $imageRepository `
  --output table

$fullImageName = "${loginServer}/${imageRepository}:${imageTag}"
Write-Host "Registry: $loginServer"
Write-Host "Image: $imageRepository"
Write-Host "Tag: $imageTag"
Write-Host "Full image: $fullImageName"
```

Container Apps はマネージド ID を使用してイメージをプルします。

---

## 4. 参加者へのワークショップ用 ACR アクセス権の付与

参加者は、Portal で Container App を作成するときに共有イメージを直接選択します。次のセクションで作成する共有ユーザー割り当てマネージド ID には `AcrPull` が付与され、ワークショップ用の各 Container Apps 環境に関連付けられます。

参加者ごとに、次の手順を実行します。

1. Azure Portal でワークショップ用 ACR を開きます。
2. **Access control (IAM)** → **+ Add role assignment** の順に選択します。
3. **Owner** を選択します。
4. **User, group, or service principal** を選択します。
5. 参加者のアカウントを選択し、割り当てを完了します。

> `Owner` は、参加者が Container App の作成時に共有 ACR イメージを参照して選択できるようにするための、ワークショップ向けの簡略化された設定です。通常の運用環境では、一般のアプリケーション ユーザーにこのような広範なロールを付与しないでください。

ワークショップでは、ACR の管理者ユーザーを有効にして運用します。

---

## 5. 共有 Container Apps 環境の作成

1 つの Container Apps 環境で、複数の参加者の Container Apps をホストできます。同じ環境内のアプリはネットワーク境界とログの保存先を共有しますが、各参加者は引き続き、自分のリソース グループ内で一意の名前を持つ MCP Toolkit Container App をデプロイして管理します。

最初に、共有ユーザー割り当てマネージド ID を作成し、ワークショップ用 ACR に対する `AcrPull` を付与します。

```powershell
$environmentIdentityName = "id-todomanagement-workshop-env"

az identity create `
  --name $environmentIdentityName `
  --resource-group $resourceGroup `
  --location $location

$environmentIdentityId = az identity show `
  --name $environmentIdentityName `
  --resource-group $resourceGroup `
  --query id `
  --output tsv

$environmentIdentityPrincipalId = az identity show `
  --name $environmentIdentityName `
  --resource-group $resourceGroup `
  --query principalId `
  --output tsv

$acrId = az acr show `
  --name $acrName `
  --resource-group $resourceGroup `
  --query id `
  --output tsv

az role assignment create `
  --assignee-object-id $environmentIdentityPrincipalId `
  --assignee-principal-type ServicePrincipal `
  --role AcrPull `
  --scope $acrId
```

このロールはワークショップ用 ACR のスコープに限定されており、参加者は割り当てられた環境で Container App を作成するときに共有イメージを直接選択できます。

このワークショップでは、**1 つの環境につき参加者を 8 人以下**にしてください。各参加者は、`0.5` vCPU、`1 GiB` メモリ、最大 1 レプリカの MCP Toolkit アプリを 1 つ構成します。8 つのアプリがすべて同時にアクティブになった場合、要求される CPU は約 `8 × 0.5 = 4` vCPU です。

Consumption の **4 vCPU / 8 GiB** という値は、個々のレプリカの最大サイズであり、Container Apps 環境全体のコンピューティング上限ではありません。そのため、参加者 8 人という数は Azure のハード制限ではなく、同時起動とテストを予測可能にするための、ワークショップにおける保守的な計画上の境界です。ワークショップの前に、必ず実際の環境クォータを確認してください。

式 `environmentCount = Ceiling(participantCount / 8)` を使用します。

たとえば、参加者が 8 人以下の場合は 1 つ、9 人から 16 人の場合は 2 つ、17 人から 24 人の場合は 3 つの環境を作成します。

同じ Cloud Shell PowerShell セッションで、環境を作成します。

```powershell
$participantCount = 24
$participantsPerEnvironment = 8
$environmentCount = [Math]::Ceiling($participantCount / $participantsPerEnvironment)
$environmentPrefix = "cae-todomanagement-workshop"

1..$environmentCount | ForEach-Object {
  $environmentName = "{0}-{1:D2}" -f $environmentPrefix, $_

  az containerapp env create `
    --name $environmentName `
    --resource-group $resourceGroup `
    --location $location

  az containerapp env identity assign `
    --name $environmentName `
    --resource-group $resourceGroup `
    --user-assigned $environmentIdentityId
}
```

すべての環境が準備できていることを確認します。

```powershell
az containerapp env list `
  --resource-group $resourceGroup `
  --query "[].{Name:name,State:properties.provisioningState,Location:location}" `
  --output table
```

各参加者に 1 つの環境と一意の Container App 名を割り当て、その対応関係を記録します。たとえば、参加者 1 から 8 は `cae-todomanagement-workshop-01` を使用し、アプリ名を `mcp-toolkit-p01` から `mcp-toolkit-p08` とします。参加者 9 から 16 は `cae-todomanagement-workshop-02` を使用し、アプリ名を `mcp-toolkit-p09` から `mcp-toolkit-p16` とします。

Container App 名は、共有環境内で一意である必要があります。すべての参加者に同じ汎用アプリ名を割り当てないでください。

参加者ごとに、次の手順を実行します。

1. Azure Portal で、参加者に割り当てた Container Apps 環境を開きます。
2. **Access control (IAM)** → **+ Add role assignment** の順に選択します。
3. **Container Apps Contributor** を選択します。
4. **User, group, or service principal** を選択します。
5. 参加者のアカウントを選択し、割り当てを完了します。

このロールは、講師のリソース グループのスコープではなく、対象となる Container Apps 環境のスコープで割り当てます。このロールには `Microsoft.App/managedEnvironments/join/action` が含まれるため、参加者は共有環境内に Container App を作成できますが、環境を変更または削除するアクセス許可は付与されません。また、参加者が割り当てられた Container App を自分のリソース グループに作成して管理するには、そのリソース グループに対する **Contributor** または **Owner** も必要です。

> 大規模なワークショップでは、環境ごとに Microsoft Entra セキュリティ グループを 1 つ作成し、割り当てた参加者をグループに追加して、その環境のスコープでグループに **Container Apps Contributor** を一度だけ付与します。

ワークショップの前に、各環境の現在のクォータと使用量を確認します。

```powershell
1..$environmentCount | ForEach-Object {
  $environmentName = "{0}-{1:D2}" -f $environmentPrefix, $_

  az containerapp env list-usages `
    --name $environmentName `
    --resource-group $resourceGroup `
    --output table
}
```

環境がアプリ数または Consumption コアのクォータに近づいている場合は、ワークショップの前に別の環境を作成し、参加者のグループをその環境に移動します。この一時的なラボでは共有環境が適していますが、ネットワーク、ログ、セキュリティ、または障害の分離が必要な場合は個別の環境を使用してください。

📖 参考資料: [Azure Container Apps 環境](https://learn.microsoft.com/azure/container-apps/environment)および [Container Apps のクォータ](https://learn.microsoft.com/azure/container-apps/quotas)

---

## 6. 参加者との値の共有

| 項目 | 値 |
| --- | --- |
| パブリック リポジトリ URL | `https://github.com/Liminghao0922/todomanagement_v2.git` |
| レジストリ | `<acr-name>.azurecr.io` |
| イメージ | `mcp-toolkit` |
| タグ | `workshop-YYYYMMDD` |
| Container Apps 環境 | 割り当てられた環境 (例: `cae-todomanagement-workshop-01`) |
| 環境のリソース グループ | `rg-todomanagement-instructor` |
| 環境のリージョン | `japaneast` |
| Container App 名 | 割り当てられた一意の名前 (例: `mcp-toolkit-p01`) |

参加者は Cloud Shell で `git clone` コマンドを 1 回実行します。GitHub アカウントを必要としないように、リポジトリは公開された状態を維持する必要があります。ワークショップの前に URL を確認し、別のリポジトリまたはブランチを使用する場合は更新してください。

参加者は、各自の Cosmos エンドポイント、Foundry エンドポイント、テナント ID、MCP クライアント ID を Azure Portal で構成します。これらの値は、いずれもイメージに組み込まれていません。

---

## 7. 講師によるドライ ラン

テスト用の参加者アカウントを使用して、ワークショップの前に日本語の [参加者ガイド](DEPLOY_GUIDE_GUI-ja_JP.md) を一度完了してください。

次の項目をすべて確認します。

- GitHub にサインインしなくても、Cloud Shell で `git clone` が動作すること。
- クローンしたリポジトリに `src/api` と `src/web` が含まれていること。
- Cloud Shell PowerShell で `az`、Python 3.11、Functions Core Tools v4、Node.js 20 が利用できること。
- `src/web` で `npm ci` と `npm run build` が成功すること。
- Cloud Shell PowerShell で `npx @azure/static-web-apps-cli@latest` が実行できること。
- テスト参加者が、ラボに必要な割り当て済み共有 Container Apps 環境のみを表示して選択できること。
- テスト参加者が、共有環境を変更せずに、自分のリソース グループ内に一意の名前を持つ Container App を作成できること。
- テスト参加者が、Container App の作成時に共有 ACR イメージを選択できること。
- MCP Container App がポート `8080` で正常なリビジョンに到達すること。
- Function App の正常性エンドポイントから `healthy` が返されること。
- Static Web Apps が `/api/*` をリンクされた Function App にプロキシすること。

---

## 8. ワークショップ前のチェックリスト

- [ ] ワークショップ用 ACR が存在する。
- [ ] ACR の管理者ユーザーが有効になっている。
- [ ] `mcp-toolkit` イメージのビルドが成功している。
- [ ] イメージ タグが記録されており、ワークショップ中に変更されない。
- [ ] 参加者への ACR ロールの割り当てが完了している。
- [ ] 共有ユーザー割り当て ID にワークショップ用 ACR の `AcrPull` が付与され、すべての Container Apps 環境に割り当てられている。
- [ ] 参加者数に対して十分な数の Container Apps 環境が存在する。
- [ ] すべての環境で `Succeeded` が報告され、十分なクォータがある。
- [ ] すべての参加者が環境に対応付けられ、一意の Container App 名を持ち、割り当てられた環境で **Container Apps Contributor** を付与されている。
- [ ] すべての参加者が自分のリソース グループにリソースを作成できる。
- [ ] GitHub アカウントがなくてもパブリック リポジトリをクローンできる。
- [ ] レジストリ、イメージ、タグ、割り当てられた環境、環境のリソース グループ、リージョン、一意の Container App 名、リポジトリ URL が参加者に共有されている。
- [ ] 参加者レベルのアカウントを使用した完全なドライ ランに合格している。

---

## トラブルシューティング

### ACR 名を使用できない場合

小文字の英字と数字のみを使用した、別のグローバルに一意の名前を選択します。

```powershell
az acr check-name --name "<new-acr-name>"
```

### リモート ビルドで発行済みアプリケーションが見つからない場合

最初に `dotnet publish` を実行し、想定される DLL が存在することを確認します。

```powershell
Test-Path src/AzureCosmosDB.MCP.Toolkit/bin/publish/AzureCosmosDB.MCP.Toolkit.dll
```

`az acr build` を実行する前に、結果が `True` になる必要があります。

### 参加者がイメージを選択またはプルできない場合

次の項目を確認します。

- レジストリ、リポジトリ、タグが正確であること。
- 参加者にワークショップ用 ACR のロールが割り当てられていること。
- ACR の管理者ユーザーが有効であること。
- Container App でシステム割り当てマネージド ID が有効になっていること。
- Container App の ID に講師用 ACR の `AcrPull` が付与されていること。
- ACR のパブリック ネットワーク設定で、ワークショップ環境からのアクセスが許可されていること。

### 新しいイメージが必要な場合

参加者と共有済みのタグを置き換えず、新しい不変タグを作成します。

```powershell
$imageTag = "workshop-$(Get-Date -Format yyyyMMdd-HHmm)"
az acr build `
  --registry $acrName `
  --image "${imageRepository}:${imageTag}" `
  --file Dockerfile.runtime `
  --platform linux/amd64 `
  .
```

ワークショップの開始前に、参加者向け資料を新しいタグで更新してください。
