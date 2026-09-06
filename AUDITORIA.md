# Auditoria — price_monitoring (06/09/2026)

**Status: ✅ implementado em 06/09/2026 — coletar.py v4.1, push_github corrigido, testes em `tests/`, PS1 em `scripts/scheduler/`.**

Metodologia: skill `project-audit` (inventário → py_compile → paths → secrets scan → lógica → git).
Branch `main`, status limpo. `py_compile` OK nos 4 scripts. Nenhum segredo commitado (só placeholder `ghp_xxxxx` na doc).

## Legenda

- 🔴 CRÍTICO — quebra funcionalidade hoje
- 🟡 SECUNDÁRIO — confiabilidade / drift doc-vs-código
- 🔵 MELHORIA — baixo custo, alto valor

---

## 🔴 C1 — `git push --token` não existe (push quebra com token definido)

`scripts/push_github.py:55`: `["git", "push", "origin", "main", "--token", github_token]`.
Git não tem flag `--token` no push → com `GITHUB_TOKEN` definido, **todo push falha**.
README:109 repete o comando inválido.
**Fix:** remover a flag; autenticar via URL (`https://<token>@github.com/...`) ou credential helper; nunca logar stderr com token embutido.

## 🔴 C2 — `git add dados/log.txt` conflita com `.gitignore`

`push_github.py:33` adiciona `dados/log.txt`, mas o arquivo está no `.gitignore` (commit `b8f341f`)
**e nem existe no disco** (`dados/` só tem `precos.db` 22 MB + `ultima_coleta.txt`).
`git add` de pathspec ignorado/inexistente retorna ≠0 → o wrapper **aborta antes do commit** (return precoce, linha 37-39).
**Fix:** `git add docs/index.html` apenas (ou `git add -f` se log voltar a ser versionado — não recomendado).

## 🔴 C3 — `marcar_executado()` antes da coleta perde o dia em caso de crash

`coletar.py:327` grava `ultima_coleta.txt` **antes** de abrir o browser.
Se o scraper falhar, `ja_rodou_hoje()` retorna True o resto do dia → **zero retry, falha silenciosa**.
**Fix:** marcar só após `status == "ok"` (ou gravar `ultima_coleta.txt` + `status` no `coletas` e permitir retentativa quando status=erro).

## 🔴 C4 — `subprocess` usa `"python"` literal (2 pontos)

`coletar.py:53` e `:391`, `push_github.py:17`. No Windows resolve o Python do PATH
(3.11 Hermes vs 3.13 global vs `.venv`) — ambiente imprevisível; `run_coleta.bat` fixa 3.13 global,
mas nada garante `playwright` instalado nele.
**Fix:** usar `sys.executable` em todos os subprocess; no `.bat`, preferir `.venv\Scripts\python.exe` ou `uv run`.

## 🟡 R1 — Seletores ofuscados sem detecção de falha silenciosa

`kCsInf`, `BgYkof`, `jsname=OCpkoe` mudam sem aviso. README admite "count=0 sem erro",
mas o código **não alerta** e **não salva** `dados/debug_pagina.html` (README:143/174 cita o arquivo 2x —
ele nunca é gravado pelo código). Drift doc-vs-código.
**Fix:** se `total == 0` com `status ok`, marcar status=`aviso`, salvar HTML debug, logar snippet dos seletores.

## 🟡 R2 — Regex de preço pega o primeiro `R$` do card

`parsear_html` (:161) captura o primeiro `R$`/`US$` do texto — pode ser taxa, imposto ou total,
não necessariamente a diária. Sem validação de faixa (ex: descartar < R$ 30 ou > R$ 10.000).
**Fix:** priorizar elemento de preço dedicado; validar faixa plausível; logar descartes.

## 🟡 R3 — Filtro "Acima de R$ 50" documentado mas não implementado

README:fluxo passo 4 e `aplicar_filtros()` docstring citam "Menor preço + acima de R$ 50",
mas o código só clica em "Menor preço" (:221). Drift doc-vs-código.

