from dtos.card_dto import Card
from dtos.deck_card_dto import DeckCard
from repositories.cards_repository import get_card_data_by_code
from services.tcg_api_client import get_card_by_code



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
            cardFromApi:Card = get_card_by_code(card.code)
            if cardFromApi:
                card.card_name = cardFromApi.card_name
                card.image_url = cardFromApi.card_image
            card.quantityOwned = 0
    return anyCardOwned, deckCard
