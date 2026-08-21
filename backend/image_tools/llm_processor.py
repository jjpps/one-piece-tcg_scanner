import cv2
import re
from card_id_pattern import CARD_ID_PATTERN
from llm_client import chat_vision

ID_PATTERN = re.compile(CARD_ID_PATTERN)

_PROMPT = (
    'This is the bottom of a One Piece trading card. Read the printed card ID code. '
    'Valid formats: two to four letters, then two digits, a dash, then three digits '
    '(sets like OP, ST, EB, PRB); or a promo code, the single letter P, a dash, then three digits. '
    'If you cannot clearly read the code, reply with exactly UNKNOWN — never guess. '
    'Reply with ONLY the ID code or UNKNOWN, nothing else. You cannot take more than 30 seconds to identify. '
    'Character whitelist: OPSTEBRP0123456789-'
)


def _extrair_id_via_llm(carta_cv):
    """Fallback: usa LLM (Ollama local ou Gemini cloud, conforme LLM_PROVIDER) para ler o ID quando OCR falha."""

    # Envia só a região inferior — menos tokens, mais foco
    h, w = carta_cv.shape[:2]
    regiao = carta_cv[int(0.85*h):, :]

    _, buffer = cv2.imencode('.jpg', regiao)

    content = chat_vision(buffer.tobytes(), _PROMPT, ollama_model='glm-ocr')
    match = ID_PATTERN.search(content)
    return match.group() if match else None
