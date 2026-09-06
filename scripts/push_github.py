"""Wrapper para push_github — executa a lógica sem depender de PowerShell."""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _run(cmd, **kwargs):
    return subprocess.run(
        cmd, capture_output=True, text=True, errors="replace", **kwargs)


def main():
    # Define o diretório do projeto (parent do scripts/)
    PROJETO_DIR = Path(__file__).resolve().parent.parent

    print("Atualizando dashboard...")

    # Atualiza o dashboard com o mesmo interpretador (v4.1: sem "python" literal)
    result = _run([sys.executable, "scripts/dashboard.py"], cwd=str(PROJETO_DIR))

    if result.returncode != 0:
        print(f"Erro ao atualizar dashboard: {result.stderr.strip()[:300]}")
        return

    # Data da coleta
    data = datetime.now().strftime("%Y-%m-%d %H:%M")

    print("Enviando para o GitHub...")

    # Só o dashboard é versionado (dados/log.txt está no .gitignore)
    git_add_result = _run(["git", "add", "docs/index.html"], cwd=str(PROJETO_DIR))

    if git_add_result.returncode != 0:
        print(f"Erro no git add: {git_add_result.stderr.strip()[:300]}")
        return

    commit_result = _run(
        ["git", "commit", "-m", f"coleta {data}"], cwd=str(PROJETO_DIR))

    if commit_result.returncode != 0:
        saida = commit_result.stdout + commit_result.stderr
        if "nothing to commit" in saida:
            print("Sem mudanças para commitar — nada a enviar.")
            return
        print(f"Erro no git commit: {commit_result.stderr.strip()[:300]}")
        return

    # Push (token via header — "git push --token" não existe)
    github_token = os.environ.get("GITHUB_TOKEN", "")

    if github_token:
        push_result = _run(
            ["git", "-c",
             f"http.extraHeader=AUTHORIZATION: bearer {github_token}",
             "push", "origin", "main"],
            cwd=str(PROJETO_DIR))
    else:
        push_result = _run(
            ["git", "push", "origin", "main"], cwd=str(PROJETO_DIR))

    if push_result.returncode != 0:
        msg = push_result.stderr.strip()[:300]
        if github_token:  # nunca expor o token no log
            msg = msg.replace(github_token, "***")
        print(f"Erro no git push: {msg}")
        return

    print("")
    print("OK - GitHub Pages atualizado em " + data)


if __name__ == "__main__":
    main()
