"""
coletar.py — Monitor de preços de pousadas em Peruíbe via Google Hotels
Versão 2.2 — filtros via URL (menor preço + mínimo R$ 50 + moeda BRL)
Seletores validados em 06/05/2026.
"""

import sqlite3, random, re, time, json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from bs4 import BeautifulSoup

# ─── Configurações ────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
DB_PATH     = BASE_DIR / "dados" / "precos.db"
LOG_PATH    = BASE_DIR / "dados" / "log.txt"
CONTROLE    = BASE_DIR / "dados" / "ultima_coleta.txt"
JANELA_DIAS = 30
USER_AGENT  = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ─── Parâmetros de filtro codificados na URL ──────────────────────
# ts  → preço mínimo R$ 50 + ordenação por menor preço (protobuf)
# ap  → parâmetro auxiliar de filtro de preço
# qs  → estado dos filtros selecionados
# sort=13 → menor preço
# curr=BRL → moeda em Reais
URL_TS  = (
    "CAESCgoCCAMKAggDEAAaUwo1EjEyJTB4OTRkMDI2MGZkZDhiZTMyNToweDNkMTY3"
    "YTk4MDczZDJlYzc6CFBlcnXDrWJlGgASGhIUCgcI6g8QBRgZEgcI6g8QBRgaGAEy"
    "AhAAKhEKBygDOgNCUkwaACIECgIQMg"
)
URL_AP  = "MAE"
URL_QS  = "CAE4AEgA"

# ─── Cotação USD/BRL ──────────────────────────────────────────────
def buscar_taxa_cambio() -> float:
    """
    Busca a taxa USD/BRL do dia via AwesomeAPI (gratuita, sem autenticação).
    Em caso de falha, usa taxa de fallback para não interromper a coleta.
    Mantida como fallback caso a página retorne preços em USD.
    """
    try:
        url = "https://economia.awesomeapi.com.br/json/last/USD-BRL"
        with urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        taxa = float(data["USDBRL"]["bid"])
        log(f"  Taxa USD/BRL do dia: R$ {taxa:.4f}")
        return taxa
    except (URLError, KeyError, ValueError) as e:
        log(f"  Aviso: nao foi possivel buscar cotacao ({e}). Usando R$ 5,70 como fallback.")
        return 5.70

