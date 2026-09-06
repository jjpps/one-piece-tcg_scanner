# Plano de Implementação — Migração Ollama → Gemini

> Baseado em `gemini_spec.md`. Este arquivo traduz a spec em passos de implementação, com código.

## Contexto

Dois pontos de chamada real a modelo LLM, ambos hoje só em Ollama:

| Função | Arquivo | Caso de uso | Modelo Ollama atual |
|---|---|---|---|
| `_extrair_id_via_llm` | `backend/image_tools/llm_processor.py` | imagem → texto (fallback do OCR) | `glm-ocr` |
| `_normalize_deck_payload_with_llm` | `backend/services/upload_service.py` | texto → texto (parse de deck-list) | `llama3.2` |

Objetivo: os dois passam a checar `LLM_PROVIDER` (`ollama` default, ou `gemini`) e, se `gemini`, chamam a API do Gemini (`gemini-3.5-flash-lite` por padrão, configurável) em vez do Ollama local. Contrato de retorno de cada função não muda.

## Decisões já tomadas

- Switch único (`LLM_PROVIDER`), não um toggle por função.
- SDK: `google-genai` (SDK unificado atual do Google).
- Módulo novo `backend/config.py` (env) e `backend/llm_client.py` (dispatch Ollama/Gemini) — ambos top-level em `backend/`, mesmo padrão de `card_id_pattern.py`, importáveis de qualquer pacote sem path relativo.
- `extrair_lista_cards` (morto) não é migrado, é removido.
- `load_hashes_from_db` / `cards_hash_repository.py` (morto, feature de comparação de imagem) é removido nesta mesma limpeza.
- Nenhuma decisão em aberto — pronto para implementação.

---

## Passo 0 — Dependências e env

### `backend/requirements.txt`

Adicionar duas linhas (remover `ollama` **não** — continua necessário para o modo local):

```diff
 flask
 flask-cors
 requests
 opencv-python
 pytesseract
 imagehash
 ollama
+google-genai
+python-dotenv
```

> `imagehash` fica sem nenhum usuário no código depois da limpeza do Passo 3 (só era usado por `load_hashes_from_db`). Não removida a dependência nesta spec — pertence à feature de comparação de imagem (`imagem_comparation.spec.md`), que ainda vai precisar dela. Decisão de removê-la fica pra aquela spec, não aqui.

### `.gitignore`

Hoje não existe nenhuma entrada para `.env`. Adicionar (junto das outras extensões ignoradas, topo do arquivo):

```diff
 *.jpg
 *.png
 *.jpeg
 db.sqlite
 *.xlsx
+.env
```

### `backend/.env.example` (novo arquivo)

```
LLM_PROVIDER=ollama
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.5-flash-lite
```

### `backend/.env` (novo arquivo, não commitado — cada dev cria o seu)

Mesmo conteúdo do `.env.example`, com `GEMINI_API_KEY` preenchida quando `LLM_PROVIDER=gemini`.

---

## Passo 1 — `backend/config.py` (novo)

Único ponto que lê env. Carregado automaticamente na primeira vez que qualquer módulo importar `config` (não precisa chamar nada em `app.py`).

```python
import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')
```

---

## Passo 2 — `backend/llm_client.py` (novo)

Dispatch único: os dois call sites passam a chamar `chat_vision` ou `chat_text` em vez de `ollama.chat` direto. Mantém a mesma forma de uso que já existia (Ollama recebe o modelo por parâmetro, igual antes), só decide o provider.

```python
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
```

- `_gemini_client` é lazy (só instancia no primeiro uso) — assim quem estiver com `LLM_PROVIDER=ollama` nunca precisa ter `GEMINI_API_KEY` setada.
- Modelo Ollama continua vindo de cada call site (`glm-ocr`, `llama3.2`) — só o modelo Gemini é centralizado via env, porque é o mesmo modelo multimodal pros dois casos de uso.

---

## Passo 3 — Trocar os call sites

### 3.1 `backend/image_tools/llm_processor.py`

Estado atual (arquivo completo hoje, 61 linhas) — ver spec para o texto. Vira:

```python
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
```

Removidos: `import ollama`, `import base64` (não usado mais aqui — o encode fica dentro de `llm_client.py`), e a função `extrair_lista_cards` inteira (código morto, ver Passo 4).

### 3.2 `backend/services/upload_service.py`

Trocar o import (linha 5):
```diff
-import ollama
+from llm_client import chat_text
```

Trocar o corpo do `try` em `_normalize_deck_payload_with_llm` (linhas 107-115):
```diff
     try:
-        response = ollama.chat(
-            model='llama3.2',
-            messages=[{'role': 'user', 'content': prompt}],
-            options={'temperature': 0}
-        )
-        content = response.get('message', {}).get('content', '')
-        content = str(content).strip()
+        content = chat_text(prompt, ollama_model='llama3.2', temperature=0)
         print(f"LLM response: {content}", flush=True)
```

Resto da função (`_extract_json_from_text`, fallback pra `_parse_plain_cards`, etc.) não muda — o contrato de `content` (string com o texto da resposta) é o mesmo.

---

## Passo 4 — Limpeza de código morto

- **`backend/image_tools/llm_processor.py`**: remover a função `extrair_lista_cards` (linhas 37-61 do arquivo atual) — 0 chamadores em todo o repo, retorna `"NOTHING YET"`. Já removida como parte da reescrita do Passo 3.1 acima (o arquivo novo já não a inclui).
- **`backend/repositories/cards_hash_repository.py`**: deletar o arquivo inteiro. Única função (`load_hashes_from_db`) sem chamadores em todo o repo; é infra órfã da feature de comparação de imagem (`imagem_comparation.spec.md`), não usada por nada hoje. Confirmar antes de deletar: `grep -rn "load_hashes_from_db\|cards_hash_repository" backend --include="*.py"` deve retornar só a própria definição.

---

## Passo 5 — Validação manual / QA

- `LLM_PROVIDER=ollama` (ou variável ausente, usa o default): comportamento idêntico ao de hoje — testar 1 carta via fallback OCR e 1 deck-list colado, confirmar que nada quebrou.
- `LLM_PROVIDER=gemini` com `GEMINI_API_KEY` válida: mesmos dois fluxos, agora batendo na API do Gemini — confirmar que `_extrair_id_via_llm` ainda retorna um ID válido ou `None`, e que `_normalize_deck_payload_with_llm` ainda retorna o mesmo formato de dict (`{'deckName': ..., 'cards': [...]}`).
- Sem `GEMINI_API_KEY` e `LLM_PROVIDER=gemini`: erro deve aparecer só na primeira chamada real ao Gemini (client é lazy), não na inicialização do app.
- Rodar a suíte/servidor depois de deletar `cards_hash_repository.py` e confirmar que o app sobe normal (nada importa esse módulo).

> Testes automatizados de backend ficam a cargo do processo já existente da equipe — não é criada suíte própria aqui.

## Arquivos impactados (resumo)

- `backend/config.py` (novo)
- `backend/llm_client.py` (novo)
- `backend/.env.example` (novo)
- `backend/.env` (novo, não commitado)
- `backend/image_tools/llm_processor.py` (modificado + remoção de `extrair_lista_cards`)
- `backend/services/upload_service.py` (modificado)
- `backend/repositories/cards_hash_repository.py` (deletado)
- `backend/requirements.txt` (adiciona `google-genai`, `python-dotenv`)
- `.gitignore` (adiciona `.env`)
