from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class DeckCard:
    code: str
    image_url: str
    card_name: str
    quantityOwned: int
    quantityRequired: int

    @staticmethod
    def from_dict(item: Dict[str, Any]) -> "DeckCard":
        return DeckCard(
            code=item.get("id", ""),
            image_url=item.get("image_url", ""),
            card_name=item.get("card_name", ""),
            quantityOwned=item.get("quantityOwned", 0),
            quantityRequired=item.get("count", 0),
        )

    @staticmethod
    def list_from_dicts(items: List[Dict[str, Any]]) -> List["DeckCard"]:
        if not isinstance(items, list):
            raise TypeError("items must be a list of dictionaries")

        return [DeckCard.from_dict(i) for i in items]