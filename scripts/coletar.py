"""
coletar.py v4.1 — Monitor de preços Peruíbe via Google Hotels
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
LOCK_PATH   = BASE_DIR / "dados" / "coleta.lock"  # anti-concorrência (v4.1)
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
        [sys.executable, str(wrapper)],
        capture_output=True, text=True, errors="replace"
    )
    if result.returncode == 0:
        log("  ✓ GitHub atualizado com sucesso")
    else:
        log(f"  ⚠ Erro no push: {result.stderr.strip()[:200]}")


# ─── Cotação USD/BRL (3 tiers: API → última válida → 5,00) ──────────
def buscar_ultima_taxa() -> float | None:
    """Tier 2: última taxa válida gravada em coletas (ignora hardcoded 5,00)."""
    try:
        if not DB_PATH.exists():
            return None
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        row = con.execute(
            "SELECT taxa_cambio FROM coletas "
            "WHERE taxa_cambio IS NOT NULL AND ABS(taxa_cambio - 5.0) > 0.0001 "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        con.close()
        if row and row[0]:
            taxa = float(row[0])
            if 3.0 < taxa < 8.0:
                return taxa
        return None
    except Exception:
        return None


def buscar_taxa_cambio() -> float:
    # Tier 1: API atualizada
    try:
        with urlopen("https://economia.awesomeapi.com.br/json/last/USD-BRL", timeout=8) as r:
            taxa = float(json.loads(r.read())["USDBRL"]["bid"])
        if not 3.0 < taxa < 8.0:
            raise ValueError(f"taxa implausivel: {taxa}")
        log(f"  Taxa USD/BRL: R$ {taxa:.4f}")
        return taxa
    except Exception as e:
        log(f"  ⚠ API falhou ({e}) — buscando última válida...")
    # Tier 2: última cotação válida do banco
    ultima = buscar_ultima_taxa()
    if ultima is not None:
        log(f"  Taxa reutilizada: R$ {ultima:.4f}")
        return ultima
    # Tier 3: hardcoded
    log("  ⚠ Sem histórico. Usando R$ 5,00.")
    return 5.00


# ─── Conversão de moedas (v4.4) ──────────────────────────────────
# O Google detecta a moeda pelo IP da VPN e ignora curr=BRL da URL
# (ex.: nó no Canadá → preços em CA$). Detectamos a moeda no card e
# convertemos para BRL via AwesomeAPI.
_cache_taxas: dict = {}

# Símbolo no card (2 letras) → código ISO 3 letras (para a API AwesomeAPI)
ISO_MAP = {
    "US": "USD", "CA": "CAD", "EU": "EUR", "GB": "GBP", "MX": "MXN",
    "AR": "ARS", "CL": "CLP", "CO": "COP", "PE": "PEN", "CH": "CHF",
    "JP": "JPY", "CN": "CNY", "IN": "INR", "AU": "AUD", "NZ": "NZD",
}

def taxa_para_brl(cod: str, taxa_usd: float) -> float | None:
    """Taxa de conversão moeda→BRL. BRL=1, USD usa a taxa já obtida,
    demais: AwesomeAPI {COD}-BRL; fallback {COD}-USD * taxa_usd."""
    cod = cod.upper()
    if cod == "BRL":
        return 1.0
    if cod == "USD":
        return taxa_usd
    if cod not in _cache_taxas:
        t = None
        try:
            with urlopen(f"https://economia.awesomeapi.com.br/json/last/{cod}-BRL", timeout=8) as r:
                j = json.loads(r.read())
                v = float(j[f"{cod}BRL"]["bid"])
                if 0.1 < v < 50:
                    t = v
        except Exception:
            pass
        if t is None:
            # Fallback: AwesomeAPI em 429 (cota estourada no IP da VPN) →
            # open.er-api.com (gratuito, sem cota agressiva).
            try:
                with urlopen(f"https://open.er-api.com/v6/latest/{cod}", timeout=8) as r:
                    j = json.loads(r.read())
                    v = float(j["rates"]["BRL"])
                    if 0.1 < v < 50:
                        t = v
            except Exception:
                t = None
        if t is None:
            # Último recurso: {COD}-USD * taxa_usd (só se AwesomeAPI responder)
            try:
                with urlopen(f"https://economia.awesomeapi.com.br/json/last/{cod}-USD", timeout=8) as r:
                    j = json.loads(r.read())
                    t = float(j[f"{cod}USD"]["bid"]) * taxa_usd
            except Exception:
                t = None
        if t:
            log(f"  Moeda {cod} detectada — taxa {t:.4f} BRL")
        _cache_taxas[cod] = t
    return _cache_taxas[cod]


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
    con.execute("CREATE INDEX IF NOT EXISTS idx_precos_coletado ON precos(coletado_em)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_coletas_data ON coletas(data)")
    con.commit()
    return con


# ─── Log ──────────────────────────────────────────────────────────
def log(msg: str):
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linha = f"[{agora}] {msg}"
    print(linha)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:  # rotação simples: cap 500 KB, mantém últimas 2000 linhas (v4.1)
        if LOG_PATH.exists() and LOG_PATH.stat().st_size > 500 * 1024:
            linhas = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
            LOG_PATH.write_text("\n".join(linhas[-2000:]) + "\n", encoding="utf-8")
    except Exception:
        pass
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

            # v4.4: preço em qualquer moeda (o Google detecta a moeda pelo
            # IP da VPN — pode vir R$, US$, CA$ etc., mesmo com curr=BRL).
            # Prefere o valor "por noite"; senão, o primeiro preço do card.
            m_preco = re.search(
                r'([A-Z]{2,3}\$|R\$)\s*([\d.]+(?:,\d+)?)\s*por noite', text)
            if not m_preco:
                m_preco = re.search(r'([A-Z]{2,3}\$|R\$)\s*([\d.]+(?:,\d+)?)', text)
            if m_preco:
                moeda = m_preco.group(1)
                cod = "BRL" if moeda.startswith("R") else moeda.rstrip("$")
                cod = ISO_MAP.get(cod, cod)
                valor = float(m_preco.group(2).replace(".", "").replace(",", "."))
                t_conv = taxa_para_brl(cod, taxa)
                if t_conv:
                    preco_brl = round(valor * t_conv, 2)
                    if cod == "USD":
                        preco_usd = valor
                    if not 30.0 <= preco_brl <= 10000.0:
                        preco_brl = None  # fora da faixa diária plausível (taxa/imposto?)

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
    ultimo_html = ""

    while pagina <= MAX_PAGINAS:
        # Scroll suave para carregar lazy content
        for _ in range(3):
            page.mouse.wheel(0, random.randint(500, 800))
            time.sleep(random.uniform(0.8, 1.2))

        # Aguarda os preços renderizarem (carregam de forma assíncrona no
        # Google; o snapshot inicial pode vir SEM preço → 0 registros com
        # preço e o dashboard trava no dia anterior. v4.2)
        # v4.4: aceita qualquer símbolo de moeda (o IP da VPN pode mudar a
        # moeda exibida — CA$, US$ etc.)
        for _ in range(12):  # até ~6s
            try:
                if re.search(r'(R\$|[A-Z]{2,3}\$)\s*\d', page.evaluate("() => document.body.innerText")):
                    break
            except Exception:
                break
            time.sleep(0.5)

        # Extrai cards da página atual
        html_atual = page.content()
        ultimo_html = html_atual
        pousadas = parsear_html(html_atual, checkin, checkout, page.url, taxa)
        if pagina == 1 and not pousadas:
            try:
                (BASE_DIR / "dados" / "debug_pagina.html").write_text(
                    html_atual, encoding="utf-8", errors="replace")
                log("    ⚠ 0 cards na pág.1 — HTML salvo em dados/debug_pagina.html (seletores?)")
            except Exception:
                pass
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
    log("Iniciando coleta — Peruíbe SP v4.1")
    log("=" * 55)

    taxa = buscar_taxa_cambio()
    con  = iniciar_banco()
    hoje = datetime.now()
    total, status, erro_msg = 0, "ok", ""
    filtros_aplicados = False

    # Lock anti-concorrência (dia só é marcado após sucesso — ver final do main)
    if LOCK_PATH.exists():
        try:
            idade = time.time() - LOCK_PATH.stat().st_mtime
        except Exception:
            idade = 0
        if idade > 7200:
            log("⚠ Lock obsoleto (>2h) — removendo e continuando")
            try:
                LOCK_PATH.unlink()
            except Exception:
                pass
        else:
            log("⚠ Outra coleta em andamento (coleta.lock) — encerrando")
            con.close()
            return
    LOCK_PATH.write_text(datetime.now().isoformat())

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

                # v4.3: se nenhum preço veio, tenta recarregar 1x com wait extra
                sem_preco = [p for p in pousadas if p["preco_brl"] is None]
                if sem_preco:
                    log(f"    ⚠ {len(sem_preco)} cards sem preco — tentando reload...")
                    try:
                        page.reload()
                        time.sleep(3)
                        pousadas, filtros_aplicados = coletar_data(
                            page, ci, co, taxa, filtros_aplicados)
                    except Exception as e:
                        log(f"    ⚠ Erro no retry: {e}")

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

    if status == "ok" and total == 0:
        status, erro_msg = "aviso", "0 cards em todas as datas — ver dados/debug_pagina.html"
        log(f"⚠ {erro_msg}")

    con.execute("INSERT INTO coletas (data,registros,taxa_cambio,status,mensagem) VALUES(?,?,?,?,?)",
        (hoje.strftime("%Y-%m-%d"),total,taxa,status,erro_msg or f"{total} registros"))
    con.commit()
    con.close()

    if status == "ok":
        marcar_executado()  # dia só é marcado após sucesso (v4.1)
        log(f"\n✓ Concluído — {total} registros salvos")
    else:
        log(f"✗ Coleta falhou: {erro_msg} — dia NÃO marcado, retentativa liberada")

    try:  # libera lock sempre
        if LOCK_PATH.exists():
            LOCK_PATH.unlink()
    except Exception:
        pass

    log("=" * 55)

    if status == "ok":
        # Atualiza o dashboard e, se der certo, envia para o GitHub
        try:
            dashboard_script = BASE_DIR / "scripts" / "dashboard.py"
            result = subprocess.run(
                [sys.executable, str(dashboard_script)],
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
