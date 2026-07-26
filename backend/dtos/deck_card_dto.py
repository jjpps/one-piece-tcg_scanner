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
        code = item.get("code") or item.get("id") or ""
        quantity_required = (
            item.get("quantity")
            or item.get("count")
            or item.get("quantityRequired")
            or 0
        )
        return DeckCard(
            code=str(code),
            image_url=item.get("image_url", ""),
            card_name=item.get("card_name", ""),
            quantityOwned=item.get("quantityOwned", 0),
            quantityRequired=int(quantity_required) if str(quantity_required).isdigit() else 0,
        )

    @staticmethod
    def list_from_dicts(items: List[Dict[str, Any]]) -> List["DeckCard"]:
        if not isinstance(items, list):
            raise TypeError("items must be a list of dictionaries")

        return [DeckCard.from_dict(i) for i in items]