## 🟡 R4 — Sem índices no SQLite (db já com 22 MB)

Consultas por `date(coletado_em)` fazem full scan e vão degradar a cada coleta (~7 dias × páginas).
**Fix:** `CREATE INDEX IF NOT EXISTS idx_precos_coletado ON precos(coletado_em);`
`CREATE INDEX IF NOT EXISTS idx_coletas_data ON coletas(data);` em `iniciar_banco()`.

## 🟡 R5 — `check_pipeline.py` dá FAIL falso antes das 08:00

Compara `ultima_coleta.txt == today`; se a auditoria rodar antes do Scheduler, reporta falha inexistente.
**Fix:** aceitar `today` ou `yesterday` (ou checar `coletas.status` da última linha em vez da data).

## 🟡 R6 — 6 arquivos `.ps1` na raiz, nenhum documentado

`_check/_diario_info/_fix/_scheduler_status/_scheduler_summary.ps1` + `fix_scheduler.ps1`
(5 com prefixo `_` = provável iteração exploratória). README não cita nenhum; sobreposição com `fix_scheduler.ps1`.
**Fix:** consolidar em `scripts/scheduler/` (1 script canônico), arquivar resto, documentar 1 linha no README.

## 🟡 R7 — `.env.example` documenta variáveis que o código não lê

`PYTHON_PATH`, `PROJETO_PATH`, `GITHUB_REPO` não são lidos por nenhum script
(o código lê `PROJECT_ROOT` e `GITHUB_TOKEN`). README:estrutura cita `uv.lock` (não existe no repo).
**Fix:** sincronizar `.env.example` com as vars reais; corrigir árvore no README.

## 🟡 R8 — Log sem rotação + `LOG_PATH` órfão

`log()` faz append infinito; hoje o arquivo nem existe (coletas desde 03/09 sem log em disco?).
`push_github.py` referencia o log que não existe (ver C2).
**Fix:** rotação simples (cap ~500 KB ou 30 dias) + decidir: log versionado ou ignorado (hoje está nos dois lugares).

## 🔵 Melhorias (backlog ordenado por custo-benefício)

| # | Ação | Esforço |
|---|------|---------|
| M1 | Índices SQLite (R4) | 5 min |
| M2 | `sys.executable` nos 3 subprocess (C4) | 10 min |
| M3 | `git add` sem `log.txt`, sem `--token` (C1+C2) | 15 min |
| M4 | Marcar executado após sucesso (C3) | 15 min |
| M5 | Alerta 0-cards + debug HTML (R1) | 30 min |
| M6 | Validação faixa de preço (R2) | 20 min |
| M7 | Consolidar PS1 + doc (R6) | 30 min |
| M8 | Sincronizar `.env.example` + README (R7) | 20 min |
| M9 | Rotação de log (R8) | 20 min |
| M10 | Suite pytest mínima (parser fixture + tiers câmbio com mock + check_pipeline) | 1–2 h |
| M11 | Lock anti-concorrência (`filelock` ou lockfile em `dados/`) | 30 min |

## ✅ Pontos positivos (manter)

- SQL 100% parametrizado — sem injeção.
- `.env` fora do git; scan de segredos limpo.
- Cotação 3-tier (API → última válida → 5,00) com validação de plausibilidade (3–8).
- Paths via `pathlib`, `BASE_DIR` consistente nos 4 scripts.
- Footer `inovatudo.com` presente no dashboard; markers `POUSADAS/SEM_PRECO/header-meta` OK (12 ocorrências).
- `requirements.txt` documenta workaround `greenlet` via `uv` (memory do ambiente).

## Plano de execução sugerido

- **Fase 1 (estabilização, ~1 h):** M1+M2+M3+M4 — elimina as 4 quebras reais de hoje.
- **Fase 2 (confiabilidade, ~2 h):** M5+M6+M9+M11+R5 — falha silenciosa deixa de existir.
- **Fase 3 (higiene, ~1 h):** M7+M8+R7+M10 — docs, testes, scheduler consolidado.
