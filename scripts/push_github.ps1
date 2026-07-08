# push_github.ps1
# Atualiza o dashboard com dados do banco e faz push para o GitHub.
# Chamado automaticamente pelo coletar.py ao final da coleta.

# ─── Variáveis de ambiente ───────────────────────────────────────
# Prioridade: variável de ambiente > .env > valor padrão

function Get-EnvVar {
    param([string]$Name, [string]$Default)
    try {
        $val = Get-Item -ErrorAction SilentlyContinue "env:\$Name"
        if ($null -ne $val) { return $val.Value }
    } catch {}
    $envFile = Join-Path $PSScriptRoot ".env"
    if (Test-Path $envFile) {
        $content = Get-Content $envFile -Raw
        if ($content -match "^$Name=(.+)") { return $Matches[1].Trim() }
    }
    return $Default
}

$GIT_REPO_PATH = Get-EnvVar "GIT_REPO_PATH" (Split-Path $PSScriptRoot -Parent)
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
git add dashboard/index.html dados/log.txt
git commit -m "coleta $data"

# Sincroniza com o remoto antes do push (evita conflitos)
git pull --rebase origin main
if ($LASTEXITCODE -ne 0) {
    # Tenta estagar mudanças não estagadas para continuar
    git stash --include-untracked 2>$null
    git pull --rebase origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Erro no rebase - resolva conflitos manualmente." -ForegroundColor Red
        exit 1
    }
    git stash pop
}

# Push para o GitHub
if ($GITHUB_TOKEN) {
    # Configura remote temporariamente com token para autenticação
    $remoteUrl = git remote get-url origin
    if ($remoteUrl -match '^https://') {
        $secureUrl = $remoteUrl -replace 'https://', "https://${GITHUB_TOKEN}@"
        git remote set-url origin $secureUrl
        git push origin main
        # Restaura remote sem token
        git remote set-url origin $remoteUrl
    } else {
        git push origin main
    }
} else {
    git push origin main
}

# Health check: verifica se o push foi aceito
$lastCommit = git rev-parse HEAD
$remoteCommit = git ls-remote origin main | ForEach-Object { ($_ -split '\t')[0] }
if ($lastCommit -eq $remoteCommit) {
    Write-Host ""
    Write-Host "OK - GitHub Pages atualizado em $data" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "AVISO: push pode nao ter sido aplicado. Verifique o repositrio." -ForegroundColor Yellow
}
