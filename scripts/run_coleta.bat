@echo off
REM Wrapper para Windows Task Scheduler
REM Usa Python global para evitar venv/ambiente contaminado
pushd "%~dp0.."
set "PYTHONPATH="
set "PYTHONHOME="
if not exist "%PYVENV%" if not exist "C:\Users\Jason\AppData\Local\Programs\Python\Python313\python.exe" (
    echo [ERRO] Nem .venv nem Python 3.13 encontrados. Rode 'uv sync' na raiz do projeto.
    popd
    pause
    exit /b 1
)
set "PYVENV=%~dp0..\.venv\Scripts\python.exe"
if exist "%PYVENV%" (
    "%PYVENV%" scripts/coletar.py
) else (
    "C:\Users\Jason\AppData\Local\Programs\Python\Python313\python.exe" scripts/coletar.py
)
set "RC=%ERRORLEVEL%"
popd
if %RC% neq 0 (
    echo [ERRO] Script coletar.py falhou com codigo %RC%
) else (
    echo [OK] Coleta concluida com sucesso!
)
