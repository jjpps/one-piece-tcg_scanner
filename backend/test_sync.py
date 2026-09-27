"""Sincronização com o Binder: parser do CSV, divergências e commit num banco temporário."""
import sqlite3
import pytest
import database
from repositories import sync_repository, inventory_repository
from services import sync_service
from services.sync_service import InvalidCsvError, PendingItemsError, SessionConflictError


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = str(tmp_path / 'test.sqlite')
    for module in (database, sync_repository, inventory_repository):
        monkeypatch.setattr(module, 'DB_PATH', path)
    database.init_db()
    conn = sqlite3.connect(path)
    conn.executemany(
        'INSERT INTO cards (code, card_name, card_color, quantity) VALUES (?, ?, ?, ?)',
        [('OP07-006', 'Sterry', 'Red', 5),   # ambos, quantidades diferentes
         ('OP07-007', 'Dice', 'Red', 3),     # igual no Binder -> ignorada
         ('EB01-001', 'Kouzuki', 'Red', 4),  # só no nosso
         ('OP05-002', 'Belo', 'Red', 0)]     # quantidade 0 = não possui
    )
    conn.commit()
    conn.close()
    return path


CSV = '''quantidade,codigo,nome,set,idioma,arte_alternativa
3,OP07-006,Sterry,OP07,en,nao
3,OP07-007,Dice,OP07,en,nao
1,OP05-002,Belo,OP05,en,nao
1,OP05-002,Belo,OP05,jp,sim
2,OP99-001,Inexistente,OP99,,
3,OP99-002,Removida,OP99,,
'''


def test_parser_soma_codigos_repetidos():
    assert sync_service.parse_binder_csv(CSV)['OP05-002'] == 2


def test_parser_rejeita_arquivo_com_linha_invalida():
    with pytest.raises(InvalidCsvError) as e:
        sync_service.parse_binder_csv('quantidade,codigo\n2,OP07-006\nx,OP07-007\n1,LIXO\n')
    assert len(e.value.errors) == 2


def test_parser_exige_cabecalho():
    with pytest.raises(InvalidCsvError):
        sync_service.parse_binder_csv('qtd,code\n1,OP07-006\n')


def test_fluxo_completo(db, monkeypatch):
    monkeypatch.setattr(sync_service, 'get_card_by_code', lambda code: None)  # API não conhece OP99-001

    session_id = sync_service.start_session(CSV)['session_id']
    with pytest.raises(SessionConflictError):
        sync_service.start_session(CSV)

    items, total = sync_service.get_items_view(session_id)
    kinds = {i['code']: i['kind'] for i in items}
    assert kinds == {'OP07-006': 'both', 'EB01-001': 'ours_only', 'OP05-002': 'binder_only', 'OP99-001': 'binder_only', 'OP99-002': 'binder_only'}

    sync_service.resolve_item(session_id, 'OP07-006', 'ours')
    with pytest.raises(PendingItemsError):
        sync_service.commit(session_id)

    sync_service.resolve_item(session_id, 'EB01-001', 'ours')
    sync_service.resolve_item(session_id, 'OP99-002', 'ours')  # removemos no nosso -> sai do Binder
    assert sync_service.resolve_bulk(session_id, 'binder', kind='binder_only')['updated'] == 2

    result = sync_service.commit(session_id)
    assert result['binder_list'] == ['4xEB01-001', '2xOP07-006', '-3xOP99-002']
    assert result['failed'] == ['OP99-001']
    assert result['updated'] == 1  # OP05-002 passa de 0 para 2

    conn = sqlite3.connect(db)
    assert conn.execute("SELECT quantity FROM cards WHERE code = 'OP05-002'").fetchone()[0] == 2
    conn.close()
    assert sync_service.get_current_session() is None

