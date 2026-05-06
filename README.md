# Monitor de Preços — Peruíbe SP

Coleta automática diária de preços de pousadas concorrentes
em Peruíbe via Google Hotels. Roda localmente no seu PC, sem custo.

---

## Estrutura do projeto

```
peruibe_monitor/
├── coletar.py              ← scraper principal (roda todo dia)
├── testar_coleta.py        ← teste visual, rode primeiro
├── configurar_agendador.ps1← configura o Windows Task Scheduler
├── dados/
│   ├── precos.db           ← banco SQLite (criado automaticamente)
│   ├── log.txt             ← histórico de execuções
│   └── ultima_coleta.txt   ← controle: data da última coleta
└── README.md
```

---

## Instalação (Windows)

### 1. Instalar Python
Baixe em https://python.org — marque "Add Python to PATH" na instalação.

### 2. Instalar dependências
Abra o Prompt de Comando na pasta do projeto e execute:

```
pip install playwright
python -m playwright install chromium
```

### 3. Testar a coleta
```
python testar_coleta.py
```
Um navegador vai abrir e você verá ao vivo o que o script está coletando.
Se aparecerem resultados, está tudo certo.

### 4. Rodar uma vez manualmente
```
python coletar.py
```
Verifica se os dados foram gravados:
```
python -c "import sqlite3; con=sqlite3.connect('dados/precos.db'); print(con.execute('SELECT count(*) FROM precos').fetchone())"
```

### 5. Configurar o agendador automático
Edite o arquivo `configurar_agendador.ps1` com os seus caminhos:
- `PYTHON_PATH`: onde está o python.exe (ex: `C:\Python312\python.exe`)
- `PROJETO_PATH`: onde está o coletar.py

Depois abra o PowerShell como **Administrador** e execute:
```
.\configurar_agendador.ps1
```

---

## Como funciona o controle de data

O script verifica `dados/ultima_coleta.txt` antes de rodar.
Se a data gravada for hoje, ele encerra sem fazer nada.
Isso garante que mesmo se o PC for ligado várias vezes no dia,
a coleta acontece apenas uma vez.

---

## Consultando os dados coletados

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
```

---

## Ajustando seletores (quando o scraper parar de funcionar)

O Google pode mudar o HTML do site sem aviso.
Sintomas: `coletar.py` roda sem erros mas `count(*)` no banco fica em zero.

Solução:
1. Rode `testar_coleta.py` — ele salva o HTML em `debug_pagina.html`
2. Abra esse arquivo no navegador e inspecione os elementos dos cards
3. Atualize os seletores na função `extrair_pousadas()` em `coletar.py`

---

## Próximos passos

- [ ] Dashboard PHP no HostGator para visualizar os dados
- [ ] Gráfico histórico de preços por pousada
- [ ] Alerta por e-mail quando concorrente baixar o preço abaixo de X
