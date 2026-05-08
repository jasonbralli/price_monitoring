# configurar_agendador.ps1
# Configura o Agendador de Tarefas do Windows para rodar a coleta
# automaticamente ao ligar o PC.
# 
# COMO USAR:
#   Abra o PowerShell como Administrador e execute:
#   .\configurar_agendador.ps1

$PYTHON_PATH  = "C:\Users\Jason\AppData\Local\Programs\Python\Python313\python.exe"
$PROJETO_PATH = "C:\Users\Jason\Desktop\PROJETOS\02 - WORKING\MONITORAMENTE PRECO DIARIA"
$SCRIPT_PATH  = "$PROJETO_PATH\coletar.py"
$NOME_TAREFA  = "MonitorPrecosPeruibe"
$DESCRICAO    = "Coleta diaria de precos de pousadas em Peruibe + push GitHub Pages"

Write-Host ""
Write-Host "Configurando Agendador de Tarefas..." -ForegroundColor Cyan
Write-Host ""

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
