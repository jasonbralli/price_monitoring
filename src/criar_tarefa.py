"""
criar_tarefa.py — Cria a tarefa agendada no Windows via Python.
Nao requer PowerShell assinado nem permissao de administrador.
Execute uma unica vez:  python criar_tarefa.py
"""

import os
import subprocess
from pathlib import Path

# ─── Variáveis de ambiente ───────────────────────────────────────
# Prioridade: variável de ambiente > .env > valor padrão

def get_env_var(name, default):
    """Retorna variável de ambiente ou lê de .env, ou retorna default."""
    val = os.environ.get(name)
    if val:
        return val
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        content = env_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                if key.strip() == name:
                    return value.strip().strip('"').strip("'")
    return default

PYTHON  = get_env_var("PYTHON_PATH", "python")
PROJETO = get_env_var("PROJETO_PATH", str(Path(__file__).parent.parent))
SCRIPT  = Path(PROJETO) / "coletar.py"
TAREFA  = "MonitorPrecosPeruibe"

# Validação
if not Path(SCRIPT).exists():
    print(f"⚠ Script coletar.py não encontrado em: {SCRIPT}")
    print("  Verifique PROJETO_PATH ou PYTHON_PATH")
    exit(1)

# XML que define a tarefa — dois gatilhos: 08:00 diario + ao fazer login
XML = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Coleta diaria de precos de pousadas em Peruibe + push GitHub Pages</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T08:00:00</StartBoundary>
      <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{PYTHON}</Command>
      <Arguments>"{SCRIPT}"</Arguments>
      <WorkingDirectory>{PROJETO}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

# Salva o XML temporariamente
xml_path = Path(PROJETO) / "tarefa_temp.xml"
xml_path.write_text(XML, encoding="utf-16")

# Deleta tarefa antiga se existir
subprocess.run(["schtasks", "/delete", "/tn", TAREFA, "/f"],
               capture_output=True)

# Cria a tarefa via schtasks (nao precisa de admin)
result = subprocess.run(
    ["schtasks", "/create", "/tn", TAREFA, "/xml", str(xml_path)],
    capture_output=True, text=True
)

# Remove o XML temporario
xml_path.unlink(missing_ok=True)

if result.returncode == 0:
    print(f"\n✓ Tarefa '{TAREFA}' criada com sucesso!")
    print("  Roda todos os dias as 08:00 ou ao ligar o PC.")
    print(f"\n  Para verificar: abra o Agendador de Tarefas")
    print(f"  e procure por '{TAREFA}'")
else:
    print(f"\n✗ Erro ao criar tarefa:")
    print(result.stderr or result.stdout)

if __name__ == "__main__":
    pass
