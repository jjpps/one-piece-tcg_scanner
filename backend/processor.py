import threading
import os
import uuid
from pathlib import Path
from dtos.local_card_dto import LocalCard
from image_tools import ocr_processor
from services.tcg_api_client import get_card_by_code
from repositories.cards_repository import card_exists, get_card_data_by_code
import json
ERROR_IMAGES_FOLDER = 'images_with_errors'


def _descartar_recorte(cropped_path):
    """Remove o recorte gerado para uma carta que não vai para a tela de review."""
    if cropped_path and Path(cropped_path).exists():
        Path(cropped_path).unlink()
processing_status = {
    "total": 0,
    "current": 0,
    "processing": False,
    "anyErrors": False
}

status_lock = threading.Lock()


def get_status():
    with status_lock:
        return processing_status.copy()



def start_processing(folder_path):

    def worker():
        allowed_extensions = ('.png', '.jpg', '.jpeg')
        files = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.lower().endswith(allowed_extensions)
        ]

        if not files:
            with status_lock:
                processing_status["total"] = 0
                processing_status["current"] = 0
                processing_status["processing"] = False            
            return

        with status_lock:
            processing_status["total"] = len(files)
            processing_status["current"] = 0
            processing_status["processing"] = True
        localCards = []
        for index, file_path in enumerate(files, start=1):
            code, ocr_text, cropped_path = ocr_processor.process_image(file_path)

            if code:
                if card_exists(code):
                    card_data = get_card_data_by_code(code)
                    localCards.append(LocalCard(file_path,card_data['image_url'],card_data['card_name'],code,True,cropped_path or ""))
                else:
                    card = get_card_by_code(code)
                    if card:
                        localCards.append(LocalCard(file_path,card.card_image,card.card_name,code,False,cropped_path or ""))
                    else:
                        _descartar_recorte(cropped_path)
                        file_ext = os.path.splitext(file_path)[1]
                        unique_filename = f"{uuid.uuid4()}{file_ext}"
                        os.rename(file_path, os.path.join(ERROR_IMAGES_FOLDER, unique_filename))
            else:
                _descartar_recorte(cropped_path)
                file_ext = os.path.splitext(file_path)[1]
                unique_filename = f"{uuid.uuid4()}{file_ext}"
                os.rename(file_path, os.path.join(ERROR_IMAGES_FOLDER, unique_filename))
                with status_lock:
                    processing_status["anyErrors"] = True


            with status_lock:
                processing_status["current"] = index
        existing_data = []
        if os.path.exists('processed_cards.json'):
            with open('processed_cards.json', 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        new_data = [card.__dict__ for card in localCards]
        combined_data = existing_data + new_data
        string_json = json.dumps(combined_data, ensure_ascii=False)
        with open('processed_cards.json', 'w', encoding='utf-8') as f:
            f.write(string_json)        

        with status_lock:
            processing_status["processing"] = False

    thread = threading.Thread(target=worker)
    thread.start()
