@echo off
REM Wrapper para Windows Task Scheduler
python "%~dp0coletar.py"

if errorlevel 1 (
    echo [ERRO] Script coletar.py falhou com codigo %errorlevel%
) else (
    echo [OK] Coleta concluida com sucesso!
)
