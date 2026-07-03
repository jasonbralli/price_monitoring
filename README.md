# Price Monitoring — Monitor de Preços Peruíbe

Monitor automatizado de preços de pousadas em Peruíbe/SP via Google Hotels, com dashboard HTML e deploy automático no GitHub Pages.

## Estrutura

```
.
├── coletar.py              # Entrypoint da coleta (usado pelo agendador)
├── src/
│   ├── criar_tarefa.py     # Cria tarefa agendada no Windows
│   ├── dashboard.py        # Gera dashboard/index.html a partir do banco
│   └── tester.py           # Teste visual do scraper (headless=False)
├── scripts/
│   ├── configurar_agendador.ps1
│   └── push_github.ps1
├── dados/
│   ├── precos.db
│   ├── log.txt
│   └── ultima_coleta.txt
├── dashboard/
│   └── index.html
├── requirements.txt
└── .env.example
```

## Fluxo

1. `coletar.py` coleta preços (7 dias à frente, até 50 pousadas) e salva em SQLite.
2. `dashboard.py` gera `dashboard/index.html` com os dados mais recentes.
3. `push_github.ps1` commita e faz push para `gh-pages` (GitHub Pages).

## Setup

```bash
python -m pip install -r requirements.txt
playwright install chromium
```

## Agendamento (Windows)

```bash
python src/criar_tarefa.py
```

Requer PowerShell como Administrador para executar `schtasks /create`.

## Variáveis de ambiente

Copie `.env.example` para `.env` e ajuste se necessário:

- `PYTHON_PATH`: caminho do Python (opcional)
- `PROJETO_PATH`: raiz do projeto (opcional)
- `GITHUB_TOKEN`: token para push sem interação (opcional)
