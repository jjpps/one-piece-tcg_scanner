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

    img = cv2.imread(image_path)

    if img is None:
        return None, ""

    h, w = img.shape[:2]

    # pegar parte inferior da carta
    roi = img[int(h*0.70):h, int(w*0.40):w]

    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    thresh = cv2.threshold(
        gray,0,255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )[1]

    contours,_ = cv2.findContours(
        thresh,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    whitelist = 'OPSTEB0123456789-'
    config = f'--psm 7 -c tessedit_char_whitelist={whitelist}'

    pattern = re.compile(r'(OP|ST|EB)\d{2}-\d{3}')

    for c in contours:

        x,y,wc,hc = cv2.boundingRect(c)

        if wc < 40 or hc < 15:
            continue

        crop = thresh[y:y+hc, x:x+wc]

        text = pytesseract.image_to_string(
            crop,
            lang='eng',
            config=config
        )

        ocr = text.replace('\n','').replace(' ','').upper()

        match = pattern.search(ocr)

        if match:
            return match.group(0), ocr

    return None, ""