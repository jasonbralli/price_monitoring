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
├── scripts/
│   ├── coletar.py             ← scraper principal (roda todo dia às 08:00)
│   ├── push_github.py         ← wrapper para atualizar dashboard e push GitHub
│   └── run_coleta.bat         ← wrapper chamado pelo Windows Task Scheduler
├── src/
│   └── dashboard.py           ← gera o HTML do dashboard a partir do banco
├── dados/
│   ├── precos.db              ← banco SQLite (criado automaticamente)
│   ├── log.txt                ← histórico de execuções
│   └── ultima_coleta.txt      ← controle: data da última coleta
├── docs/
│   └── index.html             ← dashboard HTML (gerado automaticamente pelo dashboard.py)
├── .python-version            ← versão do Python usada no venv
├── requirements.txt           ← dependências do projeto
└── uv.lock                    ← lock file do uv
```

---

## 🚀 Instalação

### 1. Instalar Python e uv

Baixe em https://github.com/astral-sh/uv — ou use o pip:

```bash
pip install uv
```

### 2. Criar ambiente virtual e instalar dependências

```bash
cd price_monitoring
uv sync
```

Isso cria `.venv` com Python 3.11+ e instala `playwright`, `beautifulsoup4`, `urllib3`.

### 3. Instalar o Playwright browser

```bash
python -m playwright install chromium
```

### 4. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto copiando `.env.example`:

```bash
cp .env.example .env
```

Edite `.env` com seus valores:

| Variável | Descrição | Exemplo |
|----------|-----------|---------|
| `GITHUB_TOKEN` | Token GitHub para push (opcional) | `ghp_xxxxx` |

### 5. Testar a coleta manualmente

```bash
python scripts/coletar.py
```

Um navegador headless vai abrir e coletar dados do Google Hotels. Verifique o log em `dados/log.txt`.

---

## ⚙️ Como funciona

### Controle diário

O script verifica `dados/ultima_coleta.txt` antes de rodar. Se a data gravada for hoje, ele encerra sem fazer nada — garante que mesmo se o PC ligar várias vezes no dia, a coleta roda apenas uma vez.

### Fluxo da coleta

1. **Busca taxa USD/BRL** via API (fallback R$ 5,00)
2. **Abre Google Hotels** com Playwright (headless, anti-detection)
3. **Varre 7 dias à frente**, ordenando por menor preço
4. **Aplica filtros** (Menor preço + acima de R$ 50) clicando na interface
5. **Paga até 50 concorrentes** via clique no botão "Avançar"
6. **Salva no banco SQLite** + atualiza dashboard HTML + push para GitHub

### Dashboard

O `src/dashboard.py` lê o banco e injeta dados JSON diretamente no `docs/index.html`:
- KPIs: menor preço, maior preço, preço médio, concorrentes monitorados
- Tabela com top 50 pousadas
- Dados em tempo real via JavaScript (sem servidor)

### Push para GitHub

O `scripts/push_github.py` faz automaticamente:
1. Chama `src/dashboard.py` para gerar o HTML atualizado
2. `git add docs/index.html dados/log.txt`
3. `git commit -m "coleta YYYY-MM-DD HH:MM"`
4. `git push origin main --token <GITHUB_TOKEN>`

---

## 📊 Consultando os dados coletados

```python
import sqlite3
con = sqlite3.connect("dados/precos.db")

# Últimos preços coletados
for row in con.execute("""
    SELECT checkin, nome, preco_brl
    FROM precos ORDER BY coletado_em DESC LIMIT 20
"""):
    print(row)

# Média de preço por pousada
for row in con.execute("""
    SELECT nome, ROUND(AVG(preco_brl), 2) as media
    FROM precos GROUP BY nome ORDER BY media ASC LIMIT 20
"""):
    print(row)
```

---

## ⚠️ Problemas conhecidos

### Google muda o HTML do site

**Sintomas:** `python scripts/coletar.py` roda sem erros mas `count(*)` no banco fica em zero.

**Solução:**
1. Rode `python scripts/coletar.py` — ele salva o HTML em `dados/debug_pagina.html` (se disponível)
2. Abra esse arquivo no navegador e inspecione os cards
3. Atualize os seletores na função `parsear_html()` em `scripts/coletar.py`

### Timeout ao carregar página

**Causa:** Conexão lenta ou Google bloqueando requisições.

**Solução:** Verifique sua conexão de internet. O timeout é de 30 segundos.

### Push para GitHub falha

**Causa:** Token GitHub expirado ou repositório sem token.

**Solução:** Verifique se `GITHUB_TOKEN` está definido em `.env`.

---

## 🛠️ Ajustando seletores (quando o scraper parar de funcionar)

1. Rode `python scripts/coletar.py` — ele salva o HTML em `dados/debug_pagina.html`
2. Abra esse arquivo no navegador e inspecione os cards
3. Atualize os seletores na função `parsear_html()` em `scripts/coletar.py`

---

## 🔒 Segurança

- **Nenhum dado é enviado para servidores externos** (exceto cotação USD/BRL)
- **Push para GitHub** usa token opcional — não commitar `.env` no repositório
- **Anti-detection de bot** — mascara propriedade `webdriver` do navegador
- `.env` e `dados/precos.db` estão no `.gitignore`

---

## 📝 Variáveis de ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
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
