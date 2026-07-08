"""
atualizar_dashboard.py — Atualiza o dashboard HTML com dados do banco.
Usa caminho relativo ao diretório do projeto (não ao do módulo).
"""

import sqlite3, json, re
from pathlib import Path

# Caminho relativo ao diretório do projeto (não ao módulo)
PROJETO_DIR = Path(__file__).parent.parent
DB_PATH = PROJETO_DIR / "dados" / "precos.db"
HTML_PATH = PROJETO_DIR / "docs" / "index.html"


def atualizar_dashboard():
    """Atualiza dashboard HTML com dados do banco."""
    if not DB_PATH.exists():
        print("Banco de dados nao encontrado.")
        return

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Pega ultima data de coleta
    row = cur.execute("SELECT MAX(date(coletado_em)) FROM precos").fetchone()
    if not row or not row[0]:
        print("Sem dados no banco.")
        return
    ultima_data = row[0]

    # Pousadas com preco (media dos proximos 7 dias) — limite 50, ordenadas por menor preco
    rows = cur.execute("""
        SELECT nome, ROUND(AVG(preco_brl), 0) as preco, ROUND(AVG(avaliacao), 1) as aval, MAX(reviews) as reviews
        FROM precos
        WHERE date(coletado_em) = ? AND preco_brl IS NOT NULL
        GROUP BY nome
        ORDER BY preco ASC
        LIMIT 50
    """, (ultima_data,)).fetchall()

    pousadas = [{"nome": r[0], "preco": int(r[1]) if r[1] else 0, "aval": r[2] or 0, "reviews": r[3] or "0"} for r in rows]

    # Pousadas sem preco — ignoradas no dashboard
    sem_preco = []

    # KPIs
    row_taxa = cur.execute("SELECT taxa_cambio FROM coletas WHERE data = ? ORDER BY id DESC LIMIT 1", (ultima_data,)).fetchone()
    taxa_val = row_taxa[0] if row_taxa else 5.0

    total_registros = cur.execute("SELECT COUNT(*) FROM precos WHERE date(coletado_em) = ?", (ultima_data,)).fetchone()[0]

    if not pousadas:
        print("Nenhuma pousada com preco encontrada para hoje.")
        return

    menor_preco = pousadas[0]
    maior_preco = pousadas[-1]
    preco_medio = int(sum(p['preco'] for p in pousadas) / len(pousadas))
    concorrentes = len(pousadas)

    # Le dashboard.html
    html = HTML_PATH.read_text(encoding="utf-8")

    # Header
    html = re.sub(
        r'<div class="header-meta">.*?</div>',
        f'<div class="header-meta">\n    Coleta: {ultima_data} &nbsp;·&nbsp; Taxa: R$ {taxa_val:.2f}/USD &nbsp;·&nbsp; {total_registros} registros\n  </div>',
        html, flags=re.DOTALL
    )

    # KPI Menor Preco
    html = re.sub(
        r'<div class="kpi green">.*?</div>\s*</div>',
        f'<div class="kpi green">\n      <div class="kpi-body">\n        <div class="kpi-label">Menor preco</div>\n        <div class="kpi-value accent">R$ {menor_preco["preco"]}</div>\n        <div class="kpi-sub">{menor_preco["nome"][:20]}...</div>\n      </div>\n    </div>',
        html, flags=re.DOTALL
    )

    # KPI Medio
    html = re.sub(
        r'<div class="kpi blue">.*?</div>\s*</div>',
        f'<div class="kpi blue">\n      <div class="kpi-body">\n        <div class="kpi-label">Preco medio mercado</div>\n        <div class="kpi-value blue">R$ {preco_medio}</div>\n        <div class="kpi-sub">{len(pousadas)} pousadas com preco</div>\n      </div>\n    </div>',
        html, flags=re.DOTALL
    )

    # KPI Maior
    html = re.sub(
        r'<div class="kpi orange">.*?</div>\s*</div>',
        f'<div class="kpi orange">\n      <div class="kpi-body">\n        <div class="kpi-label">Maior preco</div>\n        <div class="kpi-value orange">R$ {maior_preco["preco"]}</div>\n        <div class="kpi-sub">{maior_preco["nome"][:20]}...</div>\n      </div>\n    </div>',
        html, flags=re.DOTALL
    )

    # KPI Concorrentes
    html = re.sub(
        r'<div class="kpi gray">.*?</div>\s*</div>',
        f'<div class="kpi gray">\n      <div class="kpi-body">\n        <div class="kpi-label">Concorrentes monitorados</div>\n        <div class="kpi-value" style="color:var(--text)">{concorrentes}</div>\n        <div class="kpi-sub">Top 50 · 7 dias a frente</div>\n      </div>\n    </div>',
        html, flags=re.DOTALL
    )

    # Arrays JS
    html = re.sub(
        r'const POUSADAS = \[.*?\];',
        lambda _: f'const POUSADAS = {json.dumps(pousadas)};',
        html
    )
    html = re.sub(
        r'const SEM_PRECO = \[.*?\];',
        lambda _: f'const SEM_PRECO = {json.dumps(sem_preco)};',
        html
    )

    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"Dashboard atualizado com {len(pousadas)} pousadas e {total_registros} registros coletados em {ultima_data}.")


if __name__ == "__main__":
    atualizar_dashboard()
