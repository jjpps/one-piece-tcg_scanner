# Plano de Implementação — Detecção (Gemini) e Performance (Ollama)

> Baseado em `deteccao_performance_spec.md`. Este arquivo traduz a spec em passos de implementação, com código.

## Contexto

Dois eixos independentes, nenhum exige o outro:
- **Detecção (Gemini)**: `_extrair_id_via_llm` (`backend/image_tools/llm_processor.py`) para de depender do crop CV frágil quando `LLM_PROVIDER=gemini`, ganha saída estruturada com confiança, e retry em caso de baixa confiança.
- **Performance (Ollama/local)**: mudanças mecânicas em `ocr_processor.py`, `llm_client.py` e `processor.py` — nenhuma muda o resultado de detecção, só custo/latência.

## Decisões já tomadas

- Mandar a foto inteira pro Gemini é feito **só no caminho `gemini`** — o caminho `ollama` continua exatamente como está hoje (crop dos últimos 15% da carta), sem tocar no fluxo local.
- Saída estruturada usa `response_schema` como **dict simples** (JSON Schema), não Pydantic — evita depender de um modelo extra; `google-genai` já aceita dict direto (validado).
- Perspective warp (P5) e o downscale antes do Canny (P2) são a mesma mudança: `_contorno_carta` passa a devolver os 4 pontos já aproximados (`approx`) em vez do contorno bruto, e `_recortar_contorno` passa a usar esses 4 pontos pra corrigir perspectiva em vez de bounding-rect. Sem isso, perspective warp não teria pontos suficientes pra trabalhar.
- Paralelização do lote usa `ThreadPoolExecutor`, não `multiprocessing` — o custo real (Tesseract, chamada de rede pro Ollama/Gemini) já roda fora do GIL (subprocess do tesseract, socket da chamada LLM), então threads bastam; evita a complexidade de serializar estado entre processos.
- Cross-check de nome/set da carta (item 6 da spec) fica **fora desta rodada** — depende de uma chamada extra de API por carta (custo/latência), e mexe em `processor.py` além do escopo de detecção pura. Fica registrado como possível Fase 2 no fim deste plano.

---

## Passo 0 — Novas envs

### `backend/config.py`

```diff
 LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama')
 GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
 GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')
+DEBUG_IMAGES = os.getenv('DEBUG_IMAGES', 'false').lower() == 'true'
+OLLAMA_KEEP_ALIVE = os.getenv('OLLAMA_KEEP_ALIVE', '30m')
+PROCESS_WORKERS = int(os.getenv('PROCESS_WORKERS', '4'))
```

### `backend/.env.example` / `backend/.env`

```diff
 LLM_PROVIDER=ollama
 GEMINI_API_KEY=
 GEMINI_MODEL=gemini-3.5-flash-lite
+DEBUG_IMAGES=false
+OLLAMA_KEEP_ALIVE=30m
+PROCESS_WORKERS=4
```

---

## Foco Detecção (Gemini)

### Passo D1 + D2 — Foto inteira + saída estruturada com confiança

#### `backend/llm_client.py` — nova função `extract_card_id_gemini`

```diff
 import base64
+import json

 import ollama
 from google import genai
 from google.genai import types

-from config import LLM_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL
+from config import LLM_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL, OLLAMA_KEEP_ALIVE

 _gemini_client = None

 # Não usamos tools/function calling — desliga o AFC pra não logar o aviso do SDK
 # recomendando Chat.send_message pra esse caso.
 _GEMINI_CONFIG = types.GenerateContentConfig(
     automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
 )
+
+# Schema da resposta de identificação de carta — força o modelo a declarar
+# confiança em vez de chutar um código (mitiga a alucinação conhecida).
+_ID_RESPONSE_SCHEMA = {
+    'type': 'OBJECT',
+    'properties': {
+        'card_id': {'type': 'STRING', 'nullable': True},
+        'confidence': {'type': 'STRING', 'enum': ['high', 'low', 'none']},
+        'card_name': {'type': 'STRING', 'nullable': True},
+    },
+    'required': ['card_id', 'confidence'],
+}
+_ID_RESPONSE_CONFIG = types.GenerateContentConfig(
+    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
+    response_mime_type='application/json',
+    response_schema=_ID_RESPONSE_SCHEMA,
+)


 def _get_gemini_client():
     global _gemini_client
     if _gemini_client is None:
         _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
     return _gemini_client


+def extract_card_id_gemini(image_bytes: bytes, prompt: str) -> dict:
+    """Pede ao Gemini o ID da carta com saída estruturada: card_id, confidence, card_name."""
+    response = _get_gemini_client().models.generate_content(
+        model=GEMINI_MODEL,
+        contents=[prompt, types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg')],
+        config=_ID_RESPONSE_CONFIG,
+    )
+    return json.loads(response.text)
+
+
 def chat_vision(image_bytes: bytes, prompt: str, ollama_model: str) -> str:
     ...
```

