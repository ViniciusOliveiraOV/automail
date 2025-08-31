#!/usr/bin/env pwsh
<#
PowerShell script para verificar se o backend responde em http://localhost:5000
Comportamento: tenta até 15 vezes com 1s de intervalo, retorna código 0 em sucesso ou 1 em falha.
Use: .\scripts\dev-health.ps1
#>

Param(
    [string]$Url = 'http://localhost:5000',
    [int]$Retries = 15,
    [int]$TimeoutSec = 2
)

Write-Host "Verificando saúde do backend em $Url ..."

for ($i = 0; $i -lt $Retries; $i++) {
    try {
        $resp = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 400) {
            Write-Host "backend OK"
            exit 0
        }
    } catch {
        # ignorar e tentar novamente
    }
    Start-Sleep -Seconds 1
}

Write-Host "backend UNHEALTHY"
exit 1
