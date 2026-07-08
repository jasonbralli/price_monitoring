"""
tests/test_scraper.py — Testes automatizados do scraper e parser.
Roda headless, sem intervenção humana.
"""

import sys
from pathlib import Path

# Garante que src/ é importável
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from playwright.sync_api import sync_playwright
from parser import parsear_html


# HTML de exemplo mínimo para validar o parser
HTML_FIXTURE = """
<div class="kCsInf">
  <h2 class="BgYkof">Pousada Teste 1</h2>
  <div>R$ 120,50 por noite</div>
  <div>4,5 (230)</div>
</div>
<div class="kCsInf">
  <h2 class="BgYkof">Pousada Teste 2</h2>
  <div>US$ 45,00 por noite</div>
  <div>4,8 (12)</div>
</div>
<div class="kCsInf">
  <h2 class="BgYkof">Pousada Sem Preço</h2>
  <div>Sem disponibilidade</div>
</div>
"""


def test_parser_fixture():
    """Valida parser com HTML de exemplo fixo."""
    resultados = parsear_html(HTML_FIXTURE, taxa=5.0)

    assert len(resultados) == 3, f"Esperado 3 resultados, got {len(resultados)}"

    r1 = resultados[0]
    assert r1["nome"] == "Pousada Teste 1"
    assert r1["moeda"] == "BRL"
    assert r1["preco_brl"] == 120.5
    assert r1["preco_usd"] == 24.1
    assert r1["avaliacao"] == 4.5
    assert r1["reviews"] == "230"

    r2 = resultados[1]
    assert r2["nome"] == "Pousada Teste 2"
    assert r2["moeda"] == "USD"
    assert r2["preco_usd"] == 45.0
    assert r2["preco_brl"] == 225.0
    assert r2["avaliacao"] == 4.8
    assert r2["reviews"] == "12"

    r3 = resultados[2]
    assert r3["nome"] == "Pousada Sem Preço"
    assert r3["moeda"] is None
    assert r3["preco_brl"] is None
    assert r3["preco_usd"] is None
    assert r3["avaliacao"] is None
    assert r3["reviews"] is None


def test_parser_sem_taxa():
    """Sem taxa, preco_brl não deve ser calculado para USD."""
    resultados = parsear_html(HTML_FIXTURE)
    r2 = resultados[1]
    assert r2["moeda"] == "USD"
    assert r2["preco_usd"] == 45.0
    assert r2["preco_brl"] is None


def test_scraper_headless():
    """Valida que o scraper headless coleta ao menos 1 pousada."""
    from coletar import coletar_data, URL_BASE, JANELA_DIAS, MAX_PAGINAS

    checkin = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    checkout = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
    url = f"{URL_BASE}&checkin={checkin}&checkout={checkout}"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.0.0 Safari/537.36",
            locale="pt-BR",
            timezone_id="America/Sao_Paulo",
            viewport={"width": 1366, "height": 768},
        )
        page = ctx.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        )
        try:
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(random.uniform(2.0, 3.5))
            pousadas, _ = coletar_data(page, checkin, checkout, 5.0, False)
        finally:
            browser.close()

    assert len(pousadas) > 0, "Nenhuma pousada coletada — verifique seletores ou conexão"
    for p in pousadas:
        assert p["nome"], "Pousada sem nome"
        assert p["preco_brl"] is not None, f"Preço BRL ausente para {p['nome']}"
        assert p["preco_brl"] > 0, f"Preço BRL inválido para {p['nome']}"
        assert p["preco_brl"] < 50000, f"Preço BRL suspeito para {p['nome']}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