Passar `keep_alive=OLLAMA_KEEP_ALIVE` nos dois branches Ollama existentes (ver Passo P3 abaixo — mesma mudança, feita junto aqui já que edita o mesmo arquivo).

#### `backend/image_tools/llm_processor.py` — reescrito

```python
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


def _tentar_gemini(imagem_cv):
    _, buffer = cv2.imencode('.jpg', imagem_cv)
    resultado = extract_card_id_gemini(buffer.tobytes(), _PROMPT_GEMINI)
    if resultado.get('confidence') == 'none':
        return None
    card_id = resultado.get('card_id')
    return card_id if card_id and ID_PATTERN.fullmatch(card_id) else None


def _extrair_id_via_llm(carta_cv, original_img=None):
    """Fallback: usa LLM (Ollama local ou Gemini cloud, conforme LLM_PROVIDER) para ler o ID quando OCR falha."""

    if LLM_PROVIDER == 'gemini':
        # Gemini localiza a carta sozinho — manda a foto inteira em vez do crop CV,
        # que é frágil com fundo poluído/rotação (ver evidência na spec).
        foto = original_img if original_img is not None else carta_cv
        card_id = _tentar_gemini(foto)
        if card_id:
            return card_id

        # Confiança baixa/nenhuma na foto inteira — tenta de novo só com o recorte
        # inferior (mesma heurística de crop usada no caminho Ollama abaixo).
        h, w = carta_cv.shape[:2]
        recorte = carta_cv[int(0.85*h):, :]
        return _tentar_gemini(recorte)

    # Ollama: mantém o crop já testado (região inferior, menos tokens)
    h, w = carta_cv.shape[:2]
    regiao = carta_cv[int(0.85*h):, :]
    _, buffer = cv2.imencode('.jpg', regiao)
    content = chat_vision(buffer.tobytes(), _PROMPT_OLLAMA, ollama_model='glm-ocr')
    match = ID_PATTERN.search(content)
    return match.group() if match else None
```

#### `backend/image_tools/ocr_processor.py` — call site

```diff
         card_id = extrair_id_por_ocr(carta)
         if not card_id:
-            card_id = _extrair_id_via_llm(carta)
+            card_id = _extrair_id_via_llm(carta, original_img=img)
```

`original_img=None` como default mantém compatibilidade se `_extrair_id_via_llm` for chamada de algum outro lugar sem a foto original (não existe hoje, mas evita quebrar silenciosamente).

---

## Foco Performance (Ollama / local)

### Passo P1 — Debug images atrás de env

#### `backend/image_tools/ocr_processor.py`

```diff
+from config import DEBUG_IMAGES
+
 def extrair_carta(img):
     """Extrai a carta da foto. Tenta contorno; cai para recorte fixo."""
     try:
         contour = _contorno_carta(img)
         if contour is not None:
             card = _recortar_contorno(img, contour)
             if card.shape[0] > 50 and card.shape[1] > 50:
-                cv2.imwrite("debug_detected_card.jpg", card)
+                if DEBUG_IMAGES:
+                    cv2.imwrite("debug_detected_card.jpg", card)
                 return card, "contour"
     except Exception as e:
         print(f"Contorno falhou: {e}")

     h, w = img.shape[:2]
     card = img[int(0.38*h):int(0.86*h), int(0.01*w):int(0.88*w)]
-    cv2.imwrite("debug_detected_card.jpg", card)
+    if DEBUG_IMAGES:
+        cv2.imwrite("debug_detected_card.jpg", card)
     return card, "percentage"
```

