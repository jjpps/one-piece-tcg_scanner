import cv2
import pytesseract
from PIL import Image
import re
import sys

# Configura caminho do executável Tesseract para Windows
if sys.platform.startswith('win'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def process_image(image_path):
    # Abre imagem
    img = cv2.imread(image_path)
    h, w, _ = img.shape

    # Crop fixo
    crop = img[3598:3892, 1030:1388]

    # Pré-processamento: contraste
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    alpha = 2.0  # contraste
    beta = 0     # brilho
    contrasted = cv2.convertScaleAbs(gray, alpha=alpha, beta=beta)

    temp_crop_path = 'temp_crop.png'
    cv2.imwrite(temp_crop_path, crop)

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

    return code, ocr_text
