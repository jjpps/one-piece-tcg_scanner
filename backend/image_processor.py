import cv2
import pytesseract
from PIL import Image
import re
import sys
import os

# Configura caminho do executável Tesseract para Windows
if sys.platform.startswith('win'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def process_image(image_path):
    print(f"Processando: {image_path}")
    # Abre imagem
    img = cv2.imread(image_path)
    h, w, _ = img.shape

    y1_pct, y2_pct = 0.30, 0.75  
    x1_pct, x2_pct = 0.15, 0.85  
    y1, y2 = int(y1_pct * h), int(y2_pct * h)
    x1, x2 = int(x1_pct * w), int(x2_pct * w)
    carta_isolada = img[y1:y2, x1:x2]
    cv2.imwrite('carta_isolada.png', carta_isolada)
    w2, h2, _ = carta_isolada.shape
    #Gambiarra
    y_start_pct = 1509 / h2
    y_end_pct   = 1727 / h2
    x_start_pct = 881  / w2
    x_end_pct   = 1184 / w2
    
    y_start, y_end = int(y_start_pct * h2), int(y_end_pct * h2)
    x_start, x_end = int(x_start_pct * w2), int(x_end_pct * w2)

    
    #codigo_crop = carta_isolada[1509:1727, 895:1184]
    codigo_crop = carta_isolada[y_start:y_end, x_start:x_end]
    cv2.imwrite('img_codigo.png', codigo_crop)

    # Crop fixo

    # Pré-processamento: contraste
    gray = cv2.cvtColor(codigo_crop, cv2.COLOR_BGR2GRAY)
    alpha = 2.0  # contraste
    beta = 0     # brilho
    contrasted = cv2.convertScaleAbs(gray, alpha=alpha, beta=beta)

    temp_crop_path = 'temp_crop.png'
    cv2.imwrite(temp_crop_path, codigo_crop)

    pil_img = Image.open(temp_crop_path)

    whitelist = 'OPSTEB0123456789-'
    custom_config = f'--psm 6 -c tessedit_char_whitelist={whitelist}'
    text = pytesseract.image_to_string(
        pil_img,
        lang='eng',
        config=custom_config
    )

    # Pós-processamento OCR
    ocr_text = text.replace('\n', '').replace(' ', '')

    ocr_text = re.sub(r'^0P', 'OP', ocr_text)
    ocr_text = re.sub(r'^5T', 'ST', ocr_text)
    ocr_text = re.sub(r'^6B', 'EB', ocr_text)
    ocr_text = re.sub(r'([O0])P', 'OP', ocr_text)

    match = re.search(r'(OP|ST|EB)\d{2}-\d{3}', ocr_text)
    code = match.group(0) if match else None
    os.remove(temp_crop_path)
    os.remove('carta_isolada.png')
    os.remove('img_codigo.png')
    return code, ocr_text
