# Plano de Implementação — Suporte a Novos Tipos de Carta

> Baseado em `othersets_spec.md`. Este arquivo traduz a spec em passos de implementação. Atualizar conforme decisões forem tomadas.

## Contexto

3 novos formatos de código de carta precisam ser suportados:

| Formato | Exemplo | Endpoint | Regex atual reconhece? |
|---|---|---|---|
| STXX-XXX | ST03-017 | `/api/decks/card/{id}/` | Sim (parcialmente — ver Passo 1) |
| P-XXX | P-024 | `/api/promos/card/{id}/` | Não — nenhuma regex do sistema aceita |
| PRBXX-XXX | PRB02-012 | `/api/promos/card/{id}/` | Parcial — só em `llm_processor.py` |

## Decisões já tomadas

- PRB usa o mesmo endpoint de promos que P (confirmado, não é engano).
- P-XXX é sempre `P` + traço + 3 dígitos, sem variação — não tem os 2 dígitos de set que os outros formatos têm.
- **P-XXX é uma regra de regex isolada** (não combinada numa única expressão com o padrão genérico dos outros tipos) — `(OP|ST|EB|PRB)\d{2}-\d{3}` continua separada de `P-\d{3}`.
- **Dispatch de endpoint só dentro de `tcg_api_client.py`** — nenhum outro arquivo precisa saber sobre prefixo/tipo de carta.
- **Whitelist do Tesseract**: só adicionar a letra `R`, sem reescrever prompt/whitelist além disso.

Nenhuma decisão em aberto — pronto para implementação.

---

## O que o dev BACKEND precisa saber

Toda a feature é backend. 4 arquivos mudam, nenhum schema de banco muda.

### 1. `backend/image_tools/ocr_processor.py` — caminho principal de detecção (Tesseract)

Estado atual:
```python
# linha 13
TESS_CONFIG = '--psm 6 -c tessedit_char_whitelist=OPSTEB0123456789-'

# linha 105 (dentro de extrair_id_por_ocr)
match = re.search(r'(OP|ST|EB)\d{2}-\d{3}', texto)
return match.group() if match else None
```

Mudar para:
```python
# linha 13 — adicionar R para o Tesseract conseguir ler "PRB"
TESS_CONFIG = '--psm 6 -c tessedit_char_whitelist=OPSTEBR0123456789-'

# linha 105 — incluir PRB no grupo genérico + checagem isolada para P-XXX
match = re.search(r'(OP|ST|EB|PRB)\d{2}-\d{3}', texto) or re.search(r'P-\d{3}', texto)
return match.group() if match else None
```
- `PRB` **precisa vir antes de** qualquer tentativa de casar só `P` — como a regra do `P` isolado é uma alternativa separada (`or`), a ordem do `re.search` acima já resolve isso: se o texto for "PRB02-012", o primeiro `re.search` (que inclui `PRB`) já casa, então o segundo (`P-\d{3}`) nunca chega a ser avaliado nesse caso. Não inverter a ordem dos dois `re.search`.
- `_corrigir_ocr` (linhas 109-117) faz correções de erro de OCR assumindo prefixo de 2 letras (`^0P`→`OP`, `^5T`→`ST`, `^6B`→`EB`). Avaliar se o Tesseract vai confundir `PRB` com algo tipo `PR8`/`PRE` na prática — só dá pra saber testando com fotos reais. Se acontecer, adicionar mais uma linha de `re.sub` seguindo o mesmo padrão.
- `ID_PATTERN` na linha 10 (`[A-Z]{2,4}\d{2}-\d{3}`) é uma variável morta, não é usada em nenhum lugar deste arquivo — não precisa mexer, mas não confundir com a regex real da linha 105.

### 2. `backend/image_tools/llm_processor.py` — fallback via modelo de visão (Ollama)

Estado atual:
```python
# linha 6
ID_PATTERN = re.compile(r'[A-Z]{2,4}\d{2}-\d{3}')

# linha 21, dentro do prompt enviado ao modelo
'content': 'This is the bottom of a One Piece trading card. Read the card ID code (format: XX##-###, example: EB03-021). Reply with ONLY the ID code, nothing else. You cannot take more than 30 seconds to identify.This is character whitelist OPSTEB0123456789-',
```
Esse `ID_PATTERN` já casa com `PRB02-012` (prefixo de até 4 letras), mas **não casa com `P-024`** porque exige `\d{2}-\d{3}` sempre.

