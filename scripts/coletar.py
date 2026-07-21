"""
coletar.py v4.0 — Monitor de preços Peruíbe via Google Hotels
- Paginação via clique no botão "Avançar" (jsname=OCpkoe)
- Aplica filtros clicando na interface (não via URL)
- Converte USD→BRL automaticamente via taxa do dia
- Push automático para GitHub ao final
"""

from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout  # type: ignore
from bs4 import BeautifulSoup  # type: ignore
import os, sqlite3, sys, random, re, time, json, subprocess

# ─── Configurações ────────────────────────────────────────────────
PROJECT_ROOT = os.environ.get("PROJECT_ROOT")
if PROJECT_ROOT:
    BASE_DIR = Path(PROJECT_ROOT)
else:
    BASE_DIR = Path(__file__).parent.parent
DB_PATH     = BASE_DIR / "dados" / "precos.db"
LOG_PATH    = BASE_DIR / "dados" / "log.txt"
CONTROLE    = BASE_DIR / "dados" / "ultima_coleta.txt"
JANELA_DIAS = 7   # janela de coleta em dias (7–10)
MAX_PAGINAS = 3   # máx 3 páginas → ~60 cards, truncamos em 50

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# URL base — sem filtros na URL, aplicamos via clique
URL_BASE = (
    "https://www.google.com/travel/hotels/Peruíbe"
    "?q=pousadas+em+peruibe+sp"
    "&hl=pt-BR&gl=BR&curr=BRL"
)


# ─── Push GitHub ──────────────────────────────────────────────────
def push_github():
    """Atualiza dashboard e faz push para o GitHub."""
    wrapper = Path(__file__).parent / "push_github.py"
    if not wrapper.exists():
        log("  ⚠ push_github.py não encontrado — pulando push")
        return
    
    log("  Iniciando push para o GitHub...")
    result = subprocess.run(
        ["python", str(wrapper)],
        capture_output=True, text=True, errors="replace"
    )
    if result.returncode == 0:
        log("  ✓ GitHub atualizado com sucesso")
    else:
        log(f"  ⚠ Erro no push: {result.stderr.strip()[:200]}")


# ─── Cotação USD/BRL ──────────────────────────────────────────────
def buscar_taxa_cambio() -> float:
    try:
        with urlopen("https://economia.awesomeapi.com.br/json/last/USD-BRL", timeout=8) as r:
            taxa = float(json.loads(r.read())["USDBRL"]["bid"])
        log(f"  Taxa USD/BRL: R$ {taxa:.4f}")
        return taxa
    except (URLError, KeyError, ValueError) as e:
        log(f"  ⚠ Cotação indisponível ({e}). Usando R$ 5,00.")
        return 5.00


