"""Wrapper para push_github — executa a lógica sem depender de PowerShell."""

import os
import subprocess
from datetime import datetime
from pathlib import Path


def main():
    # Define o diretório do projeto (parent do scripts/)
    PROJETO_DIR = Path(__file__).resolve().parent.parent
    
    print("Atualizando dashboard...")
    
    # Atualiza o dashboard com Python
    result = subprocess.run(
        ["python", "src/dashboard.py"],
        cwd=str(PROJETO_DIR),
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print(f"Erro ao atualizar dashboard: {result.stderr}")
        return
    
    # Data da coleta
    data = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    print("Enviando para o GitHub...")
    
    # Adiciona e commita os arquivos
    git_add_result = subprocess.run(
        ["git", "add", "docs/index.html", "dados/log.txt"],
        capture_output=True, text=True
    )
    
    if git_add_result.returncode != 0:
        print(f"Erro no git add: {git_add_result.stderr}")
        return
    
    commit_result = subprocess.run(
        ["git", "commit", "-m", f"coleta {data}"],
        capture_output=True, text=True
    )
    
    if commit_result.returncode != 0:
        print(f"Erro no git commit: {commit_result.stderr}")
        return
    
    # Push para o GitHub (com token se disponível)
    github_token = os.environ.get("GITHUB_TOKEN", "")
    
    if github_token:
        push_result = subprocess.run(
            ["git", "push", "origin", "main", "--token", github_token],
            capture_output=True, text=True
        )
    else:
        push_result = subprocess.run(
            ["git", "push", "origin", "main"],
            capture_output=True, text=True
        )
    
    if push_result.returncode != 0:
        print(f"Erro no git push: {push_result.stderr}")
        return
    
    print("")
    print("OK - GitHub Pages atualizado em " + data)


if __name__ == "__main__":
    main()
