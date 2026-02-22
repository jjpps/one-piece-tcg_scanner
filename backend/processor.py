import threading
import os
import image_processor
from services.tcg_api_client import get_card_by_code
from repositories.cards_repository import save_to_db, card_exists, add_card_quantity
processing_status = {
    "total": 0,
    "current": 0,
    "processing": False
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
            print("Nenhuma imagem encontrada para processar.")
            return

        with status_lock:
            processing_status["total"] = len(files)
            processing_status["current"] = 0
            processing_status["processing"] = True

        for index, file_path in enumerate(files, start=1):
            code, ocr_text = image_processor.process_image(file_path)

            if code:
                if card_exists(code):
                    add_card_quantity(code)
                    print(f"Cartão já existe. Quantidade atualizada: {code}")
                else:
                    card = get_card_by_code(code)
                    if card:
                        save_to_db(file_path,card.code,card.images.large,card.name)                
                os.remove(file_path)
            else:
                print(f"Falha ao processar: {file_path} (OCR: {ocr_text})")
                

            with status_lock:
                processing_status["current"] = index

        with status_lock:
            processing_status["processing"] = False

    thread = threading.Thread(target=worker)
    thread.start()