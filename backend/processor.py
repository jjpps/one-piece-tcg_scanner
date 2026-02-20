import threading
import os
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

        # Buscar todas as imagens válidas na pasta
        allowed_extensions = ('.png', '.jpg', '.jpeg')

        files = [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.lower().endswith(allowed_extensions)
        ]

        with status_lock:
            processing_status["total"] = len(files)
            processing_status["current"] = 0
            processing_status["processing"] = True

        for index, file_path in enumerate(files, start=1):

            print(f"Processando: {file_path}")
            
            # ============================
            # Aqui entra a chamada do OCR
            # ex:
            # code, raw_text = process_image(file_path)
            # ============================

            with status_lock:
                processing_status["current"] = index

        with status_lock:
            processing_status["processing"] = False

    thread = threading.Thread(target=worker)
    thread.start()