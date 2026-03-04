from dataclasses import dataclass
from typing import Optional


@dataclass
class Card:
    card_name: str
    card_type: str
    card_cost: str
    card_power: str
    card_color: str
    rarity: str
    set_name: str
    set_id: str
    card_set_id: str
    card_text: str
    attribute: str
    sub_types: str
    counter_amount: int
    card_image: str
    card_image_id: str
    inventory_price: float
    market_price: float
    date_scraped: str
    life: Optional[str] = None

    @staticmethod
    def from_json(data: dict) -> "Card":
        return Card(
            card_name=data.get("card_name"),
            card_type=data.get("card_type"),
            card_cost=data.get("card_cost"),
            card_power=data.get("card_power"),
            card_color=data.get("card_color"),
            rarity=data.get("rarity"),
            set_name=data.get("set_name"),
            set_id=data.get("set_id"),
            card_set_id=data.get("card_set_id"),
            card_text=data.get("card_text"),
            attribute=data.get("attribute"),
            sub_types=data.get("sub_types"),
            counter_amount=data.get("counter_amount", 0),
            card_image=data.get("card_image"),
            card_image_id=data.get("card_image_id"),
            inventory_price=data.get("inventory_price", 0.0),
            market_price=data.get("market_price", 0.0),
            date_scraped=data.get("date_scraped"),
            life=data.get("life")
        )