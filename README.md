# Monitor de Preços — Peruíbe SP

Coleta automática diária de preços de pousadas concorrentes em Peruíbe via Google Hotels. Roda localmente no seu PC, sem custo.

---

## 📁 Estrutura do projeto

```
price_monitoring/
├── README.md                  ← este arquivo
├── LICENSE                    ← MIT License
├── .env                       ← variáveis de ambiente (copie de .env.example)
├── .env.example               ← modelo de variáveis
├── .gitignore
├── requirements.txt           ← dependências Python
├── CHANGELOG.md               ← histórico de versões
├── coletar.py                 ← scraper principal (roda todo dia)
├── dados/
│   ├── precos.db              ← banco SQLite (criado automaticamente)
│   ├── log.txt                ← histórico de execuções
│   └── ultima_coleta.txt      ← controle: data da última coleta
├── docs/
│   └── index.html             ← dashboard HTML (gerado automaticamente)
├── scripts/
│   └── push_github.ps1        ← push para GitHub após coleta
└── src/
    ├── collector.py           ← scraper principal (roda todo dia)
    ├── dashboard.py           ← atualização do dashboard HTML
    └── tester.py              ← teste visual do scraper
```

---

## 🚀 Instalação (Windows)

### 1. Instalar Python

Baixe em https://python.org — marque **"Add Python to PATH"** na instalação.

### 2. Instalar dependências

Abra o Prompt de Comando na pasta do projeto e execute:

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 3. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto copiando `.env.example`:

```bash
cp .env.example .env
```

Edite `.env` com seus valores:

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `PYTHON_PATH` | Caminho do python.exe (opcional, usa PATH se não definido) | `C:\Python313\python.exe` |
| `PROJETO_PATH` | Caminho do diretório do projeto (opcional, usa cwd se não definido) | `C:\Users\Jason\Desktop\price_monitoring` |
| `GITHUB_REPO` | Nome do repositório GitHub (opcional) | `price_monitoring` |
| `GITHUB_TOKEN` | Token GitHub para push (opcional) | `ghp_xxxxx` |

### 4. Testar a coleta

```bash
python src/tester.py
```

Um navegador vai abrir e você verá ao vivo o que o script está coletando. Se aparecerem resultados, está tudo certo.

### 5. Rodar uma vez manualmente

```bash
python coletar.py
```

Verifica se os dados foram gravados:

```python
import sqlite3
con = sqlite3.connect("dados/precos.db")
print(con.execute("SELECT count(*) FROM precos").fetchone())
```

### 6. Configurar o agendador automático

O agendamento é feito manualmente via Windows Task Scheduler (Logon + 08:00 AM).

Depois abra o PowerShell como **Administrador** e execute:

```powershell
.\scripts\configurar_agendador.ps1
```

A tarefa roda todos os dias às 08:00 ou ao fazer login no Windows.

---

## ⚙️ Como funciona

### Controle diário

O script verifica `dados/ultima_coleta.txt` antes de rodar. Se a data gravada for hoje, ele encerra sem fazer nada. Isso garante que mesmo se o PC for ligado várias vezes no dia, a coleta acontece apenas uma vez.

### Coleta

- Varre **7 dias à frente** (checkin + 1 ao checkout + 2)
- Ordena por **menor preço** e filtra **acima de R$ 50**
- Converte USD→BRL automaticamente via taxa do dia
- Limite de **50 concorrentes** por dia
- Salva no banco SQLite + atualiza dashboard + push para GitHub

### Dashboard

O dashboard HTML é atualizado automaticamente após cada coleta:
- KPIs: menor preço, maior preço, preço médio, concorrentes
- Tabela com top 50 pousadas
- Dados em tempo real via JavaScript

---

## 📊 Consultando os dados coletados

```python
import sqlite3
con = sqlite3.connect("dados/precos.db")

# Ver os últimos preços coletados
for row in con.execute("""
    SELECT checkin, nome, preco_brl, plataforma
    FROM precos
    ORDER BY coletado_em DESC
    LIMIT 20
"""):
    print(row)

# Média de preço por pousada
for row in con.execute("""
    SELECT nome, ROUND(AVG(preco_brl), 2) as media
    FROM precos
    GROUP BY nome
    ORDER BY media ASC
    LIMIT 20
"""):
    print(row)
```

---

## ⚠️ Problemas conhecidos

### Google muda o HTML do site

O Google pode mudar o HTML dos cards sem aviso prévio.

**Sintomas:** `coletar.py` roda sem erros mas `count(*)` no banco fica em zero.

**Solução:**
1. Rode `python src/tester.py` — ele salva o HTML em `debug_pagina.html`
2. Abra esse arquivo no navegador e inspecione os elementos dos cards
3. Atualize os seletores na função `parsear_html()` em `coletar.py`

### Timeout ao carregar página

**Causa:** Conexão lenta ou Google bloqueando requisições.

**Solução:** Verifique sua conexão de internet. O timeout é de 30 segundos.

### Cotação indisponível

**Causa:** API da awesomeapi.com.br offline ou taxa de limite.

**Solução:** O script usa R$ 5,00 como fallback. Verifique a API mais tarde.

### Push para GitHub falha

**Causa:** Token GitHub expirado ou repositório privado sem token.

**Solução:** Verifique se `GITHUB_TOKEN` está definido em `.env` com um token válido.

### Tarefa Windows não roda

**Causa:** Agendador de Tarefas desabilitado ou sem permissão.

**Solução:** Abra o Agendador de Tarefas → Tarefas do Usuário → encontre "MonitorPrecosPeruibe" → clique com botão direito → Propriedades → Segurança → marque "Executar com privileges mais elevados".

---

## 🛠️ Ajustando seletores (quando o scraper parar de funcionar)

1. Rode `python src/tester.py` — ele salva o HTML em `debug_pagina.html`
2. Abra esse arquivo no navegador e inspecione os elementos dos cards
3. Atualize os seletores na função `parsear_html()` em `coletar.py`

---

## 🔒 Segurança

- **Nenhum dado é enviado para servidores externos** (exceto cotação USD/BRL)
- **Push para GitHub** usa token opcional — não commitar `.env` no repositório
- **Anti-detection de bot** — mascara propriedade `webdriver` do navegador
- `.env` é excluído do `.gitignore` — nunca commitar variáveis reais

---

## 📝 Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `PYTHON_PATH` | `python` | Caminho completo do python.exe |
| `PROJETO_PATH` | `.` (cwd) | Caminho do diretório do projeto |
| `GITHUB_REPO` | — | Nome do repositório GitHub |
| `GITHUB_TOKEN` | — | Token GitHub para push em repos privados |

---

## 🤝 Contribuindo

1. Fork do repositório
2. Crie uma branch para sua feature
3. Faça commits atômicos com mensagens claras
4. Abra um Pull Request

### Regras

- Não modificar `.env` (variáveis reais não devem ser commitadas)
- Não modificar `dados/precos.db` (banco é local)
- Manter compatibilidade com Windows
- Testar antes de enviar

---

## 📚 Roadmap

- [ ] Dashboard com gráficos históricos de preços por pousada
- [ ] Alerta por e-mail quando concorrente baixar o preço abaixo de X
- [ ] Comparação com Booking.com e Airbnb
- [ ] Exportação de dados em CSV/Excel
- [ ] Configuração para outros destinos (não apenas Peruíbe)
- [ ] API REST para consultar dados remotamente

---

## 📜 Licença

MIT License — veja [LICENSE](LICENSE)
