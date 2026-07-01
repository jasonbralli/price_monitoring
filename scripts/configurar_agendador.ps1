# configurar_agendador.ps1
# Configura o Agendador de Tarefas do Windows para rodar a coleta
# automaticamente ao ligar o PC.
# 
# COMO USAR:
#   Abra o PowerShell como Administrador e execute:
#   .\configurar_agendador.ps1

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

$PYTHON_PATH  = Get-EnvVar "PYTHON_PATH"  "python"
$PROJETO_PATH = Get-EnvVar "PROJETO_PATH" $PSScriptRoot
$SCRIPT_PATH  = Join-Path $PROJETO_PATH "coletar.py"
$NOME_TAREFA  = "MonitorPrecosPeruibe"
$DESCRICAO    = "Coleta diaria de precos de pousadas em Peruibe + push GitHub Pages"

Write-Host ""
Write-Host "Configurando Agendador de Tarefas..." -ForegroundColor Cyan
Write-Host ""

# Validação
if (-not (Test-Path $PYTHON_PATH)) {
    Write-Host "⚠ Python não encontrado em: $PYTHON_PATH" -ForegroundColor Yellow
    Write-Host "  Verifique PYTHON_PATH ou adicione Python ao PATH" -ForegroundColor Yellow
}

if (-not (Test-Path $SCRIPT_PATH)) {
    Write-Host "⚠ Script coletar.py não encontrado em: $SCRIPT_PATH" -ForegroundColor Yellow
    Write-Host "  Verifique PROJETO_PATH" -ForegroundColor Yellow
}

# Remove tarefa antiga se existir
$existente = Get-ScheduledTask -TaskName $NOME_TAREFA -ErrorAction SilentlyContinue
if ($existente) {
    Unregister-ScheduledTask -TaskName $NOME_TAREFA -Confirm:$false
    Write-Host "Tarefa anterior removida." -ForegroundColor Yellow
}

# Acao: rodar python coletar.py
$acao = New-ScheduledTaskAction `
    -Execute $PYTHON_PATH `
    -Argument $SCRIPT_PATH `
    -WorkingDirectory $PROJETO_PATH

# Gatilho 1: todos os dias as 08:00
$gatilho_hora = New-ScheduledTaskTrigger -Daily -At "08:00"

# Gatilho 2: ao fazer login
# Cobre o caso do PC estar desligado as 08h
$gatilho_login = New-ScheduledTaskTrigger -AtLogOn

# Configuracoes
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -RunOnlyIfNetworkAvailable

# Registra a tarefa
Register-ScheduledTask `
    -TaskName    $NOME_TAREFA `
    -Description $DESCRICAO `
    -Action      $acao `
    -Trigger     @($gatilho_hora, $gatilho_login) `
    -Settings    $settings `
    -RunLevel    Limited | Out-Null

Write-Host "Tarefa '$NOME_TAREFA' criada!" -ForegroundColor Green
Write-Host ""
Write-Host "Configuracao:" -ForegroundColor White
Write-Host "  Python  : $PYTHON_PATH"
Write-Host "  Script  : $SCRIPT_PATH"
Write-Host "  Horario : 08:00 diariamente (ou ao ligar o PC)"
Write-Host ""
Write-Host "Para verificar: Abra o Agendador de Tarefas e procure 'MonitorPrecosPeruibe'"
Write-Host ""
