# Instructor Prep Guide (Foundry Focus, Beginner Track)

[English](INSTRUCTOR_PREP_GUIDE_FOUNDRY_FOCUS.md) | [简体中文](INSTRUCTOR_PREP_GUIDE_FOUNDRY_FOCUS-zh_CN.md) | [日本語](INSTRUCTOR_PREP_GUIDE_FOUNDRY_FOCUS-ja_JP.md)

[Participant guide](DEPLOY_GUIDE_GUI_FOUNDRY_FOCUS.md)

This guide defines the instructor-owned setup for a beginner-friendly Todo Management v2 workshop. The instructor completes deployment, sign-in access, and shared Container Apps environment preparation before class. Participants create their own Foundry resource, project, and embedding deployment before building the Cosmos DB MCP tool and Prompt agent.

Instructor prep has three main parts:

1. Deploy the complete Todo app with `azd`.
2. Configure participant permission to sign in to the Todo app.
3. Prepare subscription access, provider registration, and model quota for participant-owned Foundry resources.
4. Prepare shared Container Apps environments for participant Cosmos DB MCP deployments.

Estimated instructor prep time: 90-150 minutes for the first run, 45-60 minutes after the flow is familiar.

---

## 0. What This Version Assumes

This Foundry Focus track assumes:

- Participants do not run infrastructure deployment commands.
- Participants may still create their own Cosmos DB MCP Container App during the lab, but the instructor prepares the shared Container Apps environment and image access in advance.
- The Todo app itself is deployed by the instructor with `azd up`.
- Each participant creates a uniquely named Foundry resource, project, embedding deployment, MCP connection, and Prompt agent.

This repository now includes the minimum `azd` support needed for this track:

- [../azure.yaml](../azure.yaml)
- [../infra/main.parameters.json](../infra/main.parameters.json)
- [../infra/azd-postprovision.ps1](../infra/azd-postprovision.ps1)

The `azd` flow provisions the Bicep infrastructure and then runs a post-provision hook that publishes the Functions API, builds/deploys the Static Web App, links SWA to Functions, and validates health endpoints.

---

## 1. Instructor Prerequisites

Run these checks from the instructor workstation or Azure Cloud Shell PowerShell.

```powershell
azd version
az version
func --version
python --version
node --version
npm --version
```

Required versions:

| Tool                       | Expected                   |
| -------------------------- | -------------------------- |
| Azure Developer CLI        | `azd` installed          |
| Azure CLI                  | Logged in to target tenant |
| Azure Functions Core Tools | v4                         |
| Python                     | 3.11+                      |
| Node.js                    | 20+                        |
| npm                        | Available                  |

Required instructor permissions:

- Contributor or Owner on the Azure subscription/resource group.
- Permission to create Microsoft Entra app registrations.
- Permission to grant app consent or assign Enterprise Application users/groups.
- Permission to create Azure Container Registry and Container Apps environments.
- Permission to create and configure Foundry resources, projects, models, and agents.

Recommended participant account preparation:

- Create or identify a Microsoft Entra security group for workshop participants.
- Add all participants to that group before class.
- Use the group for Todo app sign-in assignment and shared Container Apps environment access.

---

## 2. Deploy The Complete Todo App With azd

### 2.1 Sign In And Create azd Environment

In Azure Cloud Shell PowerShell, clone the repository first, then move into the cloned folder:

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

Use `japaneast` for the main workload resources and `eastasia` for Static Web Apps. `Microsoft.Web/staticSites` is not available in Japan East.

Success criteria:

- `azd env get-values` shows the subscription, location, and resource group values.
- The active Azure account is in the expected tenant.

Validate:

```powershell
azd env get-values
az account show --output table
```

### 2.2 Preview Provisioning

Before creating resources, run a preview.

```powershell
azd provision --preview
```

Review that the preview includes the expected `Create` resources. The current test environment (`environment=todomangementv2`) shows entries similar to the following:

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

If you use different `projectName`, `environment`, or resource group, the suffix part will differ. The resource shape should include the Todo application resources, two Cosmos accounts, and the Cosmos DB MCP Toolkit resources.

Naming rules in this guide are aligned to the current Bicep template:

