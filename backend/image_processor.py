import cv2
from PIL import Image
import sys
import imagehash
import numpy as np
import repositories.cards_hash_repository as cards_hash_repository

hashes_db = cards_hash_repository.load_hashes_from_db()


def process_image_improved(image_path):
    
    img = cv2.imread(image_path)
    if img is None:
        return None, "Erro: Não foi possível carregar a imagem"
    
    h, w, _ = img.shape
    #print(f"Dimensões da imagem: {w}x{h}")
 
 
    carta_isolada, extraction_method = smart_card_extraction(img)    
 
    # Salvar carta para ver
    cv2.imwrite("debug_detected_card.jpg", carta_isolada)
 
    # Pré-processamento opcional
    carta_processada = cv2.GaussianBlur(carta_isolada, (3, 3), 0)
    #carta_processada = carta_isolada
 
    # Gerar hash
    pil_img = Image.fromarray(cv2.cvtColor(carta_processada, cv2.COLOR_BGR2RGB))
    scan_hash = imagehash.phash(pil_img, hash_size=8)
    
    #print(f"Hash gerado: {scan_hash}")
 
    # Comparar com banco
    best_card = None
    best_distance = 999
 
    for card_id, db_hash_str in hashes_db:
        try:
            if isinstance(db_hash_str, str):
                db_hash = imagehash.hex_to_hash(db_hash_str)
            else:
                db_hash = db_hash_str
                
            distance = scan_hash - db_hash
            
            if distance < best_distance:
                best_distance = distance
                best_card = card_id
                
        except Exception as e:
            continue
 
    print(f"Melhor match: {best_card}, distância: {best_distance}")
 
    # Validar match
    if best_card is not None and best_distance <= 14:
        return best_card, f"distance={best_distance}, method={extraction_method}"
 
    return None, f"best_distance={best_distance}, method={extraction_method}"
def detect_card_by_color(img):
    """Detecta carta por cor das bordas (assumindo bordas escuras)"""
    
    # Converter para HSV para melhor detecção de cor
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Definir range para bordas escuras (ajustar conforme necessário)
    lower_dark = np.array([0, 0, 0])
    upper_dark = np.array([180, 255, 80])
    
    # Criar máscara
    mask = cv2.inRange(hsv, lower_dark, upper_dark)
    
    # Operações morfológicas para limpar a máscara
    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    # Encontrar contornos na máscara
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        # Pegar o maior contorno
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Verificar se tem proporção de carta (aproximadamente 2.5:3.5)
        aspect_ratio = w / h
        if 0.6 < aspect_ratio < 0.8:  # Cartas TCG típicas
            return img[y:y+h, x:x+w]
    
    return None


def detect_card_contour(img):
    """Detecta automaticamente o contorno da carta"""
    
    # Converter para escala de cinza
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Aplicar blur para reduzir ruído
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Detecção de bordas
    edges = cv2.Canny(blur, 50, 150)
    
    # Encontrar contornos
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filtrar contornos por área e forma retangular
    card_contours = []
    img_area = img.shape[0] * img.shape[1]
    
    for contour in contours:
        area = cv2.contourArea(contour)
        
        # Filtrar por área (carta deve ocupar uma porção significativa)
        if area > img_area * 0.1 and area < img_area * 0.9:
            
            # Aproximar contorno para polígono
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Verificar se é aproximadamente retangular (4 pontos)
            if len(approx) == 4:
                card_contours.append((contour, area))
    
    # Retornar o maior contorno válido
    if card_contours:
        return max(card_contours, key=lambda x: x[1])[0]
    
    return None

def extract_card_by_contour(img, contour):
    """Extrai a carta usando o contorno detectado"""
    
    # Obter retângulo delimitador
    x, y, w, h = cv2.boundingRect(contour)
    
    # Adicionar margem pequena
    margin = 5
    x = max(0, x - margin)
    y = max(0, y - margin)
    w = min(img.shape[1] - x, w + 2 * margin)
    h = min(img.shape[0] - y, h + 2 * margin)
    
    return img[y:y+h, x:x+w]


def smart_card_extraction(img, fallback_percentages=None):
    """
    Sistema inteligente de extração com múltiplas tentativas
    """
    
    if fallback_percentages is None:
        fallback_percentages = {
            'y1_pct': 0.38, 'y2_pct': 0.86,
            'x1_pct': 0.01, 'x2_pct': 0.88
        }
    
    h, w, _ = img.shape
    extraction_methods = []
    
    # Método 1: Detecção por contorno
    try:
        contour = detect_card_contour(img)
        if contour is not None:
            card_by_contour = extract_card_by_contour(img, contour)
            if card_by_contour is not None and card_by_contour.shape[0] > 50 and card_by_contour.shape[1] > 50:
                extraction_methods.append(("contour", card_by_contour))
    except Exception as e:
        print(f"Erro na detecção por contorno: {e}")
    
    #Método 2: Detecção por cor
    # try:
    #     card_by_color = detect_card_by_color(img)
    #     if card_by_color is not None:
    #         extraction_methods.append(("color", card_by_color))
    # except Exception as e:
    #     print(f"Erro na detecção por cor: {e}")
    
    # Método 3: Recorte por porcentagem (fallback)
    y1, y2 = int(fallback_percentages['y1_pct'] * h), int(fallback_percentages['y2_pct'] * h)
    x1, x2 = int(fallback_percentages['x1_pct'] * w), int(fallback_percentages['x2_pct'] * w)
    card_by_percentage = img[y1:y2, x1:x2]
    extraction_methods.append(("percentage", card_by_percentage))
    
    # Salvar todas as tentativas para debug
    for i, (method, card_img) in enumerate(extraction_methods):
        cv2.imwrite(f"debug_card_{method}.jpg", card_img)
    
    # Retornar a primeira extração válida (prioridade: contorno > cor > porcentagem)
    for method, card_img in extraction_methods:
        if card_img is not None and card_img.shape[0] > 20 and card_img.shape[1] > 20:
            #print(f"Usando método: {method}")
            return card_img, method
    
    return card_by_percentage, "percentage"  # Fallback final
