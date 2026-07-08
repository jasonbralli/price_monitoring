"""
testar_coleta.py — Teste visual do scraper.
Abre o navegador com filtros ja embutidos na URL:
  - Moeda: BRL (Reais)
  - Ordenacao: Menor preco
  - Preco minimo: R$ 50
Scroll dinamico: carrega todos os resultados (40+).
NAO salva no banco.
"""

import time, random, re
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
from src.parser import parsear_html

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ─── Filtros codificados na URL ───────────────────────────────────
# Extraidos da URL real gerada pelo Google Hotels com os filtros aplicados:
#   - sort=13       → menor preco
#   - curr=BRL      → moeda em Reais
#   - ts=...        → preco minimo R$ 50 (protobuf)
#   - ap=MAE        → parametro auxiliar do filtro de preco
#   - qs=CAE4AEgA   → estado dos chips de filtro
URL_TS = (
    "CAESCgoCCAMKAggDEAAaUwo1EjEyJTB4OTRkMDI2MGZkZDhiZTMyNToweDNkMTY3"
    "YTk4MDczZDJlYzc6CFBlcnXDrWJlGgASGhIUCgcI6g8QBRgZEgcI6g8QBRgaGAEy"
    "AhAAKhEKBygDOgNCUkwaACIECgIQMg"
)
URL_AP = "MAE"
URL_QS = "CAE4AEgA"


def montar_url(checkin: str, checkout: str) -> str:
    return (
        "https://www.google.com/travel/search"
        "?q=pousadas+em+peruibe+sp"
        f"&qs={URL_QS}"
        f"&checkin={checkin}&checkout={checkout}"
        "&hl=pt-BR&gl=BR&curr=BRL"
        "&sort=13"
        f"&ts={URL_TS}"
        f"&ap={URL_AP}"
    )


def _scroll_pagina(page) -> None:
    """Rola toda a pagina atual para garantir que todos os cards visiveiscarreguem."""
    for _ in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(random.uniform(0.6, 1.0))


def coletar_todas_paginas(page) -> list[dict]:
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
            print(f"  Pagina {pagina}: carregando...")
            _scroll_pagina(page)

            pousadas = parsear_html(page.content())
            if not pousadas:
                print(f"  Pagina {pagina}: sem resultados. Fim da paginacao.")
                break
                
            # Verifica se e pagina repetida (loop)
            primeiro_nome = pousadas[0]["nome"]
            if primeiro_nome in nomes_vistos:
                print(f"  Pagina {pagina}: resultados repetidos. Fim real da paginacao.")
                break
            nomes_vistos.add(primeiro_nome)

            todos.extend(pousadas)
            print(f"  Pagina {pagina}: {len(pousadas)} pousadas (total ate agora: {len(todos)})")

            # Seletor preciso: botao de paginacao (fora dos cards .kCsInf)
            btn_proximo = page.locator(
                "button:has-text('Avan\u00e7ar'):not(.kCsInf button), "
                "[aria-label='Avan\u00e7ar']:not(.kCsInf [aria-label])"
            ).last

            try:
                visivel = btn_proximo.is_visible(timeout=3000)
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
                    print(f"  Sem pagina seguinte. Coleta encerrada.")
                    break
                print(f"  Avancar clicado via JS (fallback)")
            else:
                btn_proximo.scroll_into_view_if_needed()
                time.sleep(0.5)
                btn_proximo.click()

            page.wait_for_timeout(3500)
            pagina += 1

    except TargetClosedError:
        print(f"  Navegador fechado inesperadamente. Retornando {len(todos)} coletados.")
    except Exception as e:
        print(f"  Erro inesperado na paginacao: {e}")

    return todos


def parsear_html(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_=lambda c: c and "kCsInf" in c)
    resultados = []

    for card in cards:
        nome_el = card.find("h2", class_=lambda c: c and "BgYkof" in c)
        if not nome_el:
            continue
        nome = nome_el.get_text(strip=True)

        preco_num, moeda = None, None
        for txt in card.stripped_strings:
            if "por noite" in txt:
                moeda = "BRL" if "R$" in txt else "USD" if "US$" in txt else "?"
                m = re.search(r"[\d]+", txt.replace("\xa0", "").replace(".", ""))
                if m:
                    try:
                        preco_num = float(m.group())
                    except Exception:
                        pass
                break

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
            "nome":      nome,
            "preco":     preco_num,
            "moeda":     moeda,
            "avaliacao": avaliacao,
            "reviews":   reviews,
        })

    return resultados


def main():
    checkin  = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    checkout = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    url      = montar_url(checkin, checkout)

    print(f"\n{'='*60}")
    print("TESTE DE COLETA — Google Hotels Peruibe SP")
    print(f"{'='*60}")
    print(f"Checkin : {checkin}  |  Checkout: {checkout}")
    print(f"Filtros : menor preco + minimo R$ 50 + moeda BRL")
    print(f"URL     : {url[:80]}...")
    print()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            slow_mo=300,
            args=["--no-sandbox"],
        )
        ctx = browser.new_context(
            user_agent=USER_AGENT,
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1366, "height": 768},
        )
        page = ctx.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        )

        print("Abrindo navegador com filtros pre-aplicados na URL...")
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
        except PWTimeout:
            print("ERRO: Timeout — verifique sua conexao")
            browser.close()
            return

        # Aguarda carregamento inicial dos cards
        page.wait_for_timeout(2500)

        print("Coletando todas as paginas de resultados...")
        resultados = coletar_todas_paginas(page)
        print(f"  Total final: {len(resultados)} pousadas")

        # ── Exibe resultado ────────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"{'Nome':<45} {'Preco':>7} {'Moeda':>5} {'Aval':>5} {'Reviews':>7}")
        print("-" * 60)
        for r in resultados:
            preco_str = str(int(r["preco"])) if r["preco"] else "N/A"
            aval_str  = str(r["avaliacao"]) if r["avaliacao"] else "N/A"
            print(
                f"{r['nome'][:44]:<45} {preco_str:>7}"
                f" {r['moeda'] or '?':>5} {aval_str:>5}"
                f" {r['reviews'] or 'N/A':>7}"
            )

        print(f"\n{'='*60}")
        if resultados:
            # Verifica se os filtros funcionaram (todos BRL e >= 50)
            brl_count = sum(1 for r in resultados if r["moeda"] == "BRL")
            ok_preco  = sum(1 for r in resultados if r["preco"] and r["preco"] >= 50)
            print(f"OK {len(resultados)} pousadas encontradas!")
            print(f"   Moeda BRL    : {brl_count}/{len(resultados)}")
            print(f"   Preco >= R$50: {ok_preco}/{len(resultados)}")
            if brl_count == len(resultados) and ok_preco == len(resultados):
                print("   FILTROS FUNCIONANDO CORRETAMENTE!")
                print("   Pode rodar o coletar.py com seguranca.")
            else:
                print("   ATENCAO: alguns resultados fora do filtro.")
                print("   Salve debug_pagina.html para analise.")
                with open("debug_pagina.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
        else:
            print("ATENCAO: Nenhum resultado encontrado.")
            print("  Seletores podem ter mudado.")
            print("  Salvando debug_pagina.html para analise...")
            with open("debug_pagina.html", "w", encoding="utf-8") as f:
                f.write(page.content())
        print(f"{'='*60}\n")

        input("Pressione ENTER para fechar o navegador...")
        browser.close()


if __name__ == "__main__":
    main()
