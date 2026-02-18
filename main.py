import os
import base64
import sqlite3
from PIL import Image
import pytesseract
import sys
import cv2
import re
import pandas as pd
import base64
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
import io

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
    #cv2.imwrite('crop_debug.png', crop)  # Salva crop para debug
    # Pré-processamento: apenas aumento de contraste
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    alpha = 2.0  # contraste
    beta = 0    # brilho
    contrasted = cv2.convertScaleAbs(gray, alpha=alpha, beta=beta)
    # Binarização após contraste
    #_, thresh = cv2.threshold(contrasted, 120, 255, cv2.THRESH_BINARY)
    temp_crop_path = 'temp_crop.png'
    #cv2.imwrite(temp_crop_path, contrasted)
    cv2.imwrite(temp_crop_path, crop)
    pil_img = Image.open(temp_crop_path)
    whitelist = 'OPSTEB0123456789-'
    custom_config = f'--psm 6 -c tessedit_char_whitelist={whitelist}'
    text = pytesseract.image_to_string(pil_img, lang='eng', config=custom_config)
    #os.remove(temp_crop_path)
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

def save_to_db(filename, code, croped_image=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO cards (filename, code, croped_image) VALUES (?, ?, ?)', (filename, code, croped_image))
    conn.commit()
    conn.close()

def export_to_excel():
   
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query('SELECT * FROM cards', conn)
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = 'Cartas'

    # Cabeçalhos
    headers = list(df.columns)
    ws.append(headers)

    for idx, row in df.iterrows():
        values = list(row.values)
        # Temporariamente, coloque string vazia na coluna da imagem
        if isinstance(values[-1], str) and values[-1].strip():
            values[-1] = ''
        ws.append(values)

    # Inserir imagens nas células
    for idx, row in df.iterrows():
        crop_val = row['croped_image']
        if isinstance(crop_val, str) and crop_val.strip():
            try:
                img_data = base64.b64decode(crop_val)
                img_stream = io.BytesIO(img_data)
                img = XLImage(img_stream)
                # openpyxl é 1-indexado, +2 por causa do cabeçalho
                cell = f'F{idx+2}'
                ws.add_image(img, cell)
            except Exception as e:
                print(f'Erro ao inserir imagem do id {row["id"]}: {e}')

    wb.save('cartas_export.xlsx')
    print('Exportação concluída: cartas_export.xlsx (com imagens embutidas)')

def view_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, filename, code, processed_at,croped_image FROM cards')
    rows = c.fetchall()
    conn.close()
    if not rows:
        print('Banco de dados vazio.')
    else:
        print('\nBanco de Dados:')
        for row in rows:
            print(f'ID: {row[0]}, Arquivo: {row[1]}, Código: {row[2]}, Processado em: {row[3]} , Crop: {row[4]}')

def menu():
    init_db()
    while True:
        print('\nMenu:')
        print('1 - Escanear cartas')
        print('2 - Extrair para Excel')
        print('3 - Ver Banco de Dados (SQLite)')
        print('0 - Sair')
        op = input('Escolha uma opção: ')
        if op == '1':            
            files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(('.jpg', '.png','.jpeg'))]
            if not files:
                print('Nenhuma imagem encontrada em images/')
            else:
                for fname in files:
                    fpath = os.path.join(IMAGES_DIR, fname)
                    code, raw_text = process_image(fpath)                    
                    if code:
                        save_to_db(fname, code)
                        print('Salvo no banco.')
                    else:                        
                        with open('temp_crop.png', 'rb') as img_file:
                            crop_b64 = base64.b64encode(img_file.read()).decode('utf-8')
                        save_to_db(fname, 'NOT_FOUND', crop_b64)
                        print('Código não encontrado. Crop salvo no banco.')
        elif op == '2':
            export_to_excel()
        elif op == '3':
            view_db()
        elif op == '0':
            print('Saindo...')
            break
        elif op == '0':
            print('Saindo...')
            break
        else:
            print('Opção inválida.')

if __name__ == '__main__':
    menu()
