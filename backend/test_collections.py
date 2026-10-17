"""Completude por colecao: total vem do catalogo uma vez; falha da API nao derruba nada.

Rodar de backend/: python test_collections.py
"""
import os
import sys
import tempfile
import types

sys.modules['llm_client'] = types.SimpleNamespace(chat_text=lambda *a, **k: '')

import database
from repositories import collections_repository as repo
from services import collection_service as service


def novo_banco(owned):
    service._tried.clear()
    path = os.path.join(tempfile.mkdtemp(), 't.sqlite')
    for mod in (database, repo):
        mod.DB_PATH = path
    database.init_db()
    conn = __import__('sqlite3').connect(path)
    with conn:
        for code, qty in owned:
            conn.execute('INSERT INTO cards (code, quantity) VALUES (?, ?)', (code, qty))
    conn.close()


def demo():
    chamadas = []

    def catalogo():
        chamadas.append(1)
        return ['OP01-001', 'OP01-001', 'OP01-002', 'EB04-001', 'PRB02-001', 'P-001']

    service.tcg_api_client = types.SimpleNamespace(get_catalog_codes=catalogo)

    # possuir = quantidade >= 1; qtd 0 nao conta; PRB e P ficam fora; total conta codigos distintos
    novo_banco([('OP01-001', 3), ('OP01-002', 0), ('PRB02-001', 1), ('P-001', 1)])
    assert service.tracker() == [{'prefix': 'OP01', 'owned': 1, 'total': 2}]

    # total gravado: nao busca de novo
    service.tracker()
    assert len(chamadas) == 1

    # API fora: tracker responde com total None
    def falha():
        raise RuntimeError('fora')
    service.tcg_api_client = types.SimpleNamespace(get_catalog_codes=falha)
    novo_banco([('EB04-001', 1)])
    assert service.tracker() == [{'prefix': 'EB04', 'owned': 1, 'total': None}]

    # falhou uma vez: nao tenta de novo ate reiniciar
    service.tcg_api_client = types.SimpleNamespace(get_catalog_codes=lambda: chamadas.append(2) or ['EB04-001'])
    service.tracker()
    assert 2 not in chamadas

    print('ok')


if __name__ == '__main__':
    demo()
