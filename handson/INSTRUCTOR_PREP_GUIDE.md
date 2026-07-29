# Instructor Preparation Guide

[English](INSTRUCTOR_PREP_GUIDE.md) | [简体中文](INSTRUCTOR_PREP_GUIDE-zh_CN.md) | [日本語](INSTRUCTOR_PREP_GUIDE-ja_JP.md)

[Participant guide](DEPLOY_GUIDE_GUI.md)

Use this guide before the workshop. Participants do not need GitHub accounts and do not build containers. The instructor prepares:

- A shared Azure Container Registry (ACR)
- A prebuilt Cosmos DB MCP Toolkit image
- Shared Container Apps environments for participant MCP Toolkit apps
- The Todo Management v2 public repository URL
- The image and environment values that participants need

The Todo application itself remains on Azure Functions and Azure Static Web Apps. The shared container image is only for the Cosmos DB MCP Toolkit.

Estimated preparation time: 30 to 45 minutes.

---

## Prerequisites

- An Azure subscription where you can create a resource group and ACR
- Permission to assign roles on the workshop ACR
- Permission to create Container Apps environments and assign roles on them
- Azure Cloud Shell access
- Access to this Todo Management v2 repository
- A list of participant accounts

> This guide uses `az acr build`. The container build runs in ACR, so Docker is not required in Cloud Shell.

---

## 1. Create the workshop ACR

Open **Azure Cloud Shell**, switch to **PowerShell**, and set values for the workshop:

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

ACR names must be globally unique, contain only lowercase letters and numbers, and be 5 to 50 characters long.

Create the resource group and registry:

```powershell
az group create `
  --name $resourceGroup `
  --location $location

az acr create `
  --resource-group $resourceGroup `
  --name $acrName `
  --sku Basic `
  --admin-enabled false
```

---

## 2. Build the MCP Toolkit image

The instructor may use GitHub during preparation. Participants do not run these commands.

```powershell
git clone https://github.com/AzureCosmosDB/MCPToolKit.git
Set-Location MCPToolKit
```

The runtime image expects prebuilt .NET output. Check that the .NET 9 SDK is available, then publish:

```powershell
dotnet --version
dotnet publish `
  src/AzureCosmosDB.MCP.Toolkit/AzureCosmosDB.MCP.Toolkit.csproj `
  --configuration Release `
  --output src/AzureCosmosDB.MCP.Toolkit/bin/publish
```

If `dotnet --version` does not report .NET 9, install the .NET 9 SDK in the instructor environment before continuing.

Run the remote ACR build from the MCP Toolkit repository root:

```powershell
az acr build `
  --registry $acrName `
  --image "${imageRepository}:${imageTag}" `
  --file Dockerfile.runtime `
  --platform linux/amd64 `
  .
```

The command uploads the build context, builds in Azure, and pushes the image to the workshop ACR.

---

## 3. Verify the image

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

Container Apps pull the image with managed identity.

---

## 4. Give participants workshop ACR access

Participants select the shared image directly while creating their Container App in the Portal. The shared user-assigned identity created in the next section has `AcrPull` and is attached to each workshop Container Apps environment.

For each participant:

1. Open the workshop ACR in the Azure Portal.
2. Select **Access control (IAM)** → **+ Add role assignment**.
3. Select **Owner**.
4. Select **User, group, or service principal**.
5. Select the participant account and complete the assignment.

> `Owner` is a workshop shortcut that lets participants browse and select the shared ACR image during Container App creation. Do not use this broad role for normal application users in production.

Keep the ACR admin user disabled.

---

## 5. Create shared Container Apps environments

A Container Apps environment can host multiple participant Container Apps. Apps in the same environment share its network boundary and logging destination, while each participant still deploys and manages a uniquely named MCP Toolkit Container App in their own resource group.

First, create a shared user-assigned managed identity and grant it `AcrPull` on the workshop ACR:

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

The role is scoped to the workshop ACR and allows participants to select the shared image directly when they create a Container App in an assigned environment.

For this workshop, plan for **no more than 8 participants per environment**. Each participant configures one MCP Toolkit app with `0.5` vCPU, `1 GiB` memory, and at most one replica. If all eight apps are active together, their requested CPU is approximately `8 × 0.5 = 4` vCPU.

The **4 vCPU / 8 GiB** Consumption value is the maximum size of an individual replica, not the total compute limit of a Container Apps environment. Eight participants is therefore a conservative workshop planning boundary for predictable concurrent startup and testing, not an Azure hard limit. Always verify the actual environment quota before the workshop.

Use the formula `environmentCount = Ceiling(participantCount / 8)`.

For example, create one environment for up to 8 participants, two for 9–16 participants, and three for 17–24 participants.

In the same Cloud Shell PowerShell session, create the environments:

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

Confirm that every environment is ready:

```powershell
az containerapp env list `
  --resource-group $resourceGroup `
  --query "[].{Name:name,State:properties.provisioningState,Location:location}" `
  --output table