```diff
     cv2.imwrite("debug_ocr_region.jpg", thresh)
+    # (linha acima removida — ver diff completo: vira `if DEBUG_IMAGES: cv2.imwrite(...)`)
```

Concretamente, dentro de `extrair_id_por_ocr`:
```diff
-    cv2.imwrite("debug_ocr_region.jpg", thresh)
+    if DEBUG_IMAGES:
+        cv2.imwrite("debug_ocr_region.jpg", thresh)
```

### Passo P2 + P5 — Downscale no contorno + perspective warp no crop

Essas duas se implementam juntas: `_contorno_carta` passa a devolver os 4 pontos (`approx`) já escalados de volta pra resolução original, e `_recortar_contorno` usa esses 4 pontos com `warpPerspective` em vez de `boundingRect`.

#### `backend/image_tools/ocr_processor.py`

```diff
 import cv2
 import re
+import numpy as np
 import pytesseract
 from pathlib import Path
 from image_tools.llm_processor import _extrair_id_via_llm
 from card_id_pattern import CARD_ID_PATTERN
+from config import DEBUG_IMAGES
 import sys
```

```diff
+_CONTOUR_WORK_WIDTH = 1000
+
 def _contorno_carta(img):
-    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
+    h, w = img.shape[:2]
+    scale = _CONTOUR_WORK_WIDTH / w if w > _CONTOUR_WORK_WIDTH else 1.0
+    small = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale != 1.0 else img
+
+    gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
     edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
     contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

-    img_area = img.shape[0] * img.shape[1]
+    img_area = small.shape[0] * small.shape[1]
     candidatos = []
     for c in contours:
         area = cv2.contourArea(c)
         if not (img_area * 0.1 < area < img_area * 0.9):
             continue
         approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
         if len(approx) == 4:
-            candidatos.append((c, area))
+            candidatos.append((approx, area))

-    return max(candidatos, key=lambda x: x[1])[0] if candidatos else None
+    if not candidatos:
+        return None
+    melhor_approx = max(candidatos, key=lambda x: x[1])[0]
+    return (melhor_approx / scale).astype('int32') if scale != 1.0 else melhor_approx
```

```diff
-def _recortar_contorno(img, contour):
-    x, y, w, h = cv2.boundingRect(contour)
-    m = 5
-    x, y = max(0, x - m), max(0, y - m)
-    w = min(img.shape[1] - x, w + 2 * m)
-    h = min(img.shape[0] - y, h + 2 * m)
-    return img[y:y+h, x:x+w]
+def _ordenar_pontos(pts):
+    """Ordena os 4 cantos como TL, TR, BR, BL pra warpPerspective."""
+    pts = pts.reshape(4, 2).astype('float32')
+    soma = pts.sum(axis=1)
+    diff = np.diff(pts, axis=1).flatten()
+    return np.array([
+        pts[np.argmin(soma)],   # top-left: menor x+y
+        pts[np.argmin(diff)],   # top-right: menor y-x
+        pts[np.argmax(soma)],   # bottom-right: maior x+y
+        pts[np.argmax(diff)],   # bottom-left: maior y-x
+    ], dtype='float32')
+
+
+def _recortar_contorno(img, approx):
+    """Corrige perspectiva usando os 4 cantos do contorno, em vez de bounding-rect
+    alinhado aos eixos — evita sobrar fundo nas quinas e desalinhar o texto do ID
+    quando a carta está rotacionada na foto."""
+    origem = _ordenar_pontos(approx)
+    tl, tr, br, bl = origem
+
+    largura = int(max(np.linalg.norm(tr - tl), np.linalg.norm(br - bl)))
+    altura = int(max(np.linalg.norm(bl - tl), np.linalg.norm(br - tr)))
+
+    destino = np.array([[0, 0], [largura - 1, 0], [largura - 1, altura - 1], [0, altura - 1]], dtype='float32')
+    matriz = cv2.getPerspectiveTransform(origem, destino)
+    return cv2.warpPerspective(img, matriz, (largura, altura))
```