# ─── Banco de dados ───────────────────────────────────────────────
def iniciar_banco():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS precos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coletado_em TEXT NOT NULL, checkin TEXT NOT NULL, checkout TEXT NOT NULL,
            nome TEXT NOT NULL,
            preco_usd REAL,
            preco REAL,
            preco_original REAL,
            taxa_cambio REAL,
            avaliacao REAL, reviews TEXT, url TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS coletas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL,
        registros INTEGER, taxa_cambio REAL, status TEXT, mensagem TEXT)""")
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
    return CONTROLE.exists() and CONTROLE.read_text().strip() == datetime.now().strftime("%Y-%m-%d")

def marcar_executado():
    CONTROLE.parent.mkdir(parents=True, exist_ok=True)
    CONTROLE.write_text(datetime.now().strftime("%Y-%m-%d"))


# ─── Parser ───────────────────────────────────────────────────────
def parsear_html(html: str, checkin: str, checkout: str, url: str, taxa: float) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_=lambda c: c and "kCsInf" in c)
    resultados = []
    for card in cards:
        try:
            nome_el = card.find("h2", class_=lambda c: c and "BgYkof" in c)
            if not nome_el:
                continue
            nome = nome_el.get_text(strip=True)

            preco_usd, preco_brl = None, None
            text = card.get_text(" ", strip=True)

            # Busca preço sem depender da palavra "noite"
            m_preco = re.search(r'R\$\s*([\d\.]+(?:,\d+)?)', text)
            if not m_preco:
                m_preco = re.search(r'US\$\s*([\d\.]+(?:,\d+)?)', text)
            if m_preco:
                valor = float(m_preco.group(1).replace(".", "").replace(",", "."))
                if m_preco.group(0).startswith("R$"):
                    preco_brl = valor
                else:
                    preco_usd = valor
                    preco_brl = round(valor * taxa, 2)

            avaliacao, reviews = None, None
            textos = list(card.stripped_strings)
            for j, txt in enumerate(textos):
                if re.match(r"^[1-5][,\.]\d$", txt.strip()):
                    try:
                        avaliacao = float(txt.strip().replace(",", "."))
                    except Exception:
                        pass
                    if j + 1 < len(textos):
                        prox = textos[j + 1].strip()
                        if prox.startswith("(") and prox.endswith(")"):
                            reviews = prox[1:-1]
                    break

            resultados.append({
                "nome": nome, "preco_usd": preco_usd, "preco_brl": preco_brl,
                "taxa": taxa, "avaliacao": avaliacao, "reviews": reviews,
                "checkin": checkin, "checkout": checkout, "url": url,
            })
        except Exception as e:
            log(f"  ⚠ Erro card: {e}")
    return resultados


# ─── Aplicar filtros via clique ───────────────────────────────────
def aplicar_filtros(page):
    """
    Aplica filtros 'Menor preço' e 'Acima de R$50' clicando na interface.
    Executado uma única vez após carregar a primeira data.
    """
    try:
        # Fecha qualquer overlay/modal que possa estar bloqueando (cookie banner, popup)
        for sel in [
            'button:has-text("Aceitar")', 'button:has-text("Concordar")',
            'button:has-text("Reject all")', 'button:has-text("Accept all")',
            '[aria-label="Close"]', 'button:has-text("Não agora")',
        ]:
            try:
                page.click(sel, timeout=1500)
                time.sleep(0.5)
            except Exception:
                pass

        # Clica em "Todos os filtros"
        page.click('button:has-text("Todos os filtros"), button:has-text("filtros")',
                   timeout=5000)
        time.sleep(1.5)

        # Tenta clique normal primeiro; se falhar por visibilidade, usa dispatch_event
        label_sel = 'label:has-text("Menor preço"), [aria-label*="Menor preço"]'
        try:
            page.click(label_sel, timeout=3000)
        except Exception:
            el = page.query_selector(label_sel)
            if el:
                el.dispatch_event("click")
            else:
                raise RuntimeError("label 'Menor preço' não encontrado no DOM")
        time.sleep(0.8)

        # Fecha o painel de filtros
        page.keyboard.press("Escape")
        time.sleep(1.5)
        log("  ✓ Filtros aplicados via clique")
        return True
    except Exception as e:
        log(f"  ⚠ Filtros não aplicados ({e}) — continuando sem filtros")
        return False


# ─── Coleta todas as páginas de uma data ─────────────────────────
def coletar_data(page, checkin: str, checkout: str, taxa: float,
                 filtros_aplicados: bool) -> tuple[list[dict], bool]:
    """
    Retorna (lista_de_pousadas, filtros_aplicados).
    Clica em "Avançar" para paginar até não haver mais resultados.
    """
    url = f"{URL_BASE}&checkin={checkin}&checkout={checkout}"
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
    except PWTimeout:
        log("  ✗ Timeout ao carregar página")
        return [], filtros_aplicados

    time.sleep(random.uniform(2.0, 3.5))

    # Aplica filtros apenas na primeira data
    if not filtros_aplicados:
        filtros_aplicados = aplicar_filtros(page)
        time.sleep(2.0)

    todos = []
    nomes_vistos = set()
    pagina = 1

    while pagina <= MAX_PAGINAS:
        # Scroll suave para carregar lazy content
        for _ in range(3):
            page.mouse.wheel(0, random.randint(500, 800))
            time.sleep(random.uniform(0.8, 1.2))

        # Extrai cards da página atual
        pousadas = parsear_html(page.content(), checkin, checkout, page.url, taxa)
        novas = [p for p in pousadas if p["nome"] not in nomes_vistos]
        nomes_vistos.update(p["nome"] for p in novas)
        todos.extend(novas)
        log(f"    pág. {pagina}: {len(pousadas)} cards → {len(novas)} novas")

        # Limite de 50 concorrentes (já ordenados por menor preço)
        if len(todos) >= 50:
            todos = todos[:50]
            log(f"    → Limite de 50 atingido, encerrando paginação")
            break

        # Procura botão "Avançar" (jsname=OCpkoe)
        btn = page.query_selector('[jsname="OCpkoe"]')
        if not btn:
            log("    → Sem botão Avançar, última página")
            break

        # Verifica se o botão está visível e habilitado
        try:
            btn.scroll_into_view_if_needed()
            time.sleep(0.5)
            try:
                btn.click(timeout=10000)
            except Exception:
                # Overlay bloqueando — usa dispatch_event para ignorar interseção
                btn.dispatch_event("click")
            time.sleep(random.uniform(2.5, 4.0))
            pagina += 1
        except Exception as e:
            log(f"    → Não foi possível clicar em Avançar: {e}")
            break

    return todos, filtros_aplicados


# ─── Main ─────────────────────────────────────────────────────────
def main():
    if ja_rodou_hoje():
        log("✓ Já executado hoje — encerrando")
        return

    log("=" * 55)
    log("Iniciando coleta — Peruíbe SP v4.0")
    log("=" * 55)

    taxa = buscar_taxa_cambio()
    con  = iniciar_banco()
    hoje = datetime.now()
    total, status, erro_msg = 0, "ok", ""
    filtros_aplicados = False

    # Marca executado antes de qualquer operação para evitar múltiplas execuções
    marcar_executado()

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
                ci = (hoje + timedelta(days=delta+1)).strftime("%Y-%m-%d")
                co = (hoje + timedelta(days=delta+2)).strftime("%Y-%m-%d")
                log(f"  → {ci}")

                pousadas, filtros_aplicados = coletar_data(
                    page, ci, co, taxa, filtros_aplicados)

                agora = datetime.now().isoformat()
                for p in pousadas:
                    con.execute("""INSERT INTO precos
                        (coletado_em,checkin,checkout,nome,preco_usd,preco_brl,
                         taxa_cambio,avaliacao,reviews,url)
                        VALUES(?,?,?,?,?,?,?,?,?,?)""",
                        (agora,p["checkin"],p["checkout"],p["nome"],
                         p["preco_usd"],p["preco_brl"],p["taxa"],
                         p["avaliacao"],p["reviews"],p["url"]))
                    total += 1

                con.commit()
                log(f"  ✓ {len(pousadas)} pousadas | acumulado: {total}")
                time.sleep(random.uniform(4.0, 8.0))

            browser.close()

    except Exception as e:
        status, erro_msg = "erro", str(e)
        log(f"✗ Erro fatal: {e}")

    con.execute("INSERT INTO coletas (data,registros,taxa_cambio,status,mensagem) VALUES(?,?,?,?,?)",
        (hoje.strftime("%Y-%m-%d"),total,taxa,status,erro_msg or f"{total} registros"))
    con.commit()
    con.close()

    if status == "ok":
        log(f"\n✓ Concluído — {total} registros salvos")
    else:
        log(f"✗ Coleta falhou: {erro_msg}")

    log("=" * 55)

    if status == "ok":
        # Atualiza o dashboard e, se der certo, envia para o GitHub
        try:
            dashboard_script = BASE_DIR / "scripts" / "dashboard.py"
            result = subprocess.run(
                ["python", str(dashboard_script)],
                capture_output=True, text=True, errors="replace"
            )
            if result.returncode == 0:
                log(f"  ✓ {result.stdout.strip()}")
                push_github()
            else:
                log(f"  ⚠ Erro ao atualizar dashboard: {result.stderr.strip()[:200]}")
        except Exception as e:
            log(f"  ⚠ Erro ao atualizar dashboard: {e}")


if __name__ == "__main__":
    main()
