# Changelog

## [4.0] - 2026-07-01

### Adicionado
- Estrutura de diretórios refatorada para `src/` e `scripts/`
- Variáveis de ambiente via `.env` para configuração
- `.gitignore` expandido com exclusões adequadas
- `requirements.txt` para dependências Python
- `.env.example` para documentação de variáveis
- Dashboard auto-atualizado após coleta
- Paginação mais robusta com fallback JS
- Filtros aplicados via clique (não via URL)
- Push automático para GitHub após coleta
- Anti-detection de bot (webdriver property)
- Converte USD→BRL automaticamente via taxa do dia
- Controle diário (`ultima_coleta.txt`) evita execuções duplicadas

### Melhorado
- Scripts PowerShell e Python agora usam variáveis de ambiente
- Validação de caminhos em scripts PowerShell
- Tratamento de erros mais robusto

### Alterado
- Coletar.py refatorado para usar novos paths
- Dashboard movido para `dashboard/index.html`

## [3.0] - 2026-06-28

### Adicionado
- Paginação via clique no botão "Avançar"
- Aplicação de filtros via interface (não via URL)
- Conversão USD→BRL automática
- Push automático para GitHub

## [2.0] - 2026-06-25

### Adicionado
- Coleta de preços de pousadas em Peruíbe SP
- Banco de dados SQLite
- Dashboard HTML
- Teste visual do scraper

## [1.0] - 2026-05-08

### Adicionado
- Primeiro scraper de preços
- Coleta básica de pousadas
