import threading
import os
import image_processor
from services.tcg_api_client import get_card_by_code
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

            print(f"Processando: {file_path}")

            code, ocr_text = image_processor.process_image(file_path)

            if code:
                print("buscando na api")
                print(get_card_by_code(code))

            else:
                print(f"Falha ao processar: {file_path} (OCR: {ocr_text})")

            with status_lock:
                processing_status["current"] = index

        with status_lock:
            processing_status["processing"] = False

    thread = threading.Thread(target=worker)
    thread.start()