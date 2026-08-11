param(
    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,

    [string]$AcrName = "",

    [string]$ImageRepository = "mcp-toolkit",

    [string]$ImageTag = "latest",

    [string]$SourceRepoUrl = "https://github.com/AzureCosmosDB/MCPToolKit.git",

    [string]$WorkDir = "",

    [switch]$SetAzdEnv
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($AcrName)) {
    Write-Host "[build-mcp-image] Resolving ACR in resource group '$ResourceGroupName'..." -ForegroundColor Cyan
    $acrNames = az acr list --resource-group $ResourceGroupName --query "[].name" --output tsv
    $acrList = @($acrNames -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })

    if ($acrList.Count -eq 0) {
        throw "No container registry found in '$ResourceGroupName'. Run 'azd provision' first, or pass -AcrName."
    }
    if ($acrList.Count -gt 1) {
        throw "Multiple registries found in '$ResourceGroupName' ($($acrList -join ', ')). Pass -AcrName explicitly."
    }

    $AcrName = $acrList[0]
}

Write-Host "[build-mcp-image] ACR: $AcrName" -ForegroundColor Cyan

$loginServer = az acr show --resource-group $ResourceGroupName --name $AcrName --query loginServer --output tsv
if ([string]::IsNullOrWhiteSpace($loginServer)) {
    throw "Could not read login server for ACR '$AcrName'."
}

if ([string]::IsNullOrWhiteSpace($WorkDir)) {
    $WorkDir = Join-Path ([System.IO.Path]::GetTempPath()) ("mcptoolkit-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
}

$sourceRoot = $WorkDir
if (Test-Path (Join-Path $WorkDir "Dockerfile.runtime")) {
    Write-Host "[build-mcp-image] Reusing existing source at $WorkDir" -ForegroundColor Cyan
}
else {
    Write-Host "[build-mcp-image] Cloning $SourceRepoUrl ..." -ForegroundColor Yellow
    git clone --depth 1 $SourceRepoUrl $WorkDir
    if ($LASTEXITCODE -ne 0) {
        throw "git clone failed. Ensure git is installed and the source URL is reachable."
    }
}

Push-Location $sourceRoot
try {
    Write-Host "[build-mcp-image] Publishing .NET output..." -ForegroundColor Yellow
    dotnet publish `
        src/AzureCosmosDB.MCP.Toolkit/AzureCosmosDB.MCP.Toolkit.csproj `
        --configuration Release `
        --output src/AzureCosmosDB.MCP.Toolkit/bin/publish
    if ($LASTEXITCODE -ne 0) {
        throw "dotnet publish failed. Install the .NET 9 SDK and retry."
    }

    Write-Host "[build-mcp-image] Running remote ACR build..." -ForegroundColor Yellow
    az acr build `
        --registry $AcrName `
        --image "${ImageRepository}:${ImageTag}" `
        --file Dockerfile.runtime `
        --platform linux/amd64 `
        .
    if ($LASTEXITCODE -ne 0) {
        throw "az acr build failed."
    }
}
finally {
    Pop-Location
}

$fullImage = "${loginServer}/${ImageRepository}:${ImageTag}"
Write-Host "[build-mcp-image] Image pushed: $fullImage" -ForegroundColor Green

if ($SetAzdEnv) {
    Write-Host "[build-mcp-image] Updating azd environment values..." -ForegroundColor Yellow
    azd env set COSMOS_MCP_IMAGE_REPOSITORY $ImageRepository
    azd env set COSMOS_MCP_IMAGE_TAG $ImageTag
    azd env set COSMOS_MCP_ACR_NAME $AcrName
    Write-Host "[build-mcp-image] azd env updated. Run 'azd provision' to roll out the Container App." -ForegroundColor Green
}
else {
    Write-Host "[build-mcp-image] Next: set azd env values (or pass -SetAzdEnv) and run 'azd provision'." -ForegroundColor Cyan
}