- `<suffix>` = `uniqueString(resourceGroup().id)`.
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

The exact list may vary if some resources already exist or are reported as child/no-change resources. Confirm the Function App, app registration, endpoints, and IDs from the deployment outputs after `azd up`.

If the preview shows an unexpected subscription, region, or resource group, stop and fix the azd environment values before continuing.

### 2.3 Run Full Deployment

Run:

```powershell
azd up
```

What `azd up` does in this repository:

1. Provisions infrastructure from [../infra/main.bicep](../infra/main.bicep).
2. Runs [../infra/azd-postprovision.ps1](../infra/azd-postprovision.ps1) to configure Entra, RBAC, Cosmos permissions, and the Foundry RemoteTool connection.
3. Runs `azd deploy`, whose postdeploy entry point is [../infra/azd-deploy.ps1](../infra/azd-deploy.ps1).
4. Builds and activates the Cosmos MCP Toolkit image, then creates or updates the Foundry Agent.
5. Publishes the Python Functions API and builds/deploys the Vue Static Web App.
6. Attempts to link Static Web App production APIs to the Function App.
7. Validates `/api/health` on the Function App and Static Web App route.

To run the phases separately, use `azd provision` for infrastructure and `azd deploy` for application components.

Expected output from the provision and deploy hooks includes:

- Todo app URL
- Function URL
- Foundry resource name
- Foundry project name
- Foundry project endpoint
- Entra App Registration client ID
- Tenant ID

Success criteria:

- `azd up` completes without failed provisioning.
- Function health endpoint returns `healthy`.
- Todo app URL opens in a browser.
- Static Web App `/api/health` returns `healthy`, or the script warns you to finish the SWA API link manually.

### 2.4 Manual Fix If SWA API Link Fails

If the hook prints a warning for the API link, complete this in the Azure Portal:

1. Open the Static Web App.
2. Go to **Settings** -> **APIs**.
3. In the **Production** row, select **Link**.
4. Set:
   - Backend resource type: **Function App**
   - Subscription: workshop subscription
   - Resource name: deployed Function App
   - Backend slot: **Production**
5. Select **Link**.

Validate:

```powershell
$todoAppUrl = "<static-web-app-url-from-azd-output>"
Invoke-RestMethod "$todoAppUrl/api/health"
```

Expected result:

```json
{
  "status": "healthy",
  "service": "Todo Management Functions API"
}
```

---

## 3. Record Deployment Values

After `azd up`, collect values for later setup and participant handouts.

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

Success criteria:

- [foundry-focus-class-values.json](foundry-focus-class-values.json) is created under [handson](.) or copied to the instructor-only handout.
- Values are non-empty.

Do not share secrets or deployment tokens with participants.

---

## 4. Configure Participant Login Permission For Todo App

The Bicep deployment creates the SPA app registration. The instructor must make sure participants can sign in to the deployed Todo app.

### 4.1 Verify Redirect URIs

In Microsoft Entra admin center:

1. Open **Microsoft Entra ID** -> **App registrations**.
2. Search by the Application (client) ID from `$clientId`.
3. Open **Authentication**.
4. Confirm these SPA redirect URIs exist:
   - `$staticWebAppUrl`
   - `$staticWebAppUrl/`
   - `http://localhost:5173`
   - `http://localhost:5173/`

If only the trailing-slash values exist, add the non-trailing-slash values too.

Success criteria:

- A test participant can complete sign-in without redirect URI mismatch errors.

### 4.2 Grant Or Confirm API Consent

In the same app registration:

1. Open **API permissions**.
2. Confirm Microsoft Graph delegated permissions required by the app, such as `User.Read` and calendar-related permissions if the calendar scenario is enabled.
3. Select **Grant admin consent** if your tenant does not allow user consent.

Success criteria:

- No consent prompt blocks participant sign-in.
- A test participant can sign in from the deployed Todo app URL.

### 4.3 Assign Participants To The Enterprise Application

Use this if you want to control who can access the Todo app.

1. Open **Microsoft Entra ID** -> **Enterprise applications**.
2. Search for the app registration display name created by deployment, or search by Application ID `$clientId`.
3. Open **Properties**.
4. Set **Assignment required?** to **Yes**.
5. Open **Users and groups** -> **+ Add user/group**.
6. Add the workshop participant security group or individual participant accounts.

