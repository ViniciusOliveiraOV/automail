<#
Inicia o servidor de desenvolvimento Flask após carregar variáveis de ambiente
do arquivo .env na raiz do projeto. É um wrapper de conveniência para que
você possa executar o servidor com LLM habilitado sem precisar exportar variáveis.

Uso: a partir da raiz do projeto (email-classifier-app):
    .\scripts\start_with_env.ps1
#>
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^(\s*#)|(^\s*$)') { return }
        if ($_ -match '^\s*([^=\s]+)\s*=\s*(.*)$$'){
            $k = $matches[1]
            $v = $matches[2]
            # remove surrounding quotes if present
            if ($v -match '^("|\')(.*)\1$$') { $v = $matches[2] }
            Write-Host "Setting $k"
            Set-Item -Path Env:\$k -Value $v
        }
    }
}

Write-Host "Iniciando Flask com variáveis do .env"
flask run --host=127.0.0.1 --port=5000
