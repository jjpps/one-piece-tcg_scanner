import json
import re
from typing import Any

import ollama

from dtos.card_dto import Card
from dtos.deck_card_dto import DeckCard
from repositories.cards_repository import get_card_data_by_code
from services.tcg_api_client import get_card_by_code


def _parse_plain_cards(raw_list: list[str]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for line in raw_list:
        text = str(line).strip()
        if not text:
            continue

        normalized = text.strip()
        normalized = re.sub(r'^(\d+)\s*(?:x|X)\s*', r'\1 ', normalized).strip()
        normalized = re.sub(r'^(?:x|X)\s*', '', normalized).strip()

        code_match = re.search(r'([A-Z]{2,4}\d{2}-\d{3}|P-\d{3})', normalized, re.IGNORECASE)
        if not code_match:
            continue

        code = code_match.group(1).upper()
        code = re.sub(r'^X(?=[A-Z]{2,4}\d{2}-\d{3}$|P-\d{3}$)', '', code)
        quantity = 1

        quantity_prefix = re.match(r'^(\d+)\s*(?:x|X)?\s*', normalized)
        if quantity_prefix and quantity_prefix.group(1):
            quantity = int(quantity_prefix.group(1))
        else:
            for token in normalized.split():
                if token.isdigit():
                    quantity = int(token)
                    break

        cards.append({'code': code, 'quantity': quantity})

    return cards


def _extract_json_from_text(content: str) -> Any:
    if not content:
        raise ValueError('LLM response is empty')

    normalized = str(content).strip()
    if not normalized:
        raise ValueError('LLM response is empty')

    if normalized.startswith('```'):
        normalized = re.sub(r'^```(?:json|python)?\s*', '', normalized)
        normalized = re.sub(r'\s*```$', '', normalized).strip()

    for candidate in (normalized, normalized.split('```', 1)[0] if '```' in normalized else normalized):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(normalized):
        if char not in '{[':
            continue
        try:
            return decoder.raw_decode(normalized[index:])[0]
        except json.JSONDecodeError:
            continue

    raise ValueError('Could not extract a JSON object from the LLM response')


def _normalize_deck_payload_with_llm(raw_list: list[str]) -> dict[str, Any]:
    prompt = f"""
You are a strict parser for One Piece card deck lists.
Convert the provided raw entries into a single JSON object with this exact schema:
{{"deckName": "Deck", "cards": [{{"code": "XX##-###", "quantity": 1}}]}}
Rules:
- Each input line is one card entry.
- If a line starts with a number followed by whitespace or 'x', that number is the quantity.
- If a line contains a card code like OP16-080, EB04-058, ST03-017 or PRB02-012, that code is the card code.
- A card code can also be just the letter P followed by a dash and 3 digits, like P-024, with no set number.
- If a quantity is missing, use 1.
- Examples:
  - '2 EB03-021' -> {{"deckName": "Deck", "cards": [{{"code": "EB03-021", "quantity": 2}}]}}
  - '1xOP16-080' -> {{"deckName": "Deck", "cards": [{{"code": "OP16-080", "quantity": 1}}]}}
  - '4xOP09-093' -> {{"deckName": "Deck", "cards": [{{"code": "OP09-093", "quantity": 4}}]}}
  - 'OP16-080' -> {{"deckName": "Deck", "cards": [{{"code": "OP16-080", "quantity": 1}}]}}
  - '1 ST03-017' -> {{"deckName": "Deck", "cards": [{{"code": "ST03-017", "quantity": 1}}]}}
  - '3 P-024' -> {{"deckName": "Deck", "cards": [{{"code": "P-024", "quantity": 3}}]}}
  - '1 PRB02-012' -> {{"deckName": "Deck", "cards": [{{"code": "PRB02-012", "quantity": 1}}]}}
- Ignore any text that is not a card entry.
- Do not add explanations, markdown, code fences, comments, or Python syntax.
- Return ONLY one valid JSON object that can be parsed by Python json.loads().
- Do not wrap the output in ```json or ```python.
- Use deckName exactly as "Deck".
Input entries:
{json.dumps(raw_list)}
"""

    print(f"Enviando lista para a LLM: {raw_list}", flush=True)

    try:
        response = ollama.chat(
            model='llama3.2',
            messages=[{'role': 'user', 'content': prompt}],
            options={'temperature': 0}
        )
        content = response.get('message', {}).get('content', '')
        content = str(content).strip()
        print(f"LLM response: {content}", flush=True)

        parsed = _extract_json_from_text(content)
        if not isinstance(parsed, dict):
            raise ValueError('LLM response is not a JSON object')

        cards = parsed.get('cards', [])
        if not isinstance(cards, list):
            raise ValueError('LLM response cards must be a list')

        normalized_cards = []
        for item in cards:
            if not isinstance(item, dict):
                continue
            code = str(item.get('code', '')).strip().upper()
            code = re.sub(r'^X(?=[A-Z]{2,4}\d{2}-\d{3}$|P-\d{3}$)', '', code)
            quantity = item.get('quantity', 1)
            if not code:
                continue
            normalized_cards.append({
                'code': code,
                'quantity': int(quantity) if str(quantity).isdigit() else 1,
            })

        fallback_cards = _parse_plain_cards(raw_list)
        if not normalized_cards:
            normalized_cards = fallback_cards
        elif len(normalized_cards) != len(fallback_cards):
            normalized_cards = fallback_cards
        else:
            for llm_card, fallback_card in zip(normalized_cards, fallback_cards):
                if llm_card['code'] != fallback_card['code'] or llm_card['quantity'] != fallback_card['quantity']:
                    normalized_cards = fallback_cards
                    break

        return {
            'deckName': parsed.get('deckName', 'Deck'),
            'cards': normalized_cards,
        }
    except Exception as exc:
        print(f"Falha ao chamar a LLM: {exc}", flush=True)
        raise RuntimeError(f'Falha ao chamar a LLM: {exc}') from exc


def build_deck_payload_from_text(raw_text: str) -> dict[str, Any]:
    if not raw_text or not str(raw_text).strip():
        return {'deckName': 'Deck', 'cards': []}

    if isinstance(raw_text, list):
        lines = [str(line).strip() for line in raw_text if str(line).strip()]
    else:
        lines = [line.strip() for line in str(raw_text).splitlines() if line and line.strip()]

    if not lines:
        return {'deckName': 'Deck', 'cards': []}

    return _normalize_deck_payload_with_llm(lines)


def check_deck_cards(cards):
    deckCard = DeckCard.list_from_dicts(cards)
    anyCardOwned = False
    for card in deckCard:
        cardFromDb = get_card_data_by_code(card.code)
        if cardFromDb:
            card.card_name = cardFromDb.get('card_name', '')
            card.image_url = cardFromDb.get('image_url', '')
            card.quantityOwned = cardFromDb.get('quantity', 0)
            anyCardOwned = True
        else:
            cardFromApi: Card = get_card_by_code(card.code)
            if cardFromApi:
                card.card_name = cardFromApi.card_name
                card.image_url = cardFromApi.card_image
            card.quantityOwned = 0
    return anyCardOwned, deckCard
