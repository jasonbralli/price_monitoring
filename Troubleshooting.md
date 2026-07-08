# Troubleshooting — Solução de Problemas

Guia completo para resolver problemas comuns do Price Monitoring.

---

## 🐛 Erros de Coleta

### "Sem resultados coletados"

**Causas possíveis:**
1. Google mudou o HTML dos cards
2. Bloqueio por IP (requisições muito rápidas)
3. Conexão lenta ou instável

**Solução:**
```bash
# 1. Rode o teste visual para ver o HTML atual
python src/tester.py

# 2. Verifique o log
type dados\log.txt

# 3. Se os seletores mudaram, edite parsear_html() em coletar.py
```

### "Timeout ao carregar página"

**Solução:**
- Verifique sua conexão de internet
- Aguarde 30 segundos e tente novamente
- Se persistir, o Google pode ter bloqueado seu IP

### "Erro ao aplicar filtros"

**Sintomas:** Script roda mas não filtra por menor preço/R$50

**Solução:**
- O Google pode ter mudado a interface de filtros
- Verifique `debug_pagina.html` gerado pelo tester
- Atualize os seletores em `aplicar_filtros()` em `coletar.py`

---

## 📊 Erros de Banco de Dados

### "Banco de dados não encontrado"

**Solução:**
```bash
# Verifique se o banco existe
dir dados\precos.db

# Se não existir, rode a coleta para criar
python coletar.py
```

### "Erro ao inserir registro"

**Sintomas:** Coleta roda mas banco não aumenta

**Solução:**
```python
# Verifique a tabela
import sqlite3
con = sqlite3.connect("dados/precos.db")
print(con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())

# Verifique se há dados
print(con.execute("SELECT count(*) FROM precos").fetchone())
```

---

## 🌐 Erros de Push GitHub

### "Erro ao atualizar dashboard"

**Solução:**
```bash
# Execute manualmente
python src/dashboard.py
```

### "Erro ao push para GitHub"

**Causas:**
1. Token GitHub expirado
2. Repositório privado sem token
3. Branch não atualizada

**Solução:**
```bash
# Verifique o token
git remote -v

# Atualize o token em .env
# GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Force push se necessário
git fetch origin
git reset --hard origin/main
git push origin main --force
```

### "Push sem token"

**Solução para repos privados:**
1. Acesse https://github.com/settings/tokens
2. Crie um novo token com permissão "repo"
3. Adicione em `.env`:
```
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## 🪟 Erros do Windows

### "Tarefa não roda"

**Sintomas:** Agendador de Tarefas mostra "Falha"

**Solução:**
1. Abra **Agendador de Tarefas** (taskschd.msc)
2. Navegue até: Tarefas do Usuário → MonitorPrecosPeruibe
3. Clique com botão direito → **Propriedades**
4. Aba **Segurança** → marque **"Executar com privileges mais elevados"**
5. Clique OK e teste

### "Erro ao executar PowerShell"

**Sintomas:** Script PowerShell não roda

**Solução:**
1. Abra PowerShell como **Administrador**
2. Execute:
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
```
3. Tente novamente

### "Python não encontrado"

**Solução:**
1. Verifique se Python está no PATH
2. Ou defina `PYTHON_PATH` em `.env`
3. Ou use o caminho completo:
```
PYTHON_PATH=C:\Users\Jason\AppData\Local\Programs\Python\Python313\python.exe
```

---

## 🐍 Erros Python

### "ModuleNotFoundError: No module named 'playwright'"

**Solução:**
```bash
pip install playwright
python -m playwright install chromium
```

### "ModuleNotFoundError: No module named 'beautifulsoup4'"

**Solução:**
```bash
pip install beautifulsoup4
```

### "ImportError: cannot import name 'TimeoutError'"

**Solução:**
```bash
pip install --upgrade playwright
```

---

## 📁 Erros de Arquivos

### "Arquivo não encontrado"

**Solução:**
```bash
# Verifique os caminhos
dir dados\
dir src\
dir scripts\

# Se arquivos faltarem, faça git pull
git pull origin main
```

### "Erro ao ler arquivo HTML"

**Sintomas:** Dashboard não atualiza

**Solução:**
- Verifique se `dashboard/index.html` existe
- Se o arquivo corromper, restaure do backup:
```bash
copy backup\index_*.html dashboard\index.html
```

---

## 🔍 Diagnóstico Rápido

### Checklist de verificação

- [ ] Python instalado e no PATH
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] Chromium instalado (`python -m playwright install chromium`)
- [ ] `.env` configurado com valores corretos
- [ ] Banco de dados existe (`dados/precos.db`)
- [ ] Conexão de internet estável
- [ ] Google Hotels acessível

### Comandos úteis

```bash
# Verificar dependências
pip list

# Verificar banco
python -c "import sqlite3; con=sqlite3.connect('dados/precos.db'); print(con.execute('SELECT count(*) FROM precos').fetchone())"

# Verificar último log
type dados\log.txt | tail -20

# Verificar tarefa Windows
schtasks /query /tn "MonitorPrecosPeruibe" /fo LIST

# Verificar git
git status
git log --oneline -5
```

---

## 🆘 Precisa de mais ajuda?

Se nenhum desses passos resolver:

1. Verifique `dados/log.txt` para erros detalhados
2. Rode `python src/tester.py` para debug visual
3. Abra um issue no repositório GitHub
4. Envie os logs do dia

---

## 📚 Referências

- [Documentação oficial do Playwright](https://playwright.dev/python/)
- [Documentação do BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Agendador de Tarefas Windows](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks)
