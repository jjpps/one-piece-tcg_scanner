import requests
import imagehash
from PIL import Image
from io import BytesIO
import json
from itertools import groupby

from repositories.cards_repository import (
    save_card_hash,
    save_processing_history,
    is_set_processed,
)
def create_local_data_set() :    
    with open("allCardOnePiece.json", "r", encoding="utf8") as f:
        cards = json.load(f)

    # make sure the list is sorted so groupby works correctly
    cards_sorted = sorted(cards, key=lambda x: x["set_id"])

    for set_id, group in groupby(cards_sorted, key=lambda x: x["set_id"]):
        # Skip sets that we already finished previously
        if is_set_processed(set_id):
            print(f"set {set_id} already processed, skipping")
            continue

        print(f"processing set {set_id}")
        for card in group:
            url = card["card_image"]
            code = card["card_set_id"]
            try:
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                img = Image.open(BytesIO(resp.content))
                img = img.resize((512,512))
                h = imagehash.phash(img)
                save_card_hash(code, str(h))
            except Exception as exc:
                print(f"error processing card {code} from set {set_id}: {exc}")

        # once all cards in the set have been handled, record it
        save_processing_history(set_id)
        print(f"finished set {set_id}")

