import cv2
import re
from card_id_pattern import CARD_ID_PATTERN
from config import LLM_PROVIDER
from llm_client import chat_vision, extract_card_id_gemini

ID_PATTERN = re.compile(CARD_ID_PATTERN)

_PROMPT_OLLAMA = (
    'This is the bottom of a One Piece trading card. Read the printed card ID code. '
    'Valid formats: two to four letters, then two digits, a dash, then three digits '
    '(sets like OP, ST, EB, PRB); or a promo code, the single letter P, a dash, then three digits. '
    'If you cannot clearly read the code, reply with exactly UNKNOWN — never guess. '
    'Reply with ONLY the ID code or UNKNOWN, nothing else. You cannot take more than 30 seconds to identify. '
    'Character whitelist: OPSTEBRP0123456789-'
)

_PROMPT_GEMINI = (
    'This is a photo of a One Piece trading card. It may be at an angle, partially covered by glare, '
    'or surrounded by background clutter (table, storage box, hands, etc). Find the card and read its '
    'printed ID code, usually in small print near a bottom corner. '
    'Valid formats: two to four letters, then two digits, a dash, then three digits '
    '(sets like OP, ST, EB, PRB); or a promo code, the single letter P, a dash, then three digits. '
    'Also read the card name if visible, near the bottom of the card. '
    'Set confidence to "high" only if every character of the code is clearly legible. Set it to "low" if '
    'you can read most of it but are unsure of one character. Set it to "none" and card_id to null if you '
    'cannot find the code or cannot read it at all — never guess a code you are not confident about.'
)


# q95 (default do imencode) na foto original do celular gera payload de MBs por
# chamada — upload e tokenização da imagem dominam a latência.
_JPEG_QUALIDADE = 80


def _tentar_gemini(imagem_cv):
    _, buffer = cv2.imencode('.jpg', imagem_cv, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALIDADE])
    resultado = extract_card_id_gemini(buffer.tobytes(), _PROMPT_GEMINI)
    if resultado.get('confidence') == 'none':
        return None
    card_id = resultado.get('card_id')
    return card_id if card_id and ID_PATTERN.fullmatch(card_id) else None


def _extrair_id_via_llm(carta_cv, original_img=None):
    """Fallback: usa LLM (Ollama local ou Gemini cloud, conforme LLM_PROVIDER) para ler o ID quando OCR falha."""

    if LLM_PROVIDER == 'gemini':
        # Recorte inferior primeiro: é o caso comum e custa uma fração dos pixels da
        # foto inteira. Se o crop CV saiu errado, o schema faz o modelo responder
        # confidence='none' em vez de chutar, e caímos no fallback abaixo.
        h, w = carta_cv.shape[:2]
        card_id = _tentar_gemini(carta_cv[int(0.85*h):, :])
        if card_id:
            return card_id

        # Fallback: foto original inteira, pra quando o crop CV errou a carta
        # (fundo poluído, rotação). Caro, então só no que o recorte não resolveu.
        if original_img is not None:
            return _tentar_gemini(original_img)
        return None

    # Ollama: mantém o crop já testado (região inferior, menos tokens)
    h, w = carta_cv.shape[:2]
    regiao = carta_cv[int(0.85*h):, :]
    _, buffer = cv2.imencode('.jpg', regiao)
    content = chat_vision(buffer.tobytes(), _PROMPT_OLLAMA, ollama_model='glm-ocr')
    match = ID_PATTERN.search(content)
    return match.group() if match else None