Mudar para:
```python
ID_PATTERN = re.compile(r'[A-Z]{2,4}\d{2}-\d{3}|P-\d{3}')
```
E atualizar o texto do prompt (linha 21) removendo a afirmação fixa de formato único e cobrindo os 3 casos, incluindo a letra R na whitelist mencionada:
```python
'content': 'This is the bottom of a One Piece trading card. Read the card ID code. Formats: XX##-### (example: EB03-021, ST03-017, PRB02-012) or P-### (example: P-024). Reply with ONLY the ID code, nothing else. You cannot take more than 30 seconds to identify. This is character whitelist OPSTEBR0123456789-',
```
- A função `extrair_lista_cards` (linhas 28-51) neste mesmo arquivo tem outro prompt com o mesmo formato fixo `XX##-###` na linha 44, mas **essa função retorna `"NOTHING YET"` e não é chamada por nenhum outro módulo** — confirmar com o time se ainda está em uso antes de gastar tempo atualizando; se for código morto, não mexer.

### 3. `backend/services/upload_service.py` — parse de decklist colado manualmente

> Correção importante: uma exploração anterior apontou esse código como estando em `review_service.py` — está errado, é em `upload_service.py`. `review_service.py` existe no projeto mas não tem lógica de regex de código de carta.

Dois pontos com a mesma regex fechada, usada para extrair o código de cada linha de texto colada pelo usuário (ex: "2 EB03-021"):
```python
# linha 24, dentro de _parse_plain_cards
code_match = re.search(r'([A-Z]{2,4}\d{2}-\d{3})', normalized, re.IGNORECASE)

# linha 29, mesma função — remove um "X" perdido antes do código
code = re.sub(r'^X(?=[A-Z]{2,4}\d{2}-\d{3}$)', '', code)

# linha 125, dentro de _normalize_deck_payload_with_llm — mesma limpeza pós-LLM
code = re.sub(r'^X(?=[A-Z]{2,4}\d{2}-\d{3}$)', '', code)
```
Todas as 3 ocorrências precisam da mesma extensão que os outros arquivos: aceitar o grupo genérico + `PRB` e, separadamente, `P-\d{3}`. Ex:
```python
code_match = re.search(r'([A-Z]{2,4}\d{2}-\d{3}|P-\d{3})', normalized, re.IGNORECASE)
code = re.sub(r'^X(?=[A-Z]{2,4}\d{2}-\d{3}$|P-\d{3}$)', '', code)
```
Também há um prompt de LLM em `_normalize_deck_payload_with_llm` (linhas 76-98) documentando o schema com exemplos `OP16-080`, `EB04-058` (linhas 84-90) e o formato `"code": "XX##-###"` (linha 80) — atualizar a descrição do formato e incluir um exemplo de cada tipo novo (`ST03-017`, `P-024`, `PRB02-012`), senão a LLM que normaliza a decklist colada vai continuar tendendo a rejeitar/deformar esses códigos mesmo depois do regex de fallback ser corrigido.

`check_deck_cards` (linha 169) também chama `get_card_by_code` (linha 180) — não precisa de nenhuma mudança aqui, só se beneficia automaticamente do dispatch feito no Passo 2 abaixo.

### 4. `backend/services/tcg_api_client.py` — dispatch de endpoint por tipo (o coração da feature)

Estado atual — uma única URL fixa para tudo:
```python
BASE_URL = "https://www.optcgapi.com/api/sets/card"

def get_card_by_code(card_code: str):
    try:
        url = f"{BASE_URL}/{card_code}"
        ...
```
Proposta — resolver a base a partir do prefixo, mantendo a assinatura pública de `get_card_by_code` intacta (os 4 call sites abaixo não precisam saber de nada disso):
```python
API_ROOT = "https://www.optcgapi.com/api"

def _resolve_base_url(card_code: str) -> str:
    code = card_code.upper()
    if code.startswith("PRB"):        # checar PRB ANTES de "P" isolado
        return f"{API_ROOT}/promos/card"
    if code.startswith("ST"):
        return f"{API_ROOT}/decks/card"
    if code.startswith("P-") or code.startswith("P"):
        return f"{API_ROOT}/promos/card"
    return f"{API_ROOT}/sets/card"    # comportamento atual, default (OP, EB, etc)

def get_card_by_code(card_code: str):
    try:
        url = f"{_resolve_base_url(card_code)}/{card_code}"
        ...
```
- **Ordem importa**: `PRB` tem que ser checado antes de `P`, senão "PRB02-012" cairia incorretamente na regra de promos por causa do "P" — nesse caso dá no mesmo resultado (promos), mas deixar explícito evita bug se um dia PRB ganhar endpoint próprio.
- Callers que passam por essa função sem precisar de nenhuma mudança: `backend/processor.py` (linhas 53, 56), `backend/routes/library_routes.py` (linha 77), `backend/services/upload_service.py` (linhas 45, 180).
- Esse arquivo também tem uma `API_KEY` não usada (linha 4) e um header comentado (linha 9) — não relacionado a esta feature, não mexer.

