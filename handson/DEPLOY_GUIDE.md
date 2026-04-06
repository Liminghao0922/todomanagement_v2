# Todo Management Deployment Guide

[English](DEPLOY_GUIDE.md) | [简体中文](DEPLOY_GUIDE-zh_CN.md) | [日本語](DEPLOY_GUIDE-ja_JP.md)

This document explains the full process, in English, from creating a repository from the GitHub template to deploying the application to Azure.

Estimated time: about 30 to 40 minutes.

---

## Prerequisites

- Azure subscription permissions: `Owner`, or `Contributor` plus `User Access Administrator`
- Permission in Microsoft Entra ID to create app registrations
- GitHub account
- Git installed
- Internet access

---

## Step 1. Create a Repository from the GitHub Template

### 1.1 Open the template repository

1. Open the following repository in GitHub, or use your own template repository:
	 - URL: `https://github.com/Liminghao0922/todomanagement`

### 1.2 Click "Use this template"

1. Click the **Use this template** button at the top-right of the repository page.
2. Select **Create a new repository**.
3. Fill in the repository details:
	 - **Repository name**: any name, for example `my-todo-app`
	 - **Description**: optional, for example `My Todo Management App`
	 - **Visibility**: choose `Public` or `Private`
	 - **Include all branches**: leave unchecked
4. Click **Create repository from template**.

---

## Step 2. Open Azure Cloud Shell (PowerShell)

### 2.1 Sign in to Azure Portal

1. Open `https://portal.azure.com`
2. Sign in with your Azure account

### 2.2 Start Cloud Shell

1. Click the **Cloud Shell** icon (`>_`) at the top of the Azure Portal.
2. Wait for the terminal to start.
3. Switch the shell to **PowerShell** if it opens in Bash mode.

### 2.3 Verify the subscription

```powershell
# Show the current subscription
az account show

# Switch to a different subscription if needed
az account set --subscription "<subscription-id>"
```

---

## Step 3. Download the Repository in Cloud Shell

### 3.1 Clone the repository

```powershell
# Clone the repository
git clone https://github.com/[your-username]/[your-repo-name].git
cd [your-repo-name]

# Confirm files are present
ls
# Expected output includes:
# src/
# infra/
# docs/
# README.md
```

### 3.2 Pull the latest changes if you already edited locally

If you already made local changes and pushed them before entering Cloud Shell, pull the latest version:

```powershell
git pull origin main
```

---

## Step 4. Review and Update Basic Settings

### 4.1 Review the parameter file

```powershell
# Review the parameter file
cat infra/parameters.json
```

Default `infra/parameters.json` content:

```json
	{
	"$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
	"contentVersion": "1.0.0.0",
	"parameters": {
		"location": {
			"value": "japaneast"
		},
		"environment": {
			"value": "dev"
		},
		"projectName": {
			"value": "todomanagement"
		},
		"postgresqlVersion": {
			"value": "17"
		},
		"postgresqlAdminUsername": {
			"value": "postgres"
		},
		"postgresqlAdminPassword": {
			"value": "Change@Me123!"
		},
		"vnetAddressPrefix": {
			"value": "10.0.0.0/16"
		},
		"postgresSubnetPrefix": {
			"value": "10.0.1.0/24"
		},
		"containerAppSubnetPrefix": {
			"value": "10.0.2.0/24"
		}
	}
}
```

### 4.2 Edit parameters in Cloud Shell if needed

```powershell
# Edit parameters.json in PowerShell
$json = Get-Content infra/parameters.json | ConvertFrom-Json
$json.parameters.location.value = "japaneast"
$json.parameters.environment.value = "handson"
$json.parameters.projectName.value = "mytodoapp001"
$json.parameters.postgresqlAdminPassword.value = "YourStrongPassword@123"
$json | ConvertTo-Json | Set-Content infra/parameters.json
```

Important values to review:

| Setting | Description | Example |
| --- | --- | --- |
| `location` | Azure region | `japaneast`, `eastus`, `westeurope` |
| `environment` | Environment identifier | `dev`, `staging`, `prod` |
| `projectName` | Resource name prefix | `myapp`, `mycompany-todo` |
| `postgresqlAdminPassword` | PostgreSQL admin password | `Str0ng@Password2024!` |

### 4.3 PostgreSQL password note

- `postgresqlAdminPassword` is required only when the PostgreSQL server is initially created.
- The application itself uses a user-assigned managed identity (UAI) for PostgreSQL access.
- The application does not use a stored runtime database password.
- The password should still meet strong password requirements.

---

## Step 5. Deploy the Infrastructure

### 5.1 Set local variables

```powershell
# Set variables
$resourceGroupName = "rg-todomanagement-dev"
$location = "japaneast"
```

### 5.2 Run the deployment script

```powershell
# Move to the infra directory
cd infra

# Run the PowerShell deployment script
# In local Windows PowerShell, you may need:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

.\deploy.ps1 -ResourceGroupName $resourceGroupName -Location $location
```

