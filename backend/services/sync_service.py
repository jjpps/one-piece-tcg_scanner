import csv
import io
import re
from card_id_pattern import CARD_ID_PATTERN
from repositories import sync_repository as repo
from repositories import inventory_repository
from services.tcg_api_client import get_card_by_code

RESOLUTIONS = ('binder', 'ours', 'ignore')
KINDS = ('binder_only', 'ours_only', 'both')


class SessionNotOpenError(Exception):
    pass


class SessionConflictError(Exception):
    pass


class InvalidCsvError(Exception):
    def __init__(self, errors):
        super().__init__('CSV do Binder inválido')
        self.errors = errors


class InvalidResolutionError(Exception):
    pass


class ItemNotFoundError(Exception):
    pass


class PendingItemsError(Exception):
    pass


def parse_binder_csv(text):
    """Devolve {code: quantidade}. Soma códigos repetidos; qualquer linha inválida rejeita o arquivo."""
    reader = csv.DictReader(io.StringIO(text))
    missing = {'quantidade', 'codigo'} - set(reader.fieldnames or [])
    if missing:
        raise InvalidCsvError([f"Cabeçalho sem a(s) coluna(s): {', '.join(sorted(missing))}"])

    quantities, errors = {}, []
    for line, row in enumerate(reader, start=2):
        code = (row.get('codigo') or '').strip().upper()
        raw_qty = (row.get('quantidade') or '').strip()
        if not code and not raw_qty:
            continue
        if not re.fullmatch(CARD_ID_PATTERN, code):
            errors.append(f'Linha {line}: código inválido "{code}"')
            continue
        if not raw_qty.isdigit():
            errors.append(f'Linha {line}: quantidade inválida "{raw_qty}"')
            continue
        quantities[code] = quantities.get(code, 0) + int(raw_qty)

    if errors:
        raise InvalidCsvError(errors)
    return quantities


def _require_open_session(session_id):
    session = repo.get_session_by_id(session_id)
    if not session or session['status'] != 'open':
        raise SessionNotOpenError(f'Sincronização {session_id} não está aberta')
    return session


def get_current_session():
    session = repo.get_open_session()
    if not session:
        return None
    return {**session, **repo.get_session_summary(session['id'])}


def start_session(csv_text):
    if repo.get_open_session():
        raise SessionConflictError('Já existe uma sincronização aberta. Commite ou descarte antes de importar outro CSV.')
    if inventory_repository.get_open_session():
        raise SessionConflictError('Existe uma auditoria de inventário aberta. Aplique-a antes de sincronizar.')
    session_id, total = repo.create_session_with_divergences(parse_binder_csv(csv_text))
    return {'session_id': session_id, 'total_divergences': total}


def discard_session(session_id):
    _require_open_session(session_id)
    repo.discard_session(session_id)


def get_items_view(session_id, kind=None, color=None, status=None, search=None, page=1, page_size=50):
    return repo.get_session_items(session_id, kind, color, status, search, page, page_size)


def _validate_resolution(resolution):
    # None volta o item para pendente
    if resolution is not None and resolution not in RESOLUTIONS:
        raise InvalidResolutionError(f'resolution precisa ser um de {RESOLUTIONS} ou null')


def resolve_item(session_id, code, resolution):
    _require_open_session(session_id)
    _validate_resolution(resolution)
    if not repo.get_item(session_id, code):
        raise ItemNotFoundError(f'Carta {code} não é uma divergência desta sincronização')
    return repo.set_resolution(session_id, code, resolution)


def resolve_bulk(session_id, resolution, kind=None, color=None):
    _require_open_session(session_id)
    if resolution is None:
        raise InvalidResolutionError('resolution é obrigatória na resolução em massa')
    _validate_resolution(resolution)
    if kind and kind not in KINDS:
        raise InvalidResolutionError(f'kind precisa ser um de {KINDS}')
    return {'updated': repo.set_resolution_bulk(session_id, resolution, kind, color)}


def binder_list_line(code, delta):
    return f'{delta}x{code}'


def commit(session_id):
    _require_open_session(session_id)
    if repo.get_session_summary(session_id)['pending'] > 0:
        raise PendingItemsError('Ainda existem divergências pendentes')

    binder_wins = repo.get_resolved_items(session_id, 'binder')
    existing = repo.existing_codes([i['code'] for i in binder_wins])

    updates, new_cards, failed = [], [], []
    for item in binder_wins:
        if item['code'] in existing:
            updates.append((item['code'], item['binder_quantity']))
            continue
        # Carta nunca cadastrada: dados só vêm da API, e só no commit.
        card = get_card_by_code(item['code'])
        if card:
            new_cards.append((item['code'], card, item['binder_quantity']))
        else:
            failed.append(item['code'])

    repo.commit_session(session_id, updates, new_cards)

    binder_list = [
        binder_list_line(i['code'], i['our_quantity'] - i['binder_quantity'])
        for i in repo.get_resolved_items(session_id, 'ours')
    ]
    return {
        'updated': len(updates),
        'added': len(new_cards),
        'failed': failed,
        'binder_list': binder_list,
    }
