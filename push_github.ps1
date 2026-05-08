# push_github.ps1
# Atualiza o dashboard com dados do banco e faz push para o GitHub.
# Chamado automaticamente pelo coletar.py ao final da coleta.

$PASTA = "C:\Users\Jason\Desktop\PROJETOS\02 - WORKING\MONITORAMENTE PRECO DIARIA"
Set-Location $PASTA

Write-Host "Atualizando dashboard..." -ForegroundColor Cyan
python atualizar_dashboard.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Erro ao atualizar dashboard." -ForegroundColor Red
    exit 1
}

$data = Get-Date -Format "yyyy-MM-dd HH:mm"
Write-Host "Enviando para o GitHub..." -ForegroundColor Cyan

git add index.html dados/log.txt
git commit -m "coleta $data"
git push origin main

Write-Host ""
Write-Host "OK - GitHub Pages atualizado em $data" -ForegroundColor Green