> In Azure Cloud Shell PowerShell, execution policy is already configured, so the script can usually run directly.

### 5.3 Record deployment outputs

When `deploy.ps1` completes, record the output values.

```powershell
# Sample output:
==========================================
Infrastructure Details
==========================================
PostgreSQL Server: postgres-todomanagement-4eg3h7exlf4p6
PostgreSQL Hostname: postgres-todomanagement-4eg3h7exlf4p6.postgres.database.azure.com
Container Registry Login Server: acrtodomanagement4eg3h7exlf4p6.azurecr.io
Container Registry Name: acrtodomanagement4eg3h7exlf4p6
Container App Environment: cae-todomanagement-dev
Database Name: tododb
API_URL: https://todomanagement-api.internal.calmhill-4a670c14.japaneast.azurecontainerapps.io
WEB_URL: https://todomanagement-web.calmhill-4a670c14.japaneast.azurecontainerapps.io

Web App Authentication:
	AZURE_CLIENT_ID: xxxxxxxx-1338-4d64-a90c-19ae2cc9eff9
	AZURE_TENANT_ID: xxxxxxxx-b5a9-466f-xxxx-d14b03f7ae76
User Assigned Identity:
	USER_ASSIGNED_IDENTITY_CLIENT_ID: xxxxxxxx-239e-4e1b-b759-5e601fcc4d8a
	USER_ASSIGNED_IDENTITY_RESOURCE_ID: /subscriptions/xxxxxxxx-c1ec-xxxx-9ee7-22103870844b/resourceGroups/rg-todomanagement-xxxxxxxx/providers/Microsoft.ManagedIdentity/userAssignedIdentities/uai-todomanagement-dev
	USER_ASSIGNED_IDENTITY_NAME: uai-todomanagement-dev

==========================================
Next Steps:
	1. Configure GitHub Actions for CI/CD


==========================================
Deployment Completed!
==========================================
```

---

## Step 6. Create a Service Principal and Azure Credentials for GitHub Actions

> Permission note:
> - This repository creates a Microsoft Graph `applications` resource in `infra/main.bicep`.
> - It also creates an Azure RBAC role assignment for ACR access.
> - Azure-side permissions therefore need to be `Owner`, or `Contributor` plus `User Access Administrator`.
> - The deploying identity must also be allowed to create app registrations in Microsoft Entra ID. If self-service app registration is disabled in the tenant, use an identity with `Application Administrator`, `Cloud Application Administrator`, or equivalent directory permissions.

### 6.1 Create the service principal in Cloud Shell

Run the following:

```powershell
# Set variables
$subscriptionId = $(az account show --query id -o tsv)
$spName = "github-todomanagement-ci"

# Create the service principal
$sp = az ad sp create-for-rbac `
	--name $spName `
	--role "Owner" `
	--scopes "/subscriptions/$subscriptionId/resourceGroups/$resourceGroupName" `
	--json-auth | ConvertFrom-Json

# Print JSON output for later use
$sp | ConvertTo-Json
```

### 6.2 Save the JSON output

Copy the output JSON and keep it for the next step:

```json
{
	"clientId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
	"clientSecret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
	"subscriptionId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
	"tenantId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
	...
}
```

---

## Step 7. Configure GitHub Secrets and Variables

### 7.1 Open the repository settings

1. Open your GitHub repository.
2. Click **Settings** -> **Secrets and variables** -> **Actions**.

![1775016195315](images/DEPLOY_GUIDE-ja_JP/1775016195315.png)

### 7.2 Add the secret

Click **New repository secret**.

Set:
- **Name**: `AZURE_CREDENTIALS`
- **Value**: paste the full JSON output from Step 6.1

```json
{
	"clientId": "...",
	"clientSecret": "...",
	"subscriptionId": "...",
	"tenantId": "...",
	...
}
```

Click **Add secret**.

![1775017571109](images/DEPLOY_GUIDE-ja_JP/1775017571109.png)

### 7.3 Add repository variables

Click **Settings** -> **Secrets and variables** -> **Actions** again, then add the following variables:

| Variable Name | Value | Description |
| --- | --- | --- |
| `ACR_NAME` | `acrtodomanagementxxxxx` | From deployment output |
| `RESOURCE_GROUP` | `rg-todomanagement-dev` | From deployment output |
| `CONTAINER_APP_ENVIRONMENT` | `cae-[projectName]-[environment]` | From `Container App Environment` output; used by workflow `--environment` |
| `POSTGRES_SERVER` | `postgres-todomanagement-xxxxx.postgres.database.azure.com` | PostgreSQL FQDN from deployment output |
| `DATABASE_TYPE` | `postgresql` | Force API to use PostgreSQL |
| `POSTGRES_DB` | `tododb` | Default database name |
| `POSTGRES_USER` | `uai-<project>-<env>` | Microsoft Entra ID / UAI principal name, not `postgres` |
| `AZURE_CLIENT_ID` | `[Microsoft Entra ID App ID]` | From Azure Portal |
| `AZURE_TENANT_ID` | `[Tenant ID]` | From Azure Portal |
| `AZURE_REDIRECT_URI` | `https://[web-app-url]` | Retrieve after deployment |
| `API_PROXY_TARGET` | `https://[api-app-url]` | Reverse proxy target from Web to internal API Container App |
| `USER_ASSIGNED_IDENTITY_CLIENT_ID` | `[UAI Client ID]` | From deployment output |
| `USER_ASSIGNED_IDENTITY_RESOURCE_ID` | `/subscriptions/.../userAssignedIdentities/...` | From deployment output; used by workflow `--registry-identity` |

