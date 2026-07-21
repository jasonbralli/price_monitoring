@echo off
REM Wrapper para Windows Task Scheduler
REM Usa Python global para evitar venv/ambiente contaminado
pushd "%~dp0.."
set "PYTHONPATH="
set "PYTHONHOME="
if not exist "C:\Users\Jason\AppData\Local\Programs\Python\Python313\python.exe" (
    echo [ERRO] Python 3.13 nao encontrado. Ajuste o caminho no run_coleta.bat.
    popd
    pause
    exit /b 1
)
"C:\Users\Jason\AppData\Local\Programs\Python\Python313\python.exe" scripts/coletar.py
set "RC=%ERRORLEVEL%"
popd
if %RC% neq 0 (
    echo [ERRO] Script coletar.py falhou com codigo %RC%
) else (
    echo [OK] Coleta concluida com sucesso!
)
