import cv2
import re
import numpy as np
import pytesseract
from image_tools.llm_processor import _extrair_id_via_llm
import repositories.cards_hash_repository as cards_hash_repository
from PIL import Image
import sys

ID_REGION = {'y1': 0.85, 'y2': 0.97, 'x1': 0.55, 'x2': 0.92}
 
# Padrão do ID das cartas One Piece (ex: EB03-021, OP01-001, ST01-001)
ID_PATTERN = re.compile(r'[A-Z]{2,4}\d{2}-\d{3}')
 
# Configuração do Tesseract — linha única, só chars do ID
TESS_CONFIG = '--psm 6 -c tessedit_char_whitelist=OPSTEB0123456789-'

# Configura caminho do executável Tesseract para Windows
if sys.platform.startswith('win'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def _contorno_carta(img):
    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
 
    img_area = img.shape[0] * img.shape[1]
    candidatos = []
    for c in contours:
        area = cv2.contourArea(c)
        if not (img_area * 0.1 < area < img_area * 0.9):
            continue
        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(approx) == 4:
            candidatos.append((c, area))
 
    return max(candidatos, key=lambda x: x[1])[0] if candidatos else None

 
def _recortar_contorno(img, contour):
    x, y, w, h = cv2.boundingRect(contour)
    m = 5
    x, y = max(0, x - m), max(0, y - m)
    w = min(img.shape[1] - x, w + 2 * m)
    h = min(img.shape[0] - y, h + 2 * m)
    return img[y:y+h, x:x+w]
 
 
def extrair_carta(img):
    """Extrai a carta da foto. Tenta contorno; cai para recorte fixo."""
    try:
        contour = _contorno_carta(img)
        if contour is not None:
            card = _recortar_contorno(img, contour)
            if card.shape[0] > 50 and card.shape[1] > 50:
                cv2.imwrite("debug_detected_card.jpg", card)
                return card, "contour"
    except Exception as e:
        print(f"Contorno falhou: {e}")
 
    h, w = img.shape[:2]
    card = img[int(0.38*h):int(0.86*h), int(0.01*w):int(0.88*w)]
    cv2.imwrite("debug_detected_card.jpg", card)
    return card, "percentage"
 
 
# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------
 
def _preprocessar_para_ocr(regiao_cv):
    """Aumenta e binariza a região para melhorar leitura do Tesseract."""
    gray = cv2.cvtColor(regiao_cv, cv2.COLOR_BGR2GRAY)
 
    # Upscale 3x — texto pequeno precisa de mais pixels pro OCR funcionar
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
 
    # Binarização adaptativa — lida melhor com variações de iluminação
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )
    return thresh
 
 
def extrair_id_por_ocr(carta_cv):
    h, w = carta_cv.shape[:2]

    y1 = int(ID_REGION['y1'] * h)
    y2 = int(ID_REGION['y2'] * h)
    x1 = int(ID_REGION['x1'] * w)
    x2 = int(ID_REGION['x2'] * w)

    regiao = carta_cv[y1:y2, x1:x2]

    gray = cv2.cvtColor(regiao, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

    # Inverte: texto claro em fundo escuro → texto escuro em fundo claro
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    cv2.imwrite("debug_ocr_region.jpg", thresh)

    texto = pytesseract.image_to_string(thresh, config=TESS_CONFIG).strip()
    texto = _corrigir_ocr(texto)
    print(f"OCR leu: '{texto}'")

    match = re.search(r'(OP|ST|EB)\d{2}-\d{3}', texto)
    return match.group() if match else None


def _corrigir_ocr(texto):
    """Corrige erros comuns do OCR no padrão de ID das cartas."""
    texto = texto.replace('\n', '').replace(' ', '')
    texto = re.sub(r'^0P', 'OP', texto)
    texto = re.sub(r'^5T', 'ST', texto)
    texto = re.sub(r'^6B', 'EB', texto)
    texto = re.sub(r'[O0](?=\d)', '0', texto)  # O/0 antes de número → 0
    texto = re.sub(r'(?<=\w)[O](?=\w)', '0', texto)  # O no meio de dígitos → 0
    return texto
 
 
# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------
 
def process_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return None, "Erro: não foi possível carregar a imagem"
 
    carta, extraction_method = extrair_carta(img)
 
    card_id = extrair_id_por_ocr(carta)
    if not card_id:
        print("OCR falhou — tentando LLM...")
        card_id = _extrair_id_via_llm(carta)
    print(f"ID detectado: {card_id}")
 
    if card_id:
        return card_id, f"ocr, method={extraction_method}"
 
    return None, f"ocr_failed, method={extraction_method}"
 