Notes:

- Web Container App runtime only needs `API_PROXY_TARGET`.
- `CONTAINER_APP_ENVIRONMENT` is used by both API and Web workflows in `az containerapp up --environment`.
- `USER_ASSIGNED_IDENTITY_CLIENT_ID` is used by the API Container App to acquire PostgreSQL tokens with Microsoft Entra ID.
- `USER_ASSIGNED_IDENTITY_RESOURCE_ID` is used only during GitHub Actions deployment and is not needed inside the application container.

How to add them:

1. Open the **Variables** tab
2. Click **New repository variable**
3. Enter the variable name in **Name**
4. Enter the value in **Value**
5. Click **Add variable**

![1775016383501](images/DEPLOY_GUIDE-ja_JP/1775016383501.png)

---

## Step 8. Copy and Enable GitHub Actions Workflow Files

### 8.1 Copy workflow template files

In this template repository, CI/CD workflow files use the `.template` suffix. This prevents workflows from running automatically in the source template repository.

Run the following locally:

```bash
# Copy workflow files and remove the template suffix
cd ..
cp .github/workflows/build-deploy-web.yml.template .github/workflows/build-deploy-web.yml
cp .github/workflows/build-deploy-api.yml.template .github/workflows/build-deploy-api.yml

# Verify the copied files
ls -la .github/workflows/

# Expected output:
# build-deploy-web.yml
# build-deploy-web.yml.template
# build-deploy-api.yml
# build-deploy-api.yml.template
```

Windows PowerShell version:

```powershell
Copy-Item ".github/workflows/build-deploy-web.yml.template" ".github/workflows/build-deploy-web.yml"
Copy-Item ".github/workflows/build-deploy-api.yml.template" ".github/workflows/build-deploy-api.yml"

Get-ChildItem ".github/workflows/"
```

### 8.2 Why templates are used

- Prevent accidental workflow runs in the source template repository
- Make workflow activation an explicit user action
- Allow users to customize workflow files before committing them

---

## Step 9. Commit and Push Your Changes

### 9.1 Review local changes

Run locally:

```bash
# Review local changes
git status

# Example output:
# On branch main
# Changes not staged for commit:
#   modified: infra/parameters.json
```

### 9.2 Commit and push

```bash
# Stage the changes, including workflow files
git add .

# Commit
git commit -m "Enable GitHub Actions workflows and configure infrastructure parameters"

# Push to main
git push origin main
```

Check the result:

```bash
git log --oneline
```

---

## Step 10. Run and Monitor GitHub Actions

### 10.1 Open the Actions tab

1. Open the **Actions** tab in your GitHub repository.
2. Confirm the following workflows are shown:
	 - `Build and Deploy API to ACR`
	 - `Build and Deploy Web to ACR`

### 10.2 Wait for workflow completion

Expected triggers:

- A push to `main`
- Changes under `src/api/` or `.github/workflows/build-deploy-api.yml` trigger the API workflow
- Changes under `src/web/` or `.github/workflows/build-deploy-web.yml` trigger the Web workflow

### 10.3 Check workflow status

Verify these steps succeed:

- Checkout code
- Log in to Azure
- Build and push image to ACR
- Deploy to Container App

Typical runtime is about 5 to 10 minutes each for API and Web.

### 10.4 Troubleshoot failed runs

Common issues include:

- `AZURE_CREDENTIALS` is missing
- `RESOURCE_GROUP` is wrong
- `CONTAINER_APP_ENVIRONMENT` does not match the deployed environment

---

## Step 11. Access and Validate the Web Application

### 11.1 Get the web app URL

Run in Cloud Shell:

```powershell
az containerapp show `
	-n todomanagement-web `
	-g $resourceGroupName `
	--query "properties.configuration.ingress.fqdn" `
	-o tsv

# Example output:
# todomanagement-web.abc123def.japaneast.azurecontainerapps.io
```

Full URL:

```
https://todomanagement-web.abc123def.japaneast.azurecontainerapps.io
```

### 11.2 Open the application in a browser

1. Copy the URL above into your browser address bar
2. Press **Enter**
3. Confirm the Todo Management application loads

### 11.3 Validate functionality

- Click the **Login** button
- Sign in with Microsoft Entra ID
- Confirm the Todo list is shown
- Confirm you can create, edit, and delete Todo items

Enjoy the deployment.

Created: 2026-04-02
Version: 1.0
