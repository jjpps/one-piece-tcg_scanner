import base64
import json

import ollama
from google import genai
from google.genai import types

from config import LLM_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL, OLLAMA_KEEP_ALIVE

_gemini_client = None

# Não usamos tools/function calling — desliga o AFC pra não logar o aviso do SDK
# recomendando Chat.send_message pra esse caso.
_GEMINI_CONFIG = types.GenerateContentConfig(
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
)

# Schema da resposta de identificação de carta — força o modelo a declarar
# confiança em vez de chutar um código (mitiga a alucinação conhecida).
_ID_RESPONSE_SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'card_id': {'type': 'STRING', 'nullable': True},
        'confidence': {'type': 'STRING', 'enum': ['high', 'low', 'none']},
        'card_name': {'type': 'STRING', 'nullable': True},
    },
    'required': ['card_id', 'confidence'],
}
_ID_RESPONSE_CONFIG = types.GenerateContentConfig(
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    response_mime_type='application/json',
    response_schema=_ID_RESPONSE_SCHEMA,
)


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


def extract_card_id_gemini(image_bytes: bytes, prompt: str) -> dict:
    """Pede ao Gemini o ID da carta com saída estruturada: card_id, confidence, card_name."""
    response = _get_gemini_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')],
        config=_ID_RESPONSE_CONFIG,
    )
    return json.loads(response.text)


def chat_vision(image_bytes: bytes, prompt: str, ollama_model: str) -> str:
    """Manda uma imagem + prompt pro provider ativo, retorna o texto da resposta."""
    if LLM_PROVIDER == 'gemini':
        response = _get_gemini_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')],
            config=_GEMINI_CONFIG,
        )
        return (response.text or '').strip()

    img_base64 = base64.b64encode(image_bytes).decode('utf-8')
    response = ollama.chat(
        model=ollama_model,
        messages=[{'role': 'user', 'content': prompt, 'images': [img_base64]}],
        keep_alive=OLLAMA_KEEP_ALIVE,
    )
    return response['message']['content'].strip()


def chat_text(prompt: str, ollama_model: str, temperature: float | None = None) -> str:
    """Manda um prompt de texto pro provider ativo, retorna o texto da resposta."""
    if LLM_PROVIDER == 'gemini':
        response = _get_gemini_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=_GEMINI_CONFIG,
        )
        return (response.text or '').strip()

    options = {'temperature': temperature} if temperature is not None else {}
    response = ollama.chat(
        model=ollama_model,
        messages=[{'role': 'user', 'content': prompt}],
        options=options,
        keep_alive=OLLAMA_KEEP_ALIVE,
    )
    return str(response.get('message', {}).get('content', '')).strip()
