# Adding suport to others SET ID SPEC


- nessa feature vamos adicionar suporte a detecção de outros tipos de cartas. cada tipo de carta tem um tipo de endpoint especifico que é usado.
- temos que adicionar suporte a 3 tipos de cartas que nao temos hoje. Talvez a detecção de texto ja esteja preparada para lidar com os novos tipos de cartas.
    - Lista de Tipos de Cartas novas
        - STXX-XXX (Exemplo ST03-017)
        - P-XXX (Exemplo P-024)
        - PRBXX-XXX (Exemplo PRB02-012)

## Estado atual do sistema (levantado em 2026-08-20)

**Detecção do código (OCR/LLM):**
- O caminho principal não é uma LLM de visão — é OCR via Tesseract (`backend/image_tools/ocr_processor.py`), com fallback para um modelo de visão local via Ollama (`backend/image_tools/llm_processor.py`) só quando o OCR falha.
- `ocr_processor.py:105` usa a regex `(OP|ST|EB)\d{2}-\d{3}` para validar o texto extraído — **já reconhece ST**, mas não reconhece `P-XXX` nem `PRB`.
- `ocr_processor.py:13` define a whitelist de caracteres do Tesseract como `OPSTEB0123456789-` — **falta a letra R**, então "PRB" nunca vai ser lido corretamente pelo OCR.
- `llm_processor.py:6` usa uma regex mais aberta `[A-Z]{2,4}\d{2}-\d{3}` (casaria com PRB), mas o prompt enviado ao modelo (`llm_processor.py:17-24`) descreve o formato como `XX##-###` e usa a mesma whitelist sem R.
- Nenhuma regex do sistema (OCR, LLM, ou `upload_service.py` para parse de decklist) suporta o formato `P-XXX` (letra + traço + 3 dígitos, sem os 2 dígitos de set que os outros formatos têm).

> Correção: um levantamento anterior citou esses trechos de parse de decklist como estando em `review_service.py` — na verdade estão em `backend/services/upload_service.py` (`_parse_plain_cards`, `_normalize_deck_payload_with_llm`, `check_deck_cards`). `review_service.py` existe mas não tem lógica de regex de código de carta.

**Endpoint por tipo de carta:**
- Não existe hoje nenhum dispatch por tipo. `backend/services/tcg_api_client.py` tem uma única `BASE_URL` (`/api/sets/card`) usada para todos os códigos, chamada a partir de 4 pontos: `processor.py`, `routes/library_routes.py`, `services/review_service.py`, `services/upload_service.py`.
- Essa lógica de roteamento por prefixo precisa ser criada do zero, num único ponto (dentro de `tcg_api_client.py`) para que todos os call sites se beneficiem sem duplicação.

**Banco de dados:**
- SQLite, colunas `code`/`card_set_id` são `TEXT` sem limite de tamanho. **Não há risco de truncamento** para códigos maiores como "PRB02-012" (9 chars). Nenhuma alteração de schema é necessária por causa do tamanho do código.

**Frontend:**
- `card_set_id`/`code` são tratados como `string` livre em todo lugar (nenhum `pattern`, `maxlength` ou regex de validação encontrado). Os únicos "formatos" existentes são textos de exemplo em placeholders. Nenhuma alteração é necessária no frontend por causa do formato/tamanho do código.

## Decisões tomadas

- **PRB usa o mesmo endpoint de promos** (`/api/promos/card/{card_set_id}/`) que o tipo P — confirmado, não é engano.
- **Formato de P-XXX é fixo**: sempre `P` + traço + 3 dígitos (ex: `P-024`), sem dígitos de set entre o `P` e o traço, sem variação. A regex de detecção precisa de uma regra própria só para esse caso, separada da regra genérica `PREFIXO + 2 dígitos + traço + 3 dígitos` usada por OP/ST/EB/PRB.
- **Regra do tipo P fica isolada**: em vez de uma única regex combinada, o formato `P-XXX` é tratado como uma regra própria e separada (não tenta encaixar no padrão genérico dos outros tipos).
- **Dispatch de endpoint só dentro de `tcg_api_client.py`**: a lógica de mapear prefixo → URL fica centralizada nesse arquivo; os 4 call sites (`processor.py`, `library_routes.py`, `review_service.py`, `upload_service.py`) não mudam.
- **Whitelist do Tesseract**: basta adicionar a letra `R` (mudança mínima, sem reestruturar a whitelist).

## Cartas do Tipo STXX-XXX
- Para as cartas do tipo ST vamos usar o endpoint `https://www.optcgapi.com/api/decks/card/{card_set_id}/` sendo `card_set_id` o codigo detecado pela nossa LLM.
- devemos revisar a detecção da LLM e ver se ela ja suporte detectção das cartas desse tipo.
- **Status:** a regex de OCR (`ocr_processor.py:105`) já reconhece o formato ST. Falta apenas o dispatch de endpoint em `tcg_api_client.py`.

## Cartas do Tipo P-XXX
- para as cartas do TIPO P vamos usar o endpoint `https://www.optcgapi.com/api/promos/card/{card_set_id}/` sendo `card_set_id` o codigo detecado pela nossa LLM.
- devemos revisar a detecção da LLM e ver se ela ja suporte detectção das cartas desse tipo.
- **Status:** nenhuma regex do sistema suporta esse formato hoje (todas exigem 2 dígitos antes do traço). Precisa de regra de regex própria (`P-\d{3}`) em todos os pontos de detecção/validação, além do dispatch de endpoint.

## Cartas do Tipo PRB
- para as cartas do TIPO PRB vamos usar o endpoint `https://www.optcgapi.com/api/promos/card/{card_set_id}/` sendo `card_set_id` o codigo detecado pela nossa LLM.
- devemos revisar a detecção da LLM e ver se ela ja suporte detectção das cartas desse tipo.
- Devemos ter um cuidado extra nas cartas desse tipo pois elas extrapolam a quantidade de caracteres que estamos acostumados a usar nesse sistema
    - revise o sistema e veja se estamos preparados pare receber esse tipo de carta
        - Verificar backend
        - verifica banco de dados
        - verificar frontend
- **Status:**
    - Backend: whitelist do Tesseract (`OPSTEB0123456789-`) não tem a letra `R` — precisa ser atualizada. Regex do `llm_processor.py` já aceita PRB no formato, mas a do `ocr_processor.py:105` está fechada em `(OP|ST|EB)` e precisa incluir `PRB`. Falta dispatch de endpoint.
    - Banco de dados: **sem problema**, colunas são `TEXT` sem limite de tamanho.
    - Frontend: **sem problema**, campos são `string` livre sem validação de formato/tamanho.