# ─── Banco de dados ───────────────────────────────────────────────
def iniciar_banco():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS precos (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            coletado_em  TEXT NOT NULL,
            checkin      TEXT NOT NULL,
            checkout     TEXT NOT NULL,
            nome         TEXT NOT NULL,
            preco_usd    REAL,
            preco_brl    REAL,
            taxa_cambio  REAL,
            avaliacao    REAL,
            reviews      TEXT,
            url          TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS coletas (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            data      TEXT NOT NULL,
            registros INTEGER,
            taxa_cambio REAL,
            status    TEXT,
            mensagem  TEXT
        )
    """)
    con.commit()
    return con

# ─── Log ──────────────────────────────────────────────────────────
def log(msg: str):
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linha = f"[{agora}] {msg}"
    print(linha)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(linha + "\n")

# ─── Controle diário ──────────────────────────────────────────────
def ja_rodou_hoje() -> bool:
    hoje = datetime.now().strftime("%Y-%m-%d")
    return CONTROLE.exists() and CONTROLE.read_text().strip() == hoje

def marcar_executado():
    CONTROLE.parent.mkdir(parents=True, exist_ok=True)
    CONTROLE.write_text(datetime.now().strftime("%Y-%m-%d"))

# ─── URL ──────────────────────────────────────────────────────────
def montar_url(checkin: str, checkout: str) -> str:
    """
    Monta a URL do Google Hotels com todos os filtros codificados:
      - curr=BRL  → preços em Reais
      - sort=13   → ordenar por menor preço
      - ts=...    → preço mínimo R$ 50 (protobuf codificado)
      - ap=MAE    → parâmetro auxiliar de filtro de preço
      - qs=...    → estado dos chips de filtro selecionados
    Apenas checkin e checkout são dinâmicos.
    """
    return (
        "https://www.google.com/travel/search"
        f"?q=pousadas+em+peruibe+sp"
        f"&qs={URL_QS}"
        f"&checkin={checkin}&checkout={checkout}"
        "&hl=pt-BR&gl=BR&curr=BRL"
        "&sort=13"
        f"&ts={URL_TS}"
        f"&ap={URL_AP}"
    )



def _scroll_pagina(page) -> None:
    """Rola toda a pagina atual para garantir que todos os cards carreguem."""
    for _ in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(random.uniform(0.6, 1.0))


def coletar_todas_paginas(page, checkin: str, checkout: str,
                          url_base: str, taxa: float) -> list[dict]:
    """
    Itera por todas as paginas de resultados clicando em 'Avancar'.
    Google Hotels exibe 18 pousadas por pagina, ~44 no total (3 paginas).
    Detecta o fim da paginacao se nao houver novos cards ou se a proxima pagina for repetida.
    """
    from playwright._impl._errors import TargetClosedError

    todos = []
    pagina = 1
    MAX_PAGINAS = 10
    nomes_vistos = set()

    try:
        while pagina <= MAX_PAGINAS:
            _scroll_pagina(page)
            resultados_pg = parsear_html(page.content(), checkin, checkout, url_base, taxa)
            
            if not resultados_pg:
                log(f"    pagina {pagina}: sem resultados. Fim da paginacao.")
                break
                
            # Verifica se e pagina repetida (loop)
            primeiro_nome = resultados_pg[0]["nome"]
            if primeiro_nome in nomes_vistos:
                log(f"    pagina {pagina}: resultados repetidos. Fim real da paginacao.")
                break
            nomes_vistos.add(primeiro_nome)

            todos.extend(resultados_pg)
            log(f"    pagina {pagina}: {len(resultados_pg)} pousadas (acumulado: {len(todos)})")

            # Seletor preciso: botao de paginacao (fora dos cards .kCsInf)
            btn = page.locator(
                "button:has-text('Avan\u00e7ar'):not(.kCsInf button), "
                "[aria-label='Avan\u00e7ar']:not(.kCsInf [aria-label])"
            ).last

            try:
                visivel = btn.is_visible(timeout=3000)
            except Exception:
                visivel = False

            if not visivel:
                # Fallback JS: clica no botao de paginacao ignorando os dos cards
                clicou = page.evaluate("""
                    () => {
                        const btns = [...document.querySelectorAll('button')];
                        const nav = btns.find(b =>
                            b.innerText.trim() === 'Avan\u00e7ar' &&
                            !b.closest('.kCsInf') &&
                            b.offsetParent !== null
                        );
                        if (nav) { nav.click(); return true; }
                        return false;
                    }
                """)
                if not clicou:
                    log(f"    Sem pagina seguinte. Total final: {len(todos)} pousadas.")
                    break
                log(f"    Avancar clicado via JS (fallback)")
            else:
                btn.scroll_into_view_if_needed()
                time.sleep(0.5)
                btn.click()

            page.wait_for_timeout(3500)
            pagina += 1
            
    except TargetClosedError:
        log(f"    Navegador fechado inesperadamente. Retornando {len(todos)} coletados.")
    except Exception as e:
        log(f"    Erro inesperado na paginacao: {e}")

    return todos


# ─── Parser (seletores validados 06/05/2026) ──────────────────────
def parsear_html(html: str, checkin: str, checkout: str,
                 url: str, taxa: float) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_=lambda c: c and "kCsInf" in c)
    resultados = []

    for card in cards:
        try:
            # Nome
            nome_el = card.find("h2", class_=lambda c: c and "BgYkof" in c)
            if not nome_el:
                continue
            nome = nome_el.get_text(strip=True)

            # Preço bruto + detecção de moeda
            preco_usd, preco_brl = None, None
            for txt in card.stripped_strings:
                if "por noite" in txt:
                    eh_usd = "US$" in txt
                    eh_brl = "R$" in txt
                    numeros = txt.replace("\xa0", "").replace(".", "").replace(",", ".")
                    m = re.search(r"\d+(?:\.\d+)?", numeros)
                    if m:
                        valor = float(m.group())
                        if eh_usd:
                            preco_usd = valor
                            preco_brl = round(valor * taxa, 2)
                        elif eh_brl:
                            preco_brl = valor
                    break

            # Avaliação e reviews
            avaliacao, reviews = None, None
            textos = list(card.stripped_strings)
            for j, txt in enumerate(textos):
                if re.match(r"^[1-5][,\.]\d$", txt.strip()):
                    try:
                        avaliacao = float(txt.strip().replace(",", "."))
                    except ValueError:
                        pass
                    if j + 1 < len(textos):
                        prox = textos[j + 1].strip()
                        if prox.startswith("(") and prox.endswith(")"):
                            reviews = prox[1:-1]
                    break

            resultados.append({
                "nome":      nome,
                "preco_usd": preco_usd,
                "preco_brl": preco_brl,
                "taxa":      taxa,
                "avaliacao": avaliacao,
                "reviews":   reviews,
                "checkin":   checkin,
                "checkout":  checkout,
                "url":       url,
            })

        except Exception as e:
            log(f"  Aviso card: {e}")

    return resultados

# ─── Coleta de uma data ───────────────────────────────────────────
def coletar_data(page, checkin: str, checkout: str, taxa: float) -> list[dict]:
    """
    Navega para a URL com filtros ja embutidos e coleta todas as paginas
    de resultados via paginacao (botao 'Avancar').
    """
    url = montar_url(checkin, checkout)
    log(f"  -> {checkin}")
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
    except PWTimeout:
        log("  Timeout na navegacao")
        return []

    page.wait_for_timeout(2500)
    return coletar_todas_paginas(page, checkin, checkout, url, taxa)

# ─── Main ─────────────────────────────────────────────────────────
def main():
    if ja_rodou_hoje():
        log("Ja executado hoje — encerrando")
        return

    log("=" * 55)
    log("Iniciando coleta — Peruibe SP")
    log("Filtros: menor preco + minimo R$ 50 + moeda BRL")
    log("=" * 55)

    taxa = buscar_taxa_cambio()
    con  = iniciar_banco()
    hoje = datetime.now()
    total, status, erro_msg = 0, "ok", ""

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
            )
            ctx = browser.new_context(
                user_agent=USER_AGENT, locale="pt-BR",
                timezone_id="America/Sao_Paulo",
                viewport={"width": 1366, "height": 768},
            )
            page = ctx.new_page()
            page.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
            )

            for delta in range(JANELA_DIAS):
                ci = (hoje + timedelta(days=delta + 1)).strftime("%Y-%m-%d")
                co = (hoje + timedelta(days=delta + 2)).strftime("%Y-%m-%d")
                pousadas = coletar_data(page, ci, co, taxa)
                agora = datetime.now().isoformat()

                # Previne duplicatas caso o script seja interrompido e reiniciado no mesmo dia
                con.execute("""
                    DELETE FROM precos 
                    WHERE date(coletado_em) = date('now', 'localtime') 
                      AND checkin = ? AND checkout = ?
                """, (ci, co))

                for p in pousadas:
                    con.execute("""
                        INSERT INTO precos
                          (coletado_em, checkin, checkout, nome,
                           preco_usd, preco_brl, taxa_cambio,
                           avaliacao, reviews, url)
                        VALUES (?,?,?,?,?,?,?,?,?,?)
                    """, (agora, p["checkin"], p["checkout"], p["nome"],
                          p["preco_usd"], p["preco_brl"], p["taxa"],
                          p["avaliacao"], p["reviews"], p["url"]))
                    total += 1

                con.commit()
                log(f"  OK {len(pousadas)} pousadas | total acumulado: {total}")
                time.sleep(random.uniform(4.0, 9.0))

            browser.close()

    except Exception as e:
        status, erro_msg = "erro", str(e)
        log(f"Erro fatal: {e}")

    con.execute("""
        INSERT INTO coletas (data, registros, taxa_cambio, status, mensagem)
        VALUES (?,?,?,?,?)
    """, (hoje.strftime("%Y-%m-%d"), total, taxa, status,
          erro_msg or f"{total} registros coletados"))
    con.commit()
    con.close()

    if status == "ok":
        marcar_executado()
        
        try:
            import atualizar_dashboard
            atualizar_dashboard.atualizar_dashboard()
            log("Dashboard HTML atualizado com sucesso.")
        except Exception as e:
            log(f"Erro ao atualizar dashboard: {e}")
            
    log(f"Concluido — {total} registros salvos")
    log("=" * 55)

if __name__ == "__main__":
    main()
