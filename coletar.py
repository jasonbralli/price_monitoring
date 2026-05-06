"""
coletar.py — Monitor de preços de pousadas em Peruíbe via Google Hotels
Versão 2.0 — com conversão automática USD→BRL via AwesomeAPI (gratuita)
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

# ─── Cotação USD/BRL ──────────────────────────────────────────────
def buscar_taxa_cambio() -> float:
    """
    Busca a taxa USD/BRL do dia via AwesomeAPI (gratuita, sem autenticação).
    Em caso de falha, usa taxa de fallback para não interromper a coleta.
    """
    try:
        url = "https://economia.awesomeapi.com.br/json/last/USD-BRL"
        with urlopen(url, timeout=8) as r:
            data = json.loads(r.read())
        taxa = float(data["USDBRL"]["bid"])
        log(f"  Taxa USD/BRL do dia: R$ {taxa:.4f}")
        return taxa
    except (URLError, KeyError, ValueError) as e:
        log(f"  ⚠ Não foi possível buscar cotação ({e}). Usando R$ 5,00 como fallback.")
        return 5.00

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
    return (
        "https://www.google.com/travel/hotels/Peruíbe"
        "?q=pousadas+em+peruibe+sp"
        f"&checkin={checkin}&checkout={checkout}"
        "&hl=pt-BR&gl=BR&curr=BRL"
    )

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
                    # Extrai o número
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
                "nome":       nome,
                "preco_usd":  preco_usd,
                "preco_brl":  preco_brl,
                "taxa":       taxa,
                "avaliacao":  avaliacao,
                "reviews":    reviews,
                "checkin":    checkin,
                "checkout":   checkout,
                "url":        url,
            })

        except Exception as e:
            log(f"  ⚠ Erro card: {e}")

    return resultados

# ─── Coleta de uma data ───────────────────────────────────────────
def coletar_data(page, checkin: str, checkout: str, taxa: float) -> list[dict]:
    url = montar_url(checkin, checkout)
    log(f"  → {checkin}")
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
    except PWTimeout:
        log("  ✗ Timeout")
        return []
    for _ in range(4):
        page.mouse.wheel(0, random.randint(400, 700))
        time.sleep(random.uniform(0.8, 1.5))
    return parsear_html(page.content(), checkin, checkout, url, taxa)

# ─── Main ─────────────────────────────────────────────────────────
def main():
    if ja_rodou_hoje():
        log("✓ Já executado hoje — encerrando")
        return

    log("=" * 55)
    log("Iniciando coleta — Peruíbe SP")
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
                log(f"  ✓ {len(pousadas)} pousadas | total acumulado: {total}")
                time.sleep(random.uniform(4.0, 9.0))

            browser.close()

    except Exception as e:
        status, erro_msg = "erro", str(e)
        log(f"✗ Erro fatal: {e}")

    con.execute("""
        INSERT INTO coletas (data, registros, taxa_cambio, status, mensagem)
        VALUES (?,?,?,?,?)
    """, (hoje.strftime("%Y-%m-%d"), total, taxa, status,
          erro_msg or f"{total} registros coletados"))
    con.commit()
    con.close()

    if status == "ok":
        marcar_executado()
    log(f"\n✓ Concluído — {total} registros salvos")
    log("=" * 55)

    if status == "ok":
        push_github()

if __name__ == "__main__":
    main()


# ─── Push automático para o GitHub ───────────────────────────────
def push_github():
    import subprocess
    script = Path(__file__).parent / "push_github.ps1"
    if not script.exists():
        log("⚠ push_github.ps1 não encontrado — pulando push")
        return
    log("Iniciando push para o GitHub...")
    result = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        log("✓ GitHub atualizado com sucesso")
    else:
        log(f"⚠ Erro no push: {result.stderr.strip()[:200]}")
