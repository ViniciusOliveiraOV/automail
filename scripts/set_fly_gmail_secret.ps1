<#
Usage: run this locally (NOT inside the Fly container). It reads the persisted
`instance/gmail_token.json` created by the app (or a file you provide), prompts
for an ADMIN_API_TOKEN, and sets both values as Fly secrets using `flyctl`.

Note: This script must be run from a machine where `flyctl` is installed and
you are authenticated (`flyctl auth login`).
#>
Param(
    [string]$TokenFilePath = "",
    [string]$AdminToken = ""
)

function Abort {
    param($msg)
    Write-Error $msg
    exit 1
}

# default token path is project-relative instance folder
if (-not $TokenFilePath -or $TokenFilePath -eq ""){
    $default = Join-Path -Path $PSScriptRoot -ChildPath "..\instance\gmail_token.json"
    $TokenFilePath = [System.IO.Path]::GetFullPath($default)
}

if (-not (Get-Command flyctl -ErrorAction SilentlyContinue)){
    Abort "flyctl not found in PATH. Install flyctl and run 'flyctl auth login' before running this script."
}

if (-not (Test-Path $TokenFilePath)){
    Write-Host "Token file not found at $TokenFilePath"
    $inputPath = Read-Host "Enter path to gmail_token.json (or press Enter to cancel)"
    if (-not $inputPath){ Abort "No token file provided, aborting." }
    if (-not (Test-Path $inputPath)){ Abort "Provided path does not exist: $inputPath" }
    $TokenFilePath = $inputPath
}

try{
    $tokenJson = Get-Content -Raw -Path $TokenFilePath
}catch{
    Abort "Failed to read token file: $_"
}

if (-not $AdminToken -or $AdminToken -eq ""){
    $secure = Read-Host -AsSecureString "Enter ADMIN_API_TOKEN to set on Fly (will be converted to plain text for secret)"
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try{
        $AdminToken = [Runtime.InteropServices.Marshal]::PtrToStringAuto($ptr)
    }finally{
        if ($ptr) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
    }
}

Write-Host "Setting Fly secrets (GMAIL_TOKEN_JSON and ADMIN_API_TOKEN). This will overwrite existing secrets with the same names." -ForegroundColor Yellow

# Prepare arguments for flyctl: each as KEY=VALUE; ensure JSON is single-line
$gmailTokenSingleLine = $tokenJson -replace "\r?\n", ""
$args = @("ADMIN_API_TOKEN=$AdminToken", "GMAIL_TOKEN_JSON=$gmailTokenSingleLine")
try{
    & flyctl secrets set @args
    if ($LASTEXITCODE -ne 0){ Abort "flyctl returned non-zero exit code ($LASTEXITCODE)" }
    Write-Host "Secrets set successfully." -ForegroundColor Green
}catch{
    Abort "Error running flyctl: $_"
}
