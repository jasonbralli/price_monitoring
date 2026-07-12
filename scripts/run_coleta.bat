@echo off
REM Wrapper para Windows Task Scheduler
REM Usa a venv do projeto para garantir dependências corretas
pushd "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] .venv\Scripts\python.exe nao encontrado. Crie a venv primeiro.
    popd
    pause
    exit /b 1
)
.venv\Scripts\python.exe scripts\coletar.py
set "RC=%ERRORLEVEL%"
popd
if %RC% neq 0 (
    echo [ERRO] Script coletar.py falhou com codigo %RC%
) else (
    echo [OK] Coleta concluida com sucesso!
)
