import requests
from dtos.card_dto import Card
API_ROOT = "https://www.optcgapi.com/api"
API_KEY = "f77838e8fb47d3e065f6e4d8330a19fb7bc76d3276545ea8f5c2efa284acf4f4"

session = requests.Session()
session.headers.update({
    "Content-Type": "application/json",
    #"x-api-key": API_KEY
})


def _resolve_base_url(card_code: str) -> str:
    code = card_code.upper()
    if code.startswith("PRB"):
        return f"{API_ROOT}/promos/card"
    if code.startswith("ST"):
        return f"{API_ROOT}/decks/card"
    if code.startswith("P"):
        return f"{API_ROOT}/promos/card"
    return f"{API_ROOT}/sets/card"


def get_card_by_code(card_code: str):
    try:
        url = f"{_resolve_base_url(card_code)}/{card_code}"
        response = session.get(url)
        response.raise_for_status()
        json_data = response.json()
        card_data = json_data[0]
        if not card_data:
            return None

        return Card.from_json(card_data)
    except requests.RequestException as e:
        print(f"Erro ao buscar carta {card_code}: {e}")
        return None