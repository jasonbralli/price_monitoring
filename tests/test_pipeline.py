"""Suite pytest — price_monitoring (auditoria 06/09/2026, M10).

Cobre a lógica pura (parser HTML, tiers de câmbio, sanidade do pipeline)
sem abrir browser nem rede. Rode da raiz: `pytest tests/ -q`
"""

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# playwright pode não estar instalado no interpretador de teste — stub mínimo,
# pois estes testes exercitam só parser/câmbio (sem browser).
try:
    import playwright.sync_api  # noqa: F401
except Exception:
    pw = types.ModuleType("playwright")
    sync_api = types.ModuleType("playwright.sync_api")

    class PWTimeout(Exception):
        pass

    sync_api.sync_playwright = None
    sync_api.TimeoutError = PWTimeout
    pw.sync_api = sync_api
    sys.modules["playwright"] = pw
    sys.modules["playwright.sync_api"] = sync_api

spec = importlib.util.spec_from_file_location("coletar", ROOT / "scripts" / "coletar.py")
coletar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coletar)


def _card(nome="Pousada Teste", preco="R$ 250", aval="4,5", reviews="(120)"):
    return f"""
    <div class="kCsInf abc">
      <h2 class="BgYkof xyz">{nome}</h2>
      <span>{preco} por noite</span>
      <span>{aval}</span>
      <span>{reviews}</span>
    </div>
    """


def test_parsear_html_preco_brl():
    res = coletar.parsear_html(_card(), "2026-09-07", "2026-09-08", "http://x", 5.0)
    assert len(res) == 1
    assert res[0]["nome"] == "Pousada Teste"
    assert res[0]["preco_brl"] == 250.0
    assert res[0]["avaliacao"] == 4.5
    assert res[0]["reviews"] == "120"


def test_parsear_html_converte_usd():
    res = coletar.parsear_html(
        _card(preco="US$ 100"), "2026-09-07", "2026-09-08", "http://x", 5.0)
    assert res[0]["preco_usd"] == 100.0
    assert res[0]["preco_brl"] == 500.0


def test_parsear_html_descarta_preco_implausivel():
    res = coletar.parsear_html(
        _card(preco="R$ 5"), "2026-09-07", "2026-09-08", "http://x", 5.0)
    assert res[0]["preco_brl"] is None
    res = coletar.parsear_html(
        _card(preco="R$ 99.999"), "2026-09-07", "2026-09-08", "http://x", 5.0)
    assert res[0]["preco_brl"] is None


def test_parsear_html_sem_cards():
    html = "<html><body>nada aqui</body></html>"
    assert coletar.parsear_html(html, "2026-09-07", "2026-09-08", "http://x", 5.0) == []


def test_buscar_ultima_taxa(tmp_path, monkeypatch):
    import sqlite3
    db = tmp_path / "t.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE coletas (id INTEGER PRIMARY KEY, taxa_cambio REAL)")
    con.execute("INSERT INTO coletas (taxa_cambio) VALUES (5.42)")
    con.commit()
    con.close()
    monkeypatch.setattr(coletar, "DB_PATH", db)
    assert coletar.buscar_ultima_taxa() == 5.42


def test_taxa_cambio_tier3_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(coletar, "DB_PATH", tmp_path / "inexistente.db")
    monkeypatch.setattr(coletar, "buscar_ultima_taxa", lambda: None)

    def _sem_rede(*a, **k):
        raise Exception("sem rede")

    monkeypatch.setattr(coletar, "urlopen", _sem_rede)
    monkeypatch.setattr(coletar, "LOG_PATH", tmp_path / "teste.log")
    assert coletar.buscar_taxa_cambio() == 5.00


def test_arquivos_pipeline():
    for f in ["scripts/coletar.py", "scripts/dashboard.py",
              "scripts/push_github.py", "scripts/check_pipeline.py",
              "scripts/run_coleta.bat", "docs/index.html"]:
        assert (ROOT / f).exists(), f"ausente: {f}"
