import base64
import json
import random
import threading
import time

import ollama
from google import genai
from google.genai import types

from config import (
    LLM_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL, OLLAMA_KEEP_ALIVE,
    GEMINI_MAX_CONCURRENCY, GEMINI_TIMEOUT_SECONDS, GEMINI_THINKING_BUDGET,
)

_gemini_client = None
_gemini_semaphore = threading.Semaphore(GEMINI_MAX_CONCURRENCY)
# 503 "high demand" é capacidade do modelo no lado do Google, não cota nossa —
# é transitório e frequente, então vale mais uma tentativa que o padrão.
_GEMINI_MAX_RETRIES = 3
_GEMINI_RETRY_BACKOFF_SECONDS = 2
# Só vale repetir cota/sobrecarga/timeout. Modelo inexistente, chave inválida ou
# safety block são permanentes: repetir 3x só multiplica a espera do lote.
_HTTP_TRANSITORIO = (408, 429, 500, 502, 503, 504)

# Ler um ID não exige raciocínio; desligar o thinking corta latência por chamada.
_THINKING = (types.ThinkingConfig(thinking_budget=GEMINI_THINKING_BUDGET)
             if GEMINI_THINKING_BUDGET >= 0 else None)

# Não usamos tools/function calling — desliga o AFC pra não logar o aviso do SDK
# recomendando Chat.send_message pra esse caso.
_GEMINI_CONFIG = types.GenerateContentConfig(
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    thinking_config=_THINKING,
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
    thinking_config=_THINKING,
)


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_SECONDS * 1000),
        )
    return _gemini_client


def _e_transitorio(exc) -> bool:
    """Erro que pode dar certo se tentar de novo (cota, sobrecarga, rede)."""
    codigo = getattr(exc, 'code', None) or getattr(exc, 'status_code', None)
    if codigo in _HTTP_TRANSITORIO:
        return True
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    # httpx.ReadTimeout/ConnectError não herdam de TimeoutError/ConnectionError.
    return any(t in type(exc).__name__ for t in ('Timeout', 'Connect'))


def _call_gemini(fn):
    """Roda uma chamada ao Gemini com limite de concorrência (GEMINI_MAX_CONCURRENCY) e
    retry com backoff apenas em erro transitório.

    O semáforo é pego por tentativa, nunca em volta do sleep: com ele por fora, uma
    única carta com erro segurava a fila inteira durante o backoff."""
    for tentativa in range(_GEMINI_MAX_RETRIES + 1):
        try:
            with _gemini_semaphore:
                return fn()
        except Exception as exc:
            print(f"[llm_client] Erro ao chamar Gemini (tentativa {tentativa + 1}/{_GEMINI_MAX_RETRIES + 1}): {exc}", flush=True)
            if tentativa == _GEMINI_MAX_RETRIES or not _e_transitorio(exc):
                raise
            # Exponencial com jitter: sem o jitter, as N threads levam 503 juntas e
            # voltam juntas no mesmo instante, batendo de novo no modelo lotado.
            espera = _GEMINI_RETRY_BACKOFF_SECONDS * (2 ** tentativa)
            time.sleep(espera * random.uniform(0.5, 1.5))


def extract_card_id_gemini(image_bytes: bytes, prompt: str) -> dict:
    """Pede ao Gemini o ID da carta com saída estruturada: card_id, confidence, card_name."""
    response = _call_gemini(lambda: _get_gemini_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')],
        config=_ID_RESPONSE_CONFIG,
    ))
    return json.loads(response.text)


def chat_vision(image_bytes: bytes, prompt: str, ollama_model: str) -> str:
    """Manda uma imagem + prompt pro provider ativo, retorna o texto da resposta."""
    if LLM_PROVIDER == 'gemini':
        response = _call_gemini(lambda: _get_gemini_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')],
            config=_GEMINI_CONFIG,
        ))
        return (response.text or '').strip()

    try:
        img_base64 = base64.b64encode(image_bytes).decode('utf-8')
        response = ollama.chat(
            model=ollama_model,
            messages=[{'role': 'user', 'content': prompt, 'images': [img_base64]}],
            keep_alive=OLLAMA_KEEP_ALIVE,
        )
        return response['message']['content'].strip()
    except Exception as exc:
        print(f"[llm_client] Erro ao chamar Ollama (vision): {exc}", flush=True)
        raise


def chat_text(prompt: str, ollama_model: str, temperature: float | None = None) -> str:
    """Manda um prompt de texto pro provider ativo, retorna o texto da resposta."""
    if LLM_PROVIDER == 'gemini':
        response = _call_gemini(lambda: _get_gemini_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=_GEMINI_CONFIG,
        ))
        return (response.text or '').strip()

    options = {'temperature': temperature} if temperature is not None else {}
    response = ollama.chat(
        model=ollama_model,
        messages=[{'role': 'user', 'content': prompt}],
        options=options,
        keep_alive=OLLAMA_KEEP_ALIVE,
    )
    return str(response.get('message', {}).get('content', '')).strip()
