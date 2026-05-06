# push_github.ps1
# Executa git add + commit + push após a coleta diária.
# O coletar.py chama este script automaticamente ao final.
# Pode também ser rodado manualmente.

$PASTA = "C:\Users\Jason\Desktop\PROJETOS\02 - WORKING\MONITORAMENTE PRECO DIARIA"

Set-Location $PASTA

$data = Get-Date -Format "yyyy-MM-dd HH:mm"

git add dados/precos.db dashboard.html
git commit -m "coleta diaria $data"
git push origin main

Write-Host ""
Write-Host "✓ GitHub atualizado — $data" -ForegroundColor Green
