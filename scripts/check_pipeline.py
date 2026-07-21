"""Verificação rápida do pipeline price_monitoring."""

from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]


def _ok(msg: str) -> None:
    print(f'OK  {msg}')


def _fail(msg: str) -> None:
    print(f'FAIL {msg}')


def main() -> None:
    print('== Verificacao price_monitoring ==')
    bat = PROJECT_DIR / 'scripts' / 'run_coleta.bat'
    coletar = PROJECT_DIR / 'scripts' / 'coletar.py'
    dashboard = PROJECT_DIR / 'scripts' / 'dashboard.py'
    docs_index = PROJECT_DIR / 'docs' / 'index.html'
    db = PROJECT_DIR / 'dados' / 'precos.db'
    controle = PROJECT_DIR / 'dados' / 'ultima_coleta.txt'

    if bat.exists():
        _ok(f'run_coleta.bat existe: {bat}')
    else:
        _fail(f'run_coleta.bat ausente: {bat}')

    if coletar.exists():
        _ok(f'coletar.py existe: {coletar}')
    else:
        _fail(f'coletar.py ausente: {coletar}')

    if dashboard.exists():
        _ok(f'dashboard.py existe: {dashboard}')
    else:
        _fail(f'dashboard.py ausente: {dashboard}')

    if docs_index.exists():
        _ok(f'docs/index.html existe: {docs_index}')
    else:
        _fail(f'docs/index.html ausente: {docs_index}')

    try:
        txt = bat.read_text(encoding='utf-8')
    except Exception as exc:
        _fail(f'run_coleta.bat ilegivel: {exc}')
        txt = ''
    else:
        ref = 'scripts\\coletar.py'
        if ref in txt or ref.replace('\\', '/') in txt:
            _ok('run_coleta.bat referencia scripts/coletar.py')
        else:
            _fail('run_coleta.bat NAO referencia scripts/coletar.py')

    if db.exists():
        _ok(f'banco existe: {db}')
        try:
            con = sqlite3.connect(db)
            cur = con.cursor()
            last = cur.execute('SELECT MAX(date(coletado_em)) FROM precos').fetchone()[0]
            today = date.today().isoformat()
            today_rows = cur.execute(
                'SELECT COUNT(*) FROM precos WHERE date(coletado_em) = ?',
                (today,),
            ).fetchone()[0]
            _ok(f'ultima coleta={last} | registros hoje={today_rows}')
            if last == today and today_rows == 0:
                _fail('ultima coleta e hoje, mas nao ha registros de hoje')
            con.close()
        except Exception as exc:
            _fail(f'erro ao consultar banco: {exc}')
    else:
        _fail(f'banco ausente: {db}')

    if controle.exists():
        ultima = controle.read_text(encoding='utf-8').strip()
        today = date.today().isoformat()
        if ultima == today:
            _ok(f'ultima_coleta.txt={ultima} (coleta de hoje ja marcada)')
        else:
            _fail(f'ultima_coleta.txt={ultima} (esperado {today})')
    else:
        _fail('ultima_coleta.txt ausente')

    print('== Fim ==')


if __name__ == '__main__':
    main()
