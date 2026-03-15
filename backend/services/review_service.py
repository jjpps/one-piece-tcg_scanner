import json
import os
import uuid
from pathlib import Path
from typing import List

from dtos.local_card_dto import LocalCard
from repositories.cards_repository import add_card_quantity,save_to_db


# the path to processed_cards.json is relative to this services directory's parent (backend)
DATA_FILE = Path(__file__).parent.parent / "processed_cards.json"
ERROR_IMAGES_FOLDER = 'images_with_errors'
IMAGES_FOLDER = "images"

def load_local_cards() -> List[LocalCard]:
    """Read processed_cards.json and return a list of LocalCard instances."""
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    cards: List[LocalCard] = []
    for item in data:
        try:
            cards.append(LocalCard(**item))
        except TypeError:
            # ignore invalid entries
            continue
    return cards


def get_local_cards_as_dicts() -> List[dict]:
    """Convenience helper returning list of cards as dictionaries for JSONification."""
    return [card.__dict__ for card in load_local_cards()]

def approve_card(card: LocalCard) -> bool:   
    print(f"Approving card: {card.card_name} (ID: {card.card_set_id})")
    with DATA_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        if item.get("local_imagem") == card.local_imagem:
            if item.get("exists"):
                add_card_quantity(item.get("card_set_id"))
            else:
                save_to_db(item.get("card_set_id"), item.get("card_image"), item.get("card_name"))
            data.remove(item)
            with DATA_FILE.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
    return True

def reprove_card(card: LocalCard) -> bool:   
    print(f"Reproving card: {card.card_name} (ID: {card.card_set_id})")
    with DATA_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        if item.get("local_imagem") == card.local_imagem:
            # Move image to error folder with unique filename
            image_filename = Path(card.local_imagem).name
            file_path = Path(__file__).parent.parent / IMAGES_FOLDER / image_filename
            if file_path.exists():
                file_ext = os.path.splitext(str(file_path))[1]
                unique_filename = f"{uuid.uuid4()}{file_ext}"
                new_path = Path(__file__).parent.parent / ERROR_IMAGES_FOLDER / unique_filename
                os.rename(str(file_path), str(new_path))
            data.remove(item)
            with DATA_FILE.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
    return True