import os
import sqlite3
from PIL import Image
import pytesseract
import sys
import cv2
import re
DB_PATH = 'db.sqlite'
IMAGES_DIR = 'images'

# Configura caminho do executável Tesseract para Windows
if sys.platform.startswith('win'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Inicializa banco de dados

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        code TEXT NOT NULL,
        processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        croped_image TEXT default NULL
    )''')
    conn.commit()
    conn.close()

# Processa uma imagem

def process_image(image_path):
    # Abre imagem
    img = cv2.imread(image_path)
    h, w, _ = img.shape
    # Crop maior (20% da altura e 40% da largura)
    crop = img[3598:3892,1030:1388]
    cv2.imwrite('crop_debug.png', crop)  # Salva crop para debug
    # Pré-processamento: apenas aumento de contraste
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    alpha = 2.0  # contraste
    beta = 0    # brilho
    contrasted = cv2.convertScaleAbs(gray, alpha=alpha, beta=beta)
    # Binarização após contraste
    #_, thresh = cv2.threshold(contrasted, 120, 255, cv2.THRESH_BINARY)
    temp_crop_path = 'temp_crop.png'
    cv2.imwrite(temp_crop_path, contrasted)
    pil_img = Image.open(temp_crop_path)
    whitelist = 'OPSTEB0123456789-'
    custom_config = f'--psm 6 -c tessedit_char_whitelist={whitelist}'
    text = pytesseract.image_to_string(pil_img, lang='eng', config=custom_config)
    os.remove(temp_crop_path)
    # Pós-processamento para corrigir confusões comuns do OCR
    ocr_text = text.replace('\n', '').replace(' ', '')
    # Corrige 0P para OP, 5T para ST, 6B para EB no início
    ocr_text = re.sub(r'^0P', 'OP', ocr_text)
    ocr_text = re.sub(r'^5T', 'ST', ocr_text)
    ocr_text = re.sub(r'^6B', 'EB', ocr_text)
    # Corrige outros erros comuns (zero por O, etc.)
    ocr_text = re.sub(r'([O0])P', 'OP', ocr_text)
    # Extrai código (regex)
    match = re.search(r'(OP|ST|EB)\d{2}-\d{3}', ocr_text)
    code = match.group(0) if match else None
    return code, ocr_text

# Salva no banco

def save_to_db(filename, code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO cards (filename, code) VALUES (?, ?)', (filename, code))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(('.jpg', '.png','.jpeg'))]
    if not files:
        print('Nenhuma imagem encontrada em images/')
    else:
        for fname in files:
            fpath = os.path.join(IMAGES_DIR, fname)
            code, raw_text = process_image(fpath)
            print(f'Arquivo: {fname}\nTexto OCR: {raw_text}\nCódigo extraído: {code}')
            if code:
                #save_to_db(fname, code)
                print('Salvo no banco.')
            else:
                print('Código não encontrado.')
