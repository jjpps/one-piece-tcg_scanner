from repositories import inventory_repository as repo
from repositories.cards_repository import card_exists
from services.tcg_api_client import get_card_by_code


class SessionNotOpenError(Exception):
    pass


class ItemNotFoundError(Exception):
    pass


class InvalidQuantityError(Exception):
    pass


class DuplicateItemError(Exception):
    pass


class CardAlreadyInLibraryError(Exception):
    pass


class CardNotFoundError(Exception):
    pass


def _require_open_session(session_id):
    session = repo.get_session_by_id(session_id)
    if not session or session['status'] != 'open':
        raise SessionNotOpenError(f'Sessão {session_id} não está aberta')
    return session


def start_new_session():
    session_id, total = repo.create_session_with_snapshot()
    return {'session_id': session_id, 'total_items': total}


def get_current_session():
    session = repo.get_open_session()
    if not session:
        return None
    summary = repo.get_session_summary(session['id'])
    return {**session, **summary}


def get_colors_view(session_id):
    colors = repo.get_session_colors(session_id)
    for color in colors:
        color['label'] = 'Sem cor definida' if color['card_color'] == '__no_color__' else color['card_color']
        color['pending'] = color['total'] - color['reviewed']
    return colors


def get_items_view(session_id, color=None, status='pending', search=None, page=1, page_size=50):
    return repo.get_session_items(session_id, color=color, status=status, search=search, page=page, page_size=page_size)


def review_item(session_id, code, changed, counted_quantity=None):
    _require_open_session(session_id)

    if not repo.item_exists(session_id, code):
        raise ItemNotFoundError(f'Carta {code} não faz parte desta sessão')

    if changed:
        if not isinstance(counted_quantity, int) or counted_quantity < 0:
            raise InvalidQuantityError('counted_quantity precisa ser um inteiro >= 0 quando changed=true')
        return repo.mark_item_reviewed(session_id, code, True, counted_quantity)

    return repo.mark_item_reviewed(session_id, code, False, None)


def lookup_card(code):
    code = code.strip().upper()
    card = get_card_by_code(code)
    if not card:
        raise CardNotFoundError(f'Carta {code} não encontrada')
    return card


def add_new_card(session_id, code, counted_quantity):
    _require_open_session(session_id)

    if not code or not code.strip():
        raise InvalidQuantityError('code é obrigatório')
    code = code.strip().upper()

    if not isinstance(counted_quantity, int) or counted_quantity < 1:
        raise InvalidQuantityError('counted_quantity precisa ser um inteiro >= 1')

    if repo.item_exists(session_id, code):
        raise DuplicateItemError(f'Carta {code} já está na lista de auditoria')

    if card_exists(code):
        raise CardAlreadyInLibraryError(f'Carta {code} já existe na biblioteca principal')

    card = get_card_by_code(code)
    if not card:
        raise CardNotFoundError(f'Carta {code} não encontrada')

    return repo.add_new_card_item(session_id, code, card, counted_quantity)


def get_diff(session_id):
    return repo.get_session_diff(session_id)


def apply(session_id):
    _require_open_session(session_id)
    return repo.apply_session(session_id)