### Testes mínimos a acrescentar
Não existe suíte de testes no backend hoje. Criar um `backend/test_card_code_detection.py` simples, baseado em `assert` (sem framework), cobrindo:
- A regex de `ocr_processor.py` linha 105 contra os 4 exemplos: `OP01-001`, `ST03-017`, `P-024`, `PRB02-012`.
- `_resolve_base_url` de `tcg_api_client.py` contra os mesmos 4 prefixos, conferindo a URL base esperada.

---

## O que o dev FRONTEND precisa saber

**Nenhuma mudança de código é necessária.** Levantamento confirmado:
- `card_set_id` / `code` são tratados como `string` livre em toda a base (`LocalCard.ts:6`, bindings em `cards-review.html:20`, `inventory-audit.ts`, `scan-errors.ts`) — sem `pattern`, `maxlength`, `Validators.pattern` ou qualquer regex de formato.
- Um código de 9 caracteres como `PRB02-012` passa por todo o fluxo (input, display, envio pro backend) sem ser truncado ou rejeitado, porque não há limite de tamanho em nenhum lugar.

O único ponto opcional (não bloqueante) são exemplos desatualizados em placeholders de UI, que hoje só citam formatos `OP`/`EB`/`FR`:
- `frontend/src/app/pages/inventory-audit/inventory-audit.html:143` → `placeholder="Código da carta (ex: OP01-016)"`
- `frontend/src/app/pages/deck-building/deck-building.html:13` → `placeholder="Exemplo:&#10;2 EB03-021&#10;1 FR02-001&#10;3 OP01-123"`

Atualizar esses textos para incluir um exemplo de ST/P/PRB é puramente cosmético (ajuda o usuário a saber que os novos formatos são aceitos) — fazer só se quiser polir a UX, não é requisito funcional da feature.

**Ação recomendada para o dev frontend:** nenhuma alteração de código. Validar manualmente (Passo 3 abaixo) que os 3 fluxos que exibem/recebem código de carta continuam funcionando com os novos formatos, já que ninguém vai escrever teste automatizado pra isso no frontend.

---

## Passos de implementação

### Passo 1 — Regex e whitelist de detecção (backend)
- `ocr_processor.py`: whitelist + regex da linha 105 (ver seção 1 acima).
- `llm_processor.py`: `ID_PATTERN` + prompt (ver seção 2 acima).
- `upload_service.py`: as 3 ocorrências de regex de parse de decklist + prompt da LLM de normalização (ver seção 3 acima).

### Passo 2 — Dispatch de endpoint por tipo (backend)
- `tcg_api_client.py`: função `_resolve_base_url` (ver seção 4 acima).

### Passo 3 — Validação manual / QA (backend + frontend)
- Testar detecção end-to-end com uma carta de cada tipo novo (ST, P, PRB) via OCR e via fallback LLM.
- Confirmar que o card retornado da API bate com o esperado para cada endpoint (decks para ST, promos para P e PRB).
- No frontend: colar um código de cada tipo novo manualmente em `inventory-audit` e `scan-errors`, e uma linha de decklist com cada tipo em `deck-building`, conferindo que aparecem corretos na tela e chegam certos no backend.

### Passo 4 — Testes (backend)
- `backend/test_card_code_detection.py` cobrindo a regex de detecção e o `_resolve_base_url`, conforme descrito na seção 4 acima.

## Itens já resolvidos (não precisam de trabalho)

- **Banco de dados**: colunas `TEXT` sem limite de tamanho — nenhuma migração necessária.
- **Frontend**: campos tratados como `string` livre, sem validação de formato/tamanho — nenhuma mudança de código necessária, só validação manual.

## Arquivos impactados (resumo)

- `backend/image_tools/ocr_processor.py`
- `backend/image_tools/llm_processor.py`
- `backend/services/upload_service.py`
- `backend/services/tcg_api_client.py`
- `backend/test_card_code_detection.py` (novo)
