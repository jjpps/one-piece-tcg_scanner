from dataclasses import dataclass
from typing import Optional, List


@dataclass
class CardImages:
    small: str
    large: str


@dataclass
class CardAttribute:
    name: str
    image: str


@dataclass
class CardSet:
    name: str


@dataclass
class Card:
    id: str
    code: str
    rarity: str
    type: str
    name: str
    images: CardImages
    cost: Optional[int]
    attribute: Optional[CardAttribute]
    power: Optional[int]
    counter: Optional[str]
    color: Optional[str]
    family: Optional[str]
    ability: Optional[str]
    trigger: Optional[str]
    set: Optional[CardSet]
    notes: List[str]

    @staticmethod
    def from_json(data: dict) -> "Card":
        return Card(
            id=data.get("id"),
            code=data.get("code"),
            rarity=data.get("rarity"),
            type=data.get("type"),
            name=data.get("name"),
            images=CardImages(**data.get("images", {})),
            cost=data.get("cost"),
            attribute=CardAttribute(**data["attribute"]) if data.get("attribute") else None,
            power=data.get("power"),
            counter=data.get("counter"),
            color=data.get("color"),
            family=data.get("family"),
            ability=data.get("ability"),
            trigger=data.get("trigger"),
            set=CardSet(**data["set"]) if data.get("set") else None,
            notes=data.get("notes", [])
        )