```

Assign each participant to one environment and a unique Container App name, then record the mapping. For example, participants 1–8 use `cae-todomanagement-workshop-01` with app names `mcp-toolkit-p01` through `mcp-toolkit-p08`; participants 9–16 use `cae-todomanagement-workshop-02` with app names `mcp-toolkit-p09` through `mcp-toolkit-p16`.

Container App names must be unique within a shared environment. Do not assign the same generic app name to every participant.

For each participant:

1. Open their assigned Container Apps environment in the Azure Portal.
2. Select **Access control (IAM)** → **+ Add role assignment**.
3. Select **Container Apps Contributor**.
4. Select **User, group, or service principal**.
5. Select the participant account and complete the assignment.

Assign this role at the specific Container Apps environment scope, not at the instructor resource group scope. It includes `Microsoft.App/managedEnvironments/join/action`, which allows the participant to create a Container App in the shared environment, but it does not grant permission to modify or delete the environment. The participant must also have **Contributor** or **Owner** on their own resource group to create and manage their assigned Container App.

> For larger workshops, create one Microsoft Entra security group per environment, add the assigned participants to the group, and grant **Container Apps Contributor** to the group once at that environment's scope.

Before the workshop, check each environment's current quota and usage:

```powershell
1..$environmentCount | ForEach-Object {
  $environmentName = "{0}-{1:D2}" -f $environmentPrefix, $_

  az containerapp env list-usages `
    --name $environmentName `
    --resource-group $resourceGroup `
    --output table
}
```

If an environment approaches its app or consumption-core quota, create another environment and move a participant group to it before the workshop. Shared environments are appropriate for this temporary lab; use separate environments when network, logging, security, or failure isolation is required.

📖 References: [Azure Container Apps environments](https://learn.microsoft.com/azure/container-apps/environment) and [Container Apps quotas](https://learn.microsoft.com/azure/container-apps/quotas)

---

## 6. Share these values with participants

| Item                       | Value                                                               |
| -------------------------- | ------------------------------------------------------------------- |
| Public repository URL      | `https://github.com/Liminghao0922/todomanagement_v2.git`          |
| Registry                   | `<acr-name>.azurecr.io`                                           |
| Image                      | `mcp-toolkit`                                                     |
| Tag                        | `workshop-YYYYMMDD`                                               |
| Container Apps environment | Assigned environment, for example`cae-todomanagement-workshop-01` |
| Environment resource group | `rg-todomanagement-instructor`                                    |
| Environment region         | `japaneast`                                                       |
| Container App name         | Unique assigned name, for example`mcp-toolkit-p01`                |

Participants run one `git clone` command in Cloud Shell. The repository must remain publicly readable so they do not need GitHub accounts. Verify the URL before the workshop and update it if a different repository or branch is used.

Participants configure their own Cosmos endpoint, Foundry endpoint, tenant ID, and MCP client ID in the Azure Portal. None of those values are baked into the image.

---

## 7. Instructor dry run

Use a test participant account and complete the English [participant guide](DEPLOY_GUIDE_GUI.md) once before the workshop.

Confirm all of the following:

- `git clone` works in Cloud Shell without signing in to GitHub.
- The cloned repository contains `src/api` and `src/web`.
- `az`, Python 3.11, Functions Core Tools v4, and Node.js 20 are available in Cloud Shell PowerShell.
- `npm ci` and `npm run build` succeed for `src/web`.
- `npx @azure/static-web-apps-cli@latest` runs in Cloud Shell PowerShell.
- The test participant can see and select only the assigned shared Container Apps environment needed for the lab.
- The test participant can create their uniquely named Container App in their own resource group without modifying the shared environment.
- The test participant can select the shared ACR image while creating the Container App.
- The MCP Container App reaches a healthy revision on port `8080`.
- The Function App health endpoint returns `healthy`.
- Static Web Apps proxies `/api/*` to the linked Function App.

---

## 8. Pre-workshop checklist

- [ ] Workshop ACR exists.
- [ ] ACR admin user is disabled.
- [ ] `mcp-toolkit` image build succeeded.
- [ ] The image tag is recorded and will not change during the workshop.
- [ ] Participant ACR role assignments are complete.
- [ ] The shared user-assigned identity has `AcrPull` on the workshop ACR and is assigned to every Container Apps environment.
- [ ] Enough Container Apps environments exist for the participant count.
- [ ] Every environment reports `Succeeded` and has sufficient quota.
- [ ] Every participant is mapped to an environment, has a unique Container App name, and has **Container Apps Contributor** on the assigned environment.
- [ ] Every participant can create resources in their own resource group.
- [ ] The public repository can be cloned without a GitHub account.
- [ ] Registry, image, tag, assigned environment, environment resource group, region, unique Container App name, and repository URL are shared with participants.
- [ ] A full dry run has passed with a participant-level account.

---

## Troubleshooting

### ACR name is unavailable

Choose another globally unique name containing only lowercase letters and numbers:

```powershell
az acr check-name --name "<new-acr-name>"
```

### The remote build cannot find the published application

Run `dotnet publish` first and verify the expected DLL exists:

```powershell
Test-Path src/AzureCosmosDB.MCP.Toolkit/bin/publish/AzureCosmosDB.MCP.Toolkit.dll
```

The result must be `True` before `az acr build` runs.

### A participant cannot select or pull the image

Confirm:

- The registry, repository, and tag are exact.
- The participant has the workshop ACR role assignment.
- The Container App has system-assigned managed identity enabled.
- The Container App identity has `AcrPull` on the instructor ACR.
- The ACR public network setting permits access from the workshop environment.

### A new image is needed

Create a new immutable tag instead of replacing the tag already shared with participants:

```powershell
$imageTag = "workshop-$(Get-Date -Format yyyyMMdd-HHmm)"
az acr build `
  --registry $acrName `
  --image "${imageRepository}:${imageTag}" `
  --file Dockerfile.runtime `
  --platform linux/amd64 `
  .
```

Update the participant handout with the new tag before the workshop starts.
