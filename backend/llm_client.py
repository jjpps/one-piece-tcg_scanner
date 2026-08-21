import base64

import ollama
from google import genai
from google.genai import types

from config import LLM_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL

_gemini_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


def chat_vision(image_bytes: bytes, prompt: str, ollama_model: str) -> str:
    """Manda uma imagem + prompt pro provider ativo, retorna o texto da resposta."""
    if LLM_PROVIDER == 'gemini':
        response = _get_gemini_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')],
        )
        return (response.text or '').strip()

    img_base64 = base64.b64encode(image_bytes).decode('utf-8')
    response = ollama.chat(
        model=ollama_model,
        messages=[{'role': 'user', 'content': prompt, 'images': [img_base64]}],
    )
    return response['message']['content'].strip()


def chat_text(prompt: str, ollama_model: str, temperature: float | None = None) -> str:
    """Manda um prompt de texto pro provider ativo, retorna o texto da resposta."""
    if LLM_PROVIDER == 'gemini':
        response = _get_gemini_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        return (response.text or '').strip()

    options = {'temperature': temperature} if temperature is not None else {}
    response = ollama.chat(
        model=ollama_model,
        messages=[{'role': 'user', 'content': prompt}],
        options=options,
    )
    return str(response.get('message', {}).get('content', '')).strip()