If you leave **Assignment required?** as **No**, users in the tenant can sign in as long as consent and redirect URIs are correct. For classroom control, assignment-required with a participant group is recommended.

Success criteria:

- Assigned participant account can sign in.
- Unassigned account cannot access the app if Assignment required is enabled.

### 4.4 Participant Login Smoke Test

Use a participant-level test account.

1. Open `$staticWebAppUrl` in a private browser window.
2. Sign in.
3. Confirm **Todos** and **Projects** pages load.
4. Select **Generate 50 Test Todos** once to seed class data, or seed data with the instructor account before class.

Success criteria:

- Participant can sign in.
- Todo data loads.
- No `AADSTS` redirect/consent/assignment error appears.

---

## 5. Prepare Container Apps Environments For Participant Cosmos DB MCP Deployments

This section follows the concrete setup pattern from the original instructor guide: [INSTRUCTOR_PREP_GUIDE.md](INSTRUCTOR_PREP_GUIDE.md). The goal is to let participants deploy their own Cosmos DB MCP Container App without creating a Container Apps environment or building the MCP image.

Participants should receive an already-built image, an assigned Container Apps environment, and a unique Container App name.

### 5.1 Verify And Reuse The azd-Deployed ACR Image

Do not create another ACR or build the MCP Toolkit image manually. The `azd up` flow already:

1. Creates the workshop ACR.
2. Builds `mcp-toolkit:<tag>` in that ACR.
3. Activates the image on the instructor MCP Container App.

Use the values recorded in section 3:

| Value      | Source                        |
| ---------- | ----------------------------- |
| Registry   | `$cosmosMcpAcrLoginServer`  |
| Repository | `$cosmosMcpImageRepository` |
| Tag        | `$cosmosMcpImageTag`        |
| Full image | `$cosmosMcpImage`           |

The ACR Admin user remains disabled. Each workshop Container Apps environment uses its own system-assigned managed identity and receives `AcrPull` on this ACR. Participants select the environment system identity for registry authentication when creating their Container App.

Validate the existing image:

```powershell
az acr repository show-tags `
  --name $cosmosMcpAcrName `
  --repository $cosmosMcpImageRepository `
  --output table
