import re

from card_id_pattern import CARD_ID_PATTERN
from repositories import shopping_list_repository as repo
from repositories.cards_repository import get_card_data_by_code
from services.tcg_api_client import get_card_by_code
from services.upload_service import build_deck_payload_from_text


def _resolve(code: str) -> tuple[str | None, int]:
    """(nome, estoque). nome=None se a carta não existe no banco nem na API."""
    row = get_card_data_by_code(code)
    if row:
        return row['card_name'], row['quantity'] or 0
    api = get_card_by_code(code)
    return (api.card_name if api else None), 0


def _linhas_sem_codigo(text: str) -> list[str]:
    return [
        l.strip() for l in text.splitlines()
        if l.strip() and not re.search(CARD_ID_PATTERN, l, re.IGNORECASE)
    ]


def import_text(text: str) -> dict:
    # Parse antes de tocar na lista: se a LLM falhar, a lista antiga fica intacta.
    cards = build_deck_payload_from_text(text)['cards']
    pedido: dict[str, int] = {}
    for c in cards:
        pedido[c['code']] = pedido.get(c['code'], 0) + c['quantity']

    items, invalid = [], []
    for code, qtd in pedido.items():
        nome, estoque = _resolve(code)
        if nome is None:
            invalid.append({'raw': code, 'code': code, 'quantity': qtd})
            continue
        faltante = max(qtd - estoque, 0)
        if faltante:
            items.append({'code': code, 'card_name': nome, 'remaining': faltante})
    for linha in _linhas_sem_codigo(text):
        invalid.append({'raw': linha, 'code': None, 'quantity': 1})

    repo.replace_all(items)
    return {'items': items, 'invalid': invalid}


def add_item(code: str, quantity: int) -> dict:
    code = code.strip().upper()
    if not re.fullmatch(CARD_ID_PATTERN, code):
        raise ValueError('Código inválido')
    nome, estoque = _resolve(code)
    if nome is None:
        raise LookupError('Carta não encontrada')
    faltante = max(quantity - estoque, 0)
    if faltante:
        repo.add_or_sum(code, nome, faltante)
    return {'code': code, 'card_name': nome, 'remaining': faltante}
