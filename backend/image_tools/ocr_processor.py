import cv2
import re
import numpy as np
import pytesseract
from pathlib import Path
from image_tools.llm_processor import _extrair_id_via_llm
from card_id_pattern import CARD_ID_PATTERN
from config import DEBUG_IMAGES
import sys

ID_REGION = {'y1': 0.85, 'y2': 0.97, 'x1': 0.55, 'x2': 0.92}

# Padrão do ID das cartas One Piece (ex: EB03-021, OP01-001, ST01-001, PRB02-001, P-041)
ID_PATTERN = re.compile(CARD_ID_PATTERN)

CROPPED_SUBFOLDER = "cropped"

# Configuração do Tesseract — linha única, só chars do ID
TESS_CONFIG = '--psm 6 -c tessedit_char_whitelist=OPSTEBR0123456789-'

# Configura caminho do executável Tesseract para Windows
if sys.platform.startswith('win'):
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

_CONTOUR_WORK_WIDTH = 1000


def _contorno_carta(img):
    h, w = img.shape[:2]
    scale = _CONTOUR_WORK_WIDTH / w if w > _CONTOUR_WORK_WIDTH else 1.0
    small = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale != 1.0 else img

    gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    img_area = small.shape[0] * small.shape[1]
    candidatos = []
    for c in contours:
        area = cv2.contourArea(c)
        if not (img_area * 0.1 < area < img_area * 0.9):
            continue
        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(approx) == 4:
            candidatos.append((approx, area))

    if not candidatos:
        return None
    melhor_approx = max(candidatos, key=lambda x: x[1])[0]
    return (melhor_approx / scale).astype('int32') if scale != 1.0 else melhor_approx


def _ordenar_pontos(pts):
    """Ordena os 4 cantos como TL, TR, BR, BL pra warpPerspective."""
    pts = pts.reshape(4, 2).astype('float32')
    soma = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).flatten()
    return np.array([
        pts[np.argmin(soma)],   # top-left: menor x+y
        pts[np.argmin(diff)],   # top-right: menor y-x
        pts[np.argmax(soma)],   # bottom-right: maior x+y
        pts[np.argmax(diff)],   # bottom-left: maior y-x
    ], dtype='float32')


def _recortar_contorno(img, approx):
    """Corrige perspectiva usando os 4 cantos do contorno, em vez de bounding-rect
    alinhado aos eixos — evita sobrar fundo nas quinas e desalinhar o texto do ID
    quando a carta está rotacionada na foto."""
    origem = _ordenar_pontos(approx)
    tl, tr, br, bl = origem

    largura = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
    altura = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))

    destino = np.array([[0, 0], [largura - 1, 0], [largura - 1, altura - 1], [0, altura - 1]], dtype='float32')
    matriz = cv2.getPerspectiveTransform(origem, destino)
    return cv2.warpPerspective(img, matriz, (largura, altura))


def extrair_carta(img):
    """Extrai a carta da foto. Tenta contorno; cai para recorte fixo."""
    try:
        contour = _contorno_carta(img)
        if contour is not None:
            card = _recortar_contorno(img, contour)
            if card.shape[0] > 50 and card.shape[1] > 50:
                if DEBUG_IMAGES:
                    cv2.imwrite("debug_detected_card.jpg", card)
                return card, "contour"
    except Exception as e:
        print(f"Contorno falhou: {e}")

    h, w = img.shape[:2]
    card = img[int(0.38*h):int(0.86*h), int(0.01*w):int(0.88*w)]
    if DEBUG_IMAGES:
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

    if DEBUG_IMAGES:
        cv2.imwrite("debug_ocr_region.jpg", thresh)

    texto = pytesseract.image_to_string(thresh, config=TESS_CONFIG).strip()
    texto = _corrigir_ocr(texto)    

    match = ID_PATTERN.search(texto)
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

def _salvar_recorte(image_path, carta_cv):
    """Salva a carta recortada ao lado da foto original, numa subpasta 'cropped'."""
    original = Path(image_path)
    cropped_dir = original.parent / CROPPED_SUBFOLDER
    cropped_dir.mkdir(exist_ok=True)
    cropped_path = cropped_dir / original.name
    cv2.imwrite(str(cropped_path), carta_cv)
    return str(cropped_path)


def process_image(image_path):
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None, "Erro: não foi possível carregar a imagem", None

        carta, extraction_method = extrair_carta(img)
        cropped_path = _salvar_recorte(image_path, carta)

        card_id = extrair_id_por_ocr(carta)
        if not card_id:
            card_id = _extrair_id_via_llm(carta, original_img=img)

        if card_id:
            return card_id, f"ocr, method={extraction_method}", cropped_path

        return None, f"ocr_failed, method={extraction_method}", cropped_path
    except Exception as e:
        return None, f"Erro ao processar imagem: {image_path}, {str(e)}", None
 