```

Success criteria:

- `az acr repository show-tags` shows `$cosmosMcpImageTag`.
- The instructor can select the image from Portal when creating a test Container App.

### 5.2 Create Shared Container Apps Environments

Enable a system-assigned identity on each shared Container Apps environment and grant that identity `AcrPull` on the workshop ACR. This environment identity is only for pulling the shared image. Each participant Container App separately enables its own system-assigned identity for Cosmos DB and Foundry runtime access.

Recommended sizing:

- No more than 8 participants per Container Apps environment.
- One participant gets one unique Container App name.
- Use multiple environments for larger classes.
- Each participant MCP app should use `0.5` vCPU, `1 GiB` memory, and at most one replica.

Use `environmentCount = Ceiling(participantCount / 8)`. Create each environment with a system-assigned identity. These commands use Azure Resource Manager directly and do not require the Azure CLI `containerapp` extension:

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

After every environment reports `Succeeded` and a non-empty `identity.principalId`, grant each environment system identity `AcrPull`:

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

The PUT response can initially report `Waiting`. After Azure finishes provisioning, confirm that every environment is ready and has a system-assigned identity:

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

Example mapping:

| Participant range | Environment                        | Container App names                        |
| ----------------- | ---------------------------------- | ------------------------------------------ |
| 1-8               | `cae-todomanagement-workshop-01` | `mcp-toolkit-p01` to `mcp-toolkit-p08` |
| 9-16              | `cae-todomanagement-workshop-02` | `mcp-toolkit-p09` to `mcp-toolkit-p16` |

Container App names must be unique within a shared environment. Record one assigned environment and one unique Container App name for each participant.

Check quota and current usage before class:

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

If an environment approaches its app or consumption-core quota, create another environment and move a participant group to it before class.

Success criteria:

- Every environment reports `Succeeded`.
- Every environment reports `identity.type` as `SystemAssigned` and has a non-empty `identity.principalId`.
- Every environment system identity has `AcrPull` on the workshop ACR.
- Environment usage/quota is checked before class.
- Participants can create a Container App in only their assigned environment.

### 5.3 Grant Participant Access

For each participant or participant group, grant:

| Scope                               | Role                       | Why                                                                             |
| ----------------------------------- | -------------------------- | ------------------------------------------------------------------------------- |
| Workshop ACR                        | Owner                      | Lets participants browse/select the shared image in Portal for this lab flow    |
| Assigned Container Apps environment | Container Apps Contributor | Lets participants create their MCP Container App in the pre-created environment |
| Participant resource group          | Owner or Contributor       | Lets participants create their assigned Container App resource                  |
| Shared Cosmos DB account            | DocumentDB Account Contributor | Lets participants create the Cosmos DB SQL data-plane role assignment for their Container App identity |

These broad permissions are acceptable for a temporary training lab but should not be reused as production guidance.

Each participant enables a system-assigned identity after creating their Container App. Unless participants have role-assignment permission on the shared resources, the instructor must then complete these assignments during the lab:

- `Cosmos DB Account Reader Role` and `Cosmos DB Built-in Data Reader` on the shared Cosmos account to that identity.
- `Foundry User` on the participant's Foundry resource to that identity.
- `MCP Tool Executor` on the participant's Enterprise Application to the Foundry project managed identity.

The participant Container App does not need `AcrPull` on its system identity because the Container Apps environment system identity is used for registry authentication.

Participants also need permission to create an app registration. If they cannot assign users or managed identities to Enterprise Application roles, the instructor performs those assignments.

`DocumentDB Account Contributor` is assigned to the participant account or participant group. Do not assign it to the Container App identity. The Container App identity receives only the runtime roles listed above.

Success criteria:

- Test participant can select only the assigned Container Apps environment.
- Test participant can select the assigned environment's system identity for registry authentication.
- Test participant can select the workshop ACR image.
- Test participant can create a uniquely named Container App without creating a new environment.
- Test participant can run `az cosmosdb sql role assignment create` against the shared Cosmos DB account.

### 5.4 Values To Give Each Participant

Prepare a per-participant handout table:

| Item                                | Example                                                   |
| ----------------------------------- | --------------------------------------------------------- |
| Todo app URL                        | `$staticWebAppUrl`                                      |
| Foundry region                      | `$location`                                             |
| Registry                            | `$cosmosMcpAcrLoginServer`                              |
| Image                               | `$cosmosMcpImageRepository`                             |
| Tag                                 | `$cosmosMcpImageTag`                                    |
| Assigned Container Apps environment | `cae-todomanagement-workshop-01`                        |
| Environment resource group          | `rg-todomanagement-instructor`                          |
| Environment region                  | `japaneast`                                             |
| Environment identity principal ID   | System identity principal ID for the assigned environment |
| Unique Container App name           | `mcp-toolkit-p01`                                       |
| Participant ID                      | `p01`                                                   |
| Cosmos endpoint                     | `$cosmosEndpoint`                                       |
| Cosmos account name                 | `$cosmosAccountName`                                    |
| Cosmos resource group               | `$resourceGroup`                                        |
| Cosmos resource ID                  | `$cosmosAccountId`                                      |
| Tenant ID                           | `$tenantId`                                             |

Do not give participants deployment tokens, app secrets, ACR passwords, or instructor credentials.

---

## 6. Foundry Preparation Before Class

The participant lab creates participant-specific Foundry resources, projects, and model deployments. Prepare subscription access, model availability, and quota before class.

1. Keep the Bicep-created Foundry resource, `proj-todomanagement` project, and model deployments for the instructor-owned Todo application.
2. Confirm `Microsoft.CognitiveServices` is registered in the workshop subscription.
3. Confirm each participant has Contributor or Owner access on their participant resource group.
4. Confirm `text-embedding-3-small` and `gpt-5.4-mini` are available in the instructor-provided Foundry region.
5. Confirm sufficient model quota exists for all participant deployments.
6. Test with a participant account that it can create `aifoundry-todomanagement-p01`, create `proj-todomanagement-p01`, and deploy `text-embedding-3-small-p01`.
7. Confirm the participant can deploy `gpt-5.4-mini` after deploying `text-embedding-3-small` and before creating the MCP Container App.
8. Delete the test Foundry resource, or reserve it for the instructor dry run.

After the agent exists, update Function App settings so the Todo app Copilot panel can call the agent:

```powershell
$foundryProjectEndpoint = "<foundry-project-endpoint-from-azd-output>"
$foundryAgentName = "todomanagement-agent"
$foundryAgentVersion = "<agent-version>"

