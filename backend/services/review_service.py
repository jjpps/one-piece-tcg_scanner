import json
import os
import uuid
from pathlib import Path
from typing import List
from dtos.local_card_dto import LocalCard
from repositories.cards_repository import add_card_quantity, save_to_db, card_exists
from services.tcg_api_client import get_card_by_code


# the path to processed_cards.json is relative to this services directory's parent (backend)
DATA_FILE = Path(__file__).parent.parent / "processed_cards.json"
ERROR_IMAGES_FOLDER = 'images_with_errors'
IMAGES_FOLDER = "images"
CROPPED_SUBFOLDER = "cropped"  # mirrors image_tools.ocr_processor.CROPPED_SUBFOLDER


def _remover_recorte(cropped_imagem):
    """Apaga o recorte derivado da carta — não precisa sobreviver à decisão do usuário."""
    if not cropped_imagem:
        return
    cropped_filename = Path(cropped_imagem).name
    cropped_path = Path(__file__).parent.parent / IMAGES_FOLDER / CROPPED_SUBFOLDER / cropped_filename
    if cropped_path.exists():
        cropped_path.unlink()

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
            if card_exists(item.get("card_set_id")):
                add_card_quantity(item.get("card_set_id"))
            else:
                api_card = get_card_by_code(item.get("card_set_id"))
                if api_card:
                    save_to_db(api_card)
            image_filename = Path(card.local_imagem).name
            file_path = Path(__file__).parent.parent / IMAGES_FOLDER / image_filename
            if file_path.exists():
                file_path.unlink()
            _remover_recorte(item.get("cropped_imagem"))
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
            _remover_recorte(item.get("cropped_imagem"))
            data.remove(item)
            with DATA_FILE.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
    return True