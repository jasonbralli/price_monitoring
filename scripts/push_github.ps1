# push_github.ps1
# Atualiza o dashboard com dados do banco e faz push para o GitHub.
# Chamado automaticamente pelo coletar.py ao final da coleta.

# ─── Variáveis de ambiente ───────────────────────────────────────
# Prioridade: variável de ambiente > .env > valor padrão

function Get-EnvVar {
    param([string]$Name, [string]$Default)
    if ($env:$Name) { return $env:$Name }
    $envFile = $PSScriptRoot\.env
    if (Test-Path $envFile) {
        $content = Get-Content $envFile -Raw
        if ($content -match "^$Name=(.+)") { return $Matches[1].Trim() }
    }
    return $Default
}

$GIT_REPO_PATH = Get-EnvVar "GIT_REPO_PATH" $PSScriptRoot
$GITHUB_TOKEN  = Get-EnvVar "GITHUB_TOKEN" ""

Set-Location $GIT_REPO_PATH

Write-Host "Atualizando dashboard..." -ForegroundColor Cyan
python src/dashboard.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Erro ao atualizar dashboard." -ForegroundColor Red
    exit 1
}

$data = Get-Date -Format "yyyy-MM-dd HH:mm"
Write-Host "Enviando para o GitHub..." -ForegroundColor Cyan

# Adiciona e commita os arquivos
git add index.html dados/log.txt
git commit -m "coleta $data"

# Push para o GitHub
if ($GITHUB_TOKEN) {
    git push origin main --token $GITHUB_TOKEN
} else {
    git push origin main
}

Write-Host ""
Write-Host "OK - GitHub Pages atualizado em $data" -ForegroundColor Green
