# configurar_agendador.ps1
# Configura o Agendador de Tarefas do Windows para rodar o monitor
# de preços diariamente ao ligar o PC.
#
# COMO USAR:
#   1. Edite as variáveis PYTHON_PATH e PROJETO_PATH abaixo
#   2. Abra o PowerShell como Administrador
#   3. Execute: .\configurar_agendador.ps1

# ─── Edite estes dois caminhos ────────────────────────────────────
$PYTHON_PATH  = "C:\Python312\python.exe"     # caminho do seu python.exe
$PROJETO_PATH = "C:\Users\SeuUsuario\peruibe_monitor\coletar.py"
# ──────────────────────────────────────────────────────────────────

$NOME_TAREFA  = "MonitorPrecosPetuibe"
$DESCRICAO    = "Coleta diária de preços de pousadas em Peruíbe via Google Hotels"

Write-Host ""
Write-Host "Configurando Agendador de Tarefas..." -ForegroundColor Cyan
Write-Host ""

# Remove tarefa antiga se existir
$existente = Get-ScheduledTask -TaskName $NOME_TAREFA -ErrorAction SilentlyContinue
if ($existente) {
    Unregister-ScheduledTask -TaskName $NOME_TAREFA -Confirm:$false
    Write-Host "Tarefa anterior removida." -ForegroundColor Yellow
}

# Define a ação: rodar python coletar.py
$acao = New-ScheduledTaskAction `
    -Execute $PYTHON_PATH `
    -Argument $PROJETO_PATH `
    -WorkingDirectory (Split-Path $PROJETO_PATH)

# Gatilho 1: todos os dias às 08:00
$gatilho_hora = New-ScheduledTaskTrigger -Daily -At "08:00"

# Gatilho 2: ao fazer login (cobre o caso de o PC estar desligado às 08h)
$gatilho_login = New-ScheduledTaskTrigger -AtLogOn

# Configurações: rodar mesmo se atrasado, não repetir se já estiver rodando
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

Write-Host "Tarefa '$NOME_TAREFA' criada com sucesso!" -ForegroundColor Green
Write-Host ""
Write-Host "Configuração:" -ForegroundColor White
Write-Host "  Python:  $PYTHON_PATH"
Write-Host "  Script:  $PROJETO_PATH"
Write-Host "  Horário: 08:00 diariamente (ou ao ligar o PC)"
Write-Host ""
Write-Host "Para verificar: Abra o Agendador de Tarefas e procure por '$NOME_TAREFA'"
Write-Host ""
