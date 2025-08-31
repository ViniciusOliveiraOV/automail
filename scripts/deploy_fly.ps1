# deploy_fly.ps1 - convenience script to create app on Fly.io and deploy using Docker
# Requirements:
#  - flyctl installed and authenticated
#  - Docker running locally

param(
    [string]$AppName = "",
    [string]$Org = "",
    [string]$Region = "",
    [switch]$ForceCreate
)

# helper: read .env and set secrets in Fly
function Set-FlySecretsFromEnv {
    param([string]$AppNameParam)

    $envFile = Join-Path (Get-Location) ".env"
    if (-not (Test-Path $envFile)) { Write-Host ".env not found."; return }
    $pairs = Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#\s][A-Za-z0-9_]+)\s*=\s*(.*)$') { $k=$matches[1]; $v=$matches[2].Trim(); "{0}={1}" -f $k, $v }
    } | Where-Object { $_ }
    if (-not $pairs) { Write-Host "No key=value pairs found in .env"; return }
    $pairs | ForEach-Object { Write-Host "Setting secret: $_" }
    # Set secrets one by one to avoid stdin/piping issues on some flyctl versions
    foreach ($p in $pairs) {
        Write-Host "flyctl secrets set $p -a $AppNameParam"
        flyctl secrets set $p -a $AppNameParam
    }
}

# ensure app name provided
if (-not $AppName) {
    Write-Host "Usage: .\scripts\deploy_fly.ps1 -AppName <your-app-name> [-Org <org>] [-Region <region>] [-ForceCreate]"
    exit 1
}

# optionally create the app
if ($ForceCreate) {
    $cmd = "flyctl apps create $AppName"
    if ($Org) { $cmd += " --organization $Org" }
    if ($Region) { $cmd += " --region $Region" }
    Write-Host "Creating app: $cmd"
    Invoke-Expression $cmd
}

# set secrets from .env
Set-FlySecretsFromEnv -AppNameParam $AppName

# deploy with Dockerfile (build and release)
Write-Host "Running: flyctl deploy -a $AppName"
flyctl deploy -a $AppName
