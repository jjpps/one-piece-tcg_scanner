import requests
from dtos.card_dto import Card
BASE_URL = "https://apitcg.com/api/one-piece/cards"
API_KEY = "f77838e8fb47d3e065f6e4d8330a19fb7bc76d3276545ea8f5c2efa284acf4f4" 

session = requests.Session()
session.headers.update({
    "Content-Type": "application/json",
    "x-api-key": API_KEY
})


def get_card_by_code(card_code: str):
    try:
        url = f"{BASE_URL}/{card_code}"
        response = session.get(url)
        response.raise_for_status()
        json_data = response.json()
        card_data = json_data.get("data")
        if not card_data:
            return None

        return Card.from_json(card_data)
    except requests.RequestException as e:
        print(f"Erro ao buscar carta {card_code}: {e}")
        return None