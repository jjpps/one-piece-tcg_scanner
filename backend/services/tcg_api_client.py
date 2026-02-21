import requests

BASE_URL = "https://apitcg.com/api/one-piece/cards"
API_KEY = "MY-API-KEY"  # ⚠️ depois vamos mover para env

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
        return response.json()
    except requests.RequestException as e:
        print(f"Erro ao buscar carta {card_code}: {e}")
        return None