`numpy` não é uma dependência nova — já vem transitivamente com `opencv-python`. `extrair_carta` (a função que chama `_contorno_carta`/`_recortar_contorno`) não precisa de nenhuma mudança — a assinatura e o comportamento externo continuam os mesmos, só o que passa por dentro dos dois pontos.

### Passo P3 — `keep_alive` explícito no Ollama

#### `backend/llm_client.py`

```diff
     img_base64 = base64.b64encode(image_bytes).decode('utf-8')
     response = ollama.chat(
         model=ollama_model,
         messages=[{'role': 'user', 'content': prompt, 'images': [img_base64]}],
+        keep_alive=OLLAMA_KEEP_ALIVE,
     )
     return response['message']['content'].strip()
```

```diff
     options = {'temperature': temperature} if temperature is not None else {}
     response = ollama.chat(
         model=ollama_model,
         messages=[{'role': 'user', 'content': prompt}],
         options=options,
+        keep_alive=OLLAMA_KEEP_ALIVE,
     )
     return str(response.get('message', {}).get('content', '')).strip()
```

### Passo P4 — Paralelizar o loop de processamento em lote

#### `backend/processor.py`

Extrai o corpo do `for` pra uma função por-arquivo, roda em `ThreadPoolExecutor`:

```diff
 import threading
 import os
 import uuid
+from concurrent.futures import ThreadPoolExecutor, as_completed
 from pathlib import Path
 from dtos.local_card_dto import LocalCard
 from image_tools import ocr_processor
 from services.tcg_api_client import get_card_by_code
 from repositories.cards_repository import card_exists, get_card_data_by_code
+from config import PROCESS_WORKERS
 import json
 ERROR_IMAGES_FOLDER = 'images_with_errors'
```

```diff
+def _processar_um_arquivo(file_path):
+    """Roda o pipeline de detecção pra um arquivo e devolve o LocalCard (ou None em erro)."""
+    code, ocr_text, cropped_path = ocr_processor.process_image(file_path)
+
+    if code:
+        if card_exists(code):
+            card_data = get_card_data_by_code(code)
+            return LocalCard(file_path, card_data['image_url'], card_data['card_name'], code, True, cropped_path or "")
+        card = get_card_by_code(code)
+        if card:
+            return LocalCard(file_path, card.card_image, card.card_name, code, False, cropped_path or "")
+        _descartar_recorte(cropped_path)
+        _mover_para_erro(file_path)
+        return None
+
+    _descartar_recorte(cropped_path)
+    _mover_para_erro(file_path)
+    with status_lock:
+        processing_status["anyErrors"] = True
+    return None
+
+
+def _mover_para_erro(file_path):
+    file_ext = os.path.splitext(file_path)[1]
+    unique_filename = f"{uuid.uuid4()}{file_ext}"
+    os.rename(file_path, os.path.join(ERROR_IMAGES_FOLDER, unique_filename))
+
+
 def start_processing(folder_path):

     def worker():
         allowed_extensions = ('.png', '.jpg', '.jpeg')
         files = [
             os.path.join(folder_path, f)
             for f in os.listdir(folder_path)
             if f.lower().endswith(allowed_extensions)
         ]

         if not files:
             with status_lock:
                 processing_status["total"] = 0
                 processing_status["current"] = 0
                 processing_status["processing"] = False            
             return

         with status_lock:
             processing_status["total"] = len(files)
             processing_status["current"] = 0
             processing_status["processing"] = True
         localCards = []
-        for index, file_path in enumerate(files, start=1):
-            code, ocr_text, cropped_path = ocr_processor.process_image(file_path)
-
-            if code:
-                if card_exists(code):
-                    card_data = get_card_data_by_code(code)
-                    localCards.append(LocalCard(file_path,card_data['image_url'],card_data['card_name'],code,True,cropped_path or ""))
-                else:
-                    card = get_card_by_code(code)
-                    if card:
-                        localCards.append(LocalCard(file_path,card.card_image,card.card_name,code,False,cropped_path or ""))
-                    else:
-                        _descartar_recorte(cropped_path)
-                        file_ext = os.path.splitext(file_path)[1]
-                        unique_filename = f"{uuid.uuid4()}{file_ext}"
-                        os.rename(file_path, os.path.join(ERROR_IMAGES_FOLDER, unique_filename))
-            else:
-                _descartar_recorte(cropped_path)
-                file_ext = os.path.splitext(file_path)[1]
-                unique_filename = f"{uuid.uuid4()}{file_ext}"
-                os.rename(file_path, os.path.join(ERROR_IMAGES_FOLDER, unique_filename))
-                with status_lock:
-                    processing_status["anyErrors"] = True
-
-
-            with status_lock:
-                processing_status["current"] = index
+        with ThreadPoolExecutor(max_workers=PROCESS_WORKERS) as executor:
+            futures = [executor.submit(_processar_um_arquivo, fp) for fp in files]
+            for index, future in enumerate(as_completed(futures), start=1):
+                resultado = future.result()
+                if resultado:
+                    localCards.append(resultado)
+                with status_lock:
+                    processing_status["current"] = index
         existing_data = []
         if os.path.exists('processed_cards.json'):
```

- `_processar_um_arquivo` roda em thread separada por arquivo — `card_exists`/`get_card_data_by_code` abrem conexão SQLite própria por chamada (já é assim hoje, `sqlite3.connect` dentro de cada função do repository), então não há conexão compartilhada entre threads.
- Cada arquivo é independente (não há leitura/escrita cruzada entre arquivos), então não precisa de lock além do que já protege `processing_status` e o append em `localCards` (GIL já torna `list.append` atômico, mas mantido dentro do mesmo `with status_lock` por consistência com o resto do arquivo).
- `PROCESS_WORKERS` (env, default 4) controla quantos arquivos rodam em paralelo — ajustável conforme CPU/rede disponível.

---

## Passo de validação manual / QA

- **Detecção (Gemini)**: rodar a mesma foto real usada na spec com `LLM_PROVIDER=gemini` e conferir que `_extrair_id_via_llm` recebe a foto inteira (não o crop percentual) e devolve `EB04-023` com `confidence: high`. Testar também uma foto proposital sem carta nenhuma — esperado `confidence: none` e `card_id: null`, sem inventar código.
- **Performance (Ollama)**: rodar um lote de várias fotos com `LLM_PROVIDER=ollama`, comparar tempo total antes/depois do Passo P4 (paralelização) e confirmar via `ollama ps` que o modelo não recarrega entre cartas (Passo P3).
- Confirmar que `DEBUG_IMAGES=false` (default) não grava mais `debug_detected_card.jpg`/`debug_ocr_region.jpg`, e que `DEBUG_IMAGES=true` volta a gravar como antes.
- Confirmar visualmente (comparando o crop salvo) que uma foto com carta rotacionada gera um recorte sem fundo nas quinas depois do Passo P2+P5.

> Testes automatizados de backend ficam a cargo do processo já existente da equipe — não é criada suíte própria aqui.

## Arquivos impactados (resumo)

- `backend/config.py` (novas envs: `DEBUG_IMAGES`, `OLLAMA_KEEP_ALIVE`, `PROCESS_WORKERS`)
- `backend/.env.example` / `backend/.env`
- `backend/llm_client.py` (`extract_card_id_gemini`, `keep_alive` nos dois chats Ollama)
- `backend/image_tools/llm_processor.py` (reescrito — caminho Gemini com foto inteira + retry, caminho Ollama inalterado)
- `backend/image_tools/ocr_processor.py` (`_contorno_carta` com downscale, `_recortar_contorno` com perspective warp, debug images atrás de env, call site de `_extrair_id_via_llm` passando `original_img`)
- `backend/processor.py` (`worker()` paralelizado com `ThreadPoolExecutor`)

## Fase 2 (fora desta rodada) — Cross-check de nome/set

Ideia registrada na spec (item 6): pedir também `card_name` no schema estruturado (já incluído no Passo D1/D2 acima, o campo já vem na resposta) e, em `processor.py`, comparar esse nome com o retornado por `get_card_by_code`/`get_card_data_by_code` antes de aceitar o `card_id` — se não baterem, tratar como card_id suspeito mesmo com `confidence: high`. Não implementado agora porque exige uma chamada de API extra por carta nova (custo/latência) e decisão de UX sobre o que fazer quando o cross-check falha (rejeitar? marcar pra revisão manual?) — fica pra quando essa spec for retomada.
