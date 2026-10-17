"""Completude por colecao (prefixo OP17, EB03, ST01...). PRB e P-### ficam fora: total nao confiavel na API."""
import re
from collections import Counter

from repositories import collections_repository as repo
from services import tcg_api_client

_tried: set[str] = set()  # cada prefixo e tentado uma vez por processo
PREFIX = re.compile(r'^((?:OP|EB|ST)\d{2})-')


def _prefix(code: str):
    m = PREFIX.match(code or '')
    return m.group(1) if m else None


def _owned_by_prefix() -> Counter:
    return Counter(p for p in map(_prefix, repo.owned_codes()) if p)


def sync_missing() -> None:
    """Busca o catalogo se alguma colecao do estoque ainda nao tem total. Falha de API: tenta no proximo startup."""
    # ponytail: sem retry em falha (decisao do usuario); sync tambem roda sob demanda em tracker()
    missing = set(_owned_by_prefix()) - set(repo.totals()) - _tried
    if not missing:
        return
    _tried.update(missing)
    try:
        catalog = {c for c in tcg_api_client.get_catalog_codes()}
    except Exception as e:
        print(f'Erro ao sincronizar colecoes: {e}')
        return
    counts = Counter(p for p in map(_prefix, catalog) if p)
    repo.save_totals({p: counts[p] for p in missing if p in counts})


def tracker() -> list[dict]:
    sync_missing()
    totals = repo.totals()
    return [
        {'prefix': p, 'owned': n, 'total': totals.get(p)}
        for p, n in _owned_by_prefix().items()
    ]
