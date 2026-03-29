import ollama
import base64
import cv2
import re

ID_PATTERN = re.compile(r'[A-Z]{2,4}\d{2}-\d{3}')
def _extrair_id_via_llm(carta_cv):
    """Fallback: usa LLM local via Ollama para ler o ID quando OCR falha."""
    
    # Envia só a região inferior — menos tokens, mais foco
    h, w = carta_cv.shape[:2]
    regiao = carta_cv[int(0.85*h):, :]
    
    _, buffer = cv2.imencode('.jpg', regiao)
    img_base64 = base64.b64encode(buffer).decode('utf-8')

    response = ollama.chat(
        model='glm-ocr',
        messages=[{
            'role': 'user',
            'content': 'This is the bottom of a One Piece trading card. Read the card ID code (format: XX##-###, example: EB03-021). Reply with ONLY the ID code, nothing else.',
            'images': [img_base64]
        }]
    )
    match = ID_PATTERN.search(response['message']['content'].strip())
    return match.group() if match else None