"""
parser.py — Parser unificado de cards do Google Hotels.
"""

import re
from typing import Optional
from bs4 import BeautifulSoup


def parsear_html(html: str, taxa: Optional[float] = None) -> list[dict]:
    """
    Extrai pousadas do HTML do Google Hotels.

    Args:
        html: HTML bruto da página.
        taxa: Taxa USD→BRL opcional. Se fornecida, calcula preco_brl.

    Returns:
        Lista de dicts com: nome, preco_usd, preco_brl, moeda, avaliacao, reviews.
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_=lambda c: c and "kCsInf" in c)
    resultados = []

    for card in cards:
        try:
            nome_el = card.find("h2", class_=lambda c: c and "BgYkof" in c)
            if not nome_el:
                continue
            nome = nome_el.get_text(strip=True)

            preco_usd, preco_brl, moeda = None, None, None
            for txt in card.stripped_strings:
                if "noite" in txt:
                    numeros = txt.replace("\xa0", "").replace(".", "").replace(",", ".")
                    m = re.search(r"\d+(?:\.\d+)?", numeros)
                    if m:
                        valor = float(m.group())
                        if "US$" in txt:
                            preco_usd = valor
                            moeda = "USD"
                            if taxa:
                                preco_brl = round(valor * taxa, 2)
                        elif "R$" in txt:
                            preco_brl = valor
                            moeda = "BRL"
                            preco_usd = round(valor / taxa, 2) if taxa else None
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
                "nome": nome,
                "preco_usd": preco_usd,
                "preco_brl": preco_brl,
                "moeda": moeda,
                "avaliacao": avaliacao,
                "reviews": reviews,
            })
        except Exception:
            pass

    return resultados