az functionapp config appsettings set `
  --resource-group $resourceGroup `
  --name $functionAppName `
  --settings `
    FOUNDRY_PROJECT_ENDPOINT=$foundryProjectEndpoint `
    FOUNDRY_AGENT_ENDPOINT=$foundryProjectEndpoint `
    FOUNDRY_AGENT_NAME=$foundryAgentName `
    FOUNDRY_AGENT_VERSION=$foundryAgentVersion

az functionapp restart --resource-group $resourceGroup --name $functionAppName
```

Success criteria:

- Foundry Playground prompt `List all databases in my Cosmos DB account.` returns `todo-db`.
- Todo app Copilot panel returns an answer for `What should I prioritize today?`.

---

## 7. Final Instructor Dry Run

Use a test participant account.

### Todo App

1. Open `$staticWebAppUrl`.
2. Sign in.
3. Open **Todos**.
4. Confirm generated data exists.
5. Open **Projects** -> **View Graph**.
6. Ask Copilot: `What should I prioritize today?`

### Participant MCP Setup

1. Create one test Container App using the participant instructions.
2. Use the assigned shared Container Apps environment.
3. Select the workshop ACR image.
4. Configure the required environment variables.
5. Open the MCP test UI.
6. Sign in and invoke `List Databases`.
7. Invoke `Vector Search` against `todo-db/todos` with search text `adoption-plan`.
8. Confirm `OPENAI_ENDPOINT` uses the participant resource's `https://<resource>.openai.azure.com/` endpoint and the embedding call succeeds without `401 Unauthorized`.

### Foundry

1. Create a participant-specific Foundry resource and project.
2. Deploy a participant-specific `text-embedding-3-small` deployment.
3. Deploy `gpt-5.4-mini` if it is not yet available in that resource.
4. Create the Prompt agent and MCP connection in that project.
5. Ask: `List containers in database todo-db.`
6. Open Trace.
7. Confirm the Cosmos DB tool call is visible.

Dry run passes only when all three areas succeed.

---

## 8. Classroom Run Plan

| Time      | Activity                                                                    | Owner             |
| --------- | --------------------------------------------------------------------------- | ----------------- |
| 0-10 min  | Explain architecture and prepared resources                                 | Instructor        |
| 10-30 min | Participants create a Foundry resource, project, and embedding deployment   | Participants      |
| 30-55 min | Participants deploy/use Cosmos DB MCP Container App in prepared environment | Participants      |
| 55-75 min | Participants create a Prompt agent and connect the Cosmos DB MCP tool       | Instructor-guided |
| 75-85 min | Trace reading exercise                                                      | Participants      |
| 85-90 min | Prompt tuning and wrap-up                                                   | Participants      |

---

## 9. Failure Handling

| Symptom                                              | Instructor action                                                              |
| ---------------------------------------------------- | ------------------------------------------------------------------------------ |
| `azd up` fails during provisioning                 | Fix infra before class; do not debug live with participants                    |
| SWA API link fails                                   | Manually link Static Web App -> APIs -> Function App                           |
| Participant cannot sign in                           | Check Enterprise Application assignment, consent, and redirect URIs            |
| Participant cannot select ACR image                  | Check ACR Owner assignment and Admin user setting                              |
| Participant cannot select Container Apps environment | Check Container Apps Contributor assignment at environment scope               |
| MCP tool cannot list databases                       | Check Cosmos endpoint, managed identity/app role, and tenant/client ID         |
| Foundry tool call fails                              | Use prepared backup agent or pre-captured trace and continue the teaching flow |

Keep at least one known-good test participant account and one known-good MCP Container App ready before class.
