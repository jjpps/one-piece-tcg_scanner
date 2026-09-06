# Detecção e Performance — Spec de Melhorias

## Overview

- Revisão do pipeline de detecção (`extrair_carta` → OCR → fallback LLM) usando como caso real a foto enviada no `/upload` (carta dentro de um organizador plástico, glare, leve rotação, bastante fundo).
- Duas frentes independentes:
  - **Prioritário — Detecção (Gemini)**: melhorar acurácia usando o Gemini como motor principal, tolerante a fundo poluído/rotação/glare.
  - **Performance (Ollama / pipeline local)**: reduzir I/O e reprocessamento desnecessário no caminho local, sem mudar arquitetura.

## Evidência coletada (testado com a foto real do `/upload`)

- Foto original: 1600x720 (retrato). Carta dentro de uma caixa/organizador com paredes plásticas héterogêneas, glare forte na metade superior da carta, leve rotação.
- `_contorno_carta` (Canny + `approxPolyDP` exigindo 4 vértices, área entre 10%-90% do quadro) **falhou** — nenhum contorno aceito, provavelmente porque as bordas retas da caixa/divisória competem com as bordas da carta, mais o glare quebrando o Canny.
- O pipeline caiu no fallback fixo por porcentagem (`carta = img[0.38h:0.86h, 0.01w:0.88w]`) — que por coincidência ainda pegou a carta razoavelmente bem *nesta* foto. Mas esse fallback assume uma posição/tamanho fixo de carta no quadro, sem nenhuma verificação de que a carta de fato caiu dentro do crop; qualquer variação de distância/zoom do usuário quebra essa suposição silenciosamente.
- `ID_REGION` (relativa ao crop acima) e a região dos últimos 15% de altura (enviada ao fallback LLM) capturaram o texto do ID (`EB04-023`) corretamente nesta foto — mas as duas dependem 100% do crop anterior estar certo; se o crop por porcentagem erra, as duas regiões erram em cascata, sem chance de recuperação.
- Tesseract não está instalado no ambiente usado pra este teste — não deu pra validar o OCR real, só o pipeline até o crop (contorno → fallback → recorte de região).

## Foco prioritário — Detecção (Gemini)

Hoje o Gemini só é chamado como fallback depois que uma sequência de heurísticas CV frágeis (contorno → crop fixo → crop de região de ID) já rodou e pode ter cortado errado a região antes mesmo do OCR tentar. As propostas abaixo colocam mais trabalho do lado do Gemini, que é mais tolerante a fundo poluído/rotação do que a heurística de contorno atual.

1. **Mandar a foto inteira pro Gemini quando `LLM_PROVIDER=gemini`, sem depender do crop CV.** Hoje `_extrair_id_via_llm` recebe `carta_cv` já cortado por `extrair_carta` — se esse crop errar (quase aconteceu aqui), o Gemini nunca vê a carta certa. Gemini localiza e lê texto pequeno mesmo com fundo poluído — pular o pré-crop no caminho Gemini e mandar a foto original (ou um resize razoável), deixando o modelo achar a carta e o ID numa única chamada.
2. **Saída estruturada (`response_schema`) em vez de regex sobre texto livre.** Hoje se faz `ID_PATTERN.search(content)` no texto devolvido. `google-genai` suporta `response_mime_type='application/json'` + `response_schema` — pedir `{"card_id": str|null, "confidence": "high"|"low"|"none"}` torna a extração determinística e dá um sinal de confiança pra decidir aceitar ou re-tentar, em vez de confiar em regex sobre texto solto.
3. **Guarda contra a alucinação já conhecida.** Bug documentado (`.spec/imagem_comparation.spec.md`) do fallback "inventar" `EB03-021` quando não tem certeza — com saída estruturada (item 2) e um prompt pedindo explicitamente `confidence: none` em vez de chutar, dá pra rejeitar respostas de baixa confiança automaticamente em vez de aceitar um ID errado.
4. **Segunda chamada de confirmação quando a confiança vier baixa.** Hoje não existe retry — uma tentativa e pronto. Se `confidence: low`, reenviar um recorte mais apertado (a mesma heurística de porcentagem que já existe) como segunda tentativa antes de desistir e marcar a carta como erro.
5. **Tolerância a rotação/perspectiva sem depender do crop CV.** A foto real tinha leve rotação e a carta não alinhada ao quadro. O crop atual por contorno não faz nenhum perspective warp (`_recortar_contorno` só faz bounding-rect axis-aligned) — pedir ao Gemini pra ler o texto independente da orientação (ele já faz isso naturalmente) evita essa dependência no caminho cloud.
6. **Cross-check com nome/set da carta.** O prompt hoje só pede o código. Pedir também nome da carta e set (visíveis no rodapé) e cruzar com a base local (`get_card_data_by_code`) ou API — se o código lido não bate com o nome esperado pro set, é sinal de erro de leitura mesmo com `confidence: high` declarada.

## Foco de performance — Ollama / pipeline local

O caminho local deve continuar rápido e gratuito — melhorias aqui reduzem I/O e reprocessamento desnecessário, sem mudar arquitetura.

1. **Debug images gravadas em disco incondicionalmente.** `extrair_carta` (`cv2.imwrite("debug_detected_card.jpg", ...)`, 2 ocorrências) e `extrair_id_por_ocr` (`cv2.imwrite("debug_ocr_region.jpg", ...)`) escrevem no disco a cada carta processada, sempre sobrescrevendo o mesmo arquivo — I/O sem valor em lote, já que não sobra nada pra debugar depois (sobrescrito a cada imagem). Colocar atrás de uma env (`DEBUG_IMAGES=true`), default desligado.
2. **Downscale antes do Canny/contorno.** `_contorno_carta` roda `Canny`/`findContours` na imagem em resolução total (aqui 1600x720; fotos reais de celular costumam ser bem maiores). Redimensionar pra uma largura de trabalho fixa (ex: 1000px) antes de achar o contorno, e reescalar as coordenadas de volta, reduz o custo de CV sem perder precisão prática.
3. **`keep_alive` explícito no `ollama.chat`.** Hoje não é passado, então depende do timeout default do daemon (5 min) — em processamento em lote (`processor.py`, loop sequencial de várias fotos), se o gap entre fotos passar disso, o modelo recarrega do zero. Setar `keep_alive` alto (ex: `"30m"`) explicitamente enquanto o worker processa um lote evita reload repetido de modelo.
4. **Paralelizar o loop de processamento em lote.** `worker()` em `processor.py` processa uma imagem por vez, sequencialmente, incluindo o Tesseract (CPU-bound). Rodar o lote num `ThreadPoolExecutor`/`multiprocessing.Pool` (2-4 workers) processa várias cartas em paralelo, sem tocar a lógica de OCR/contorno em si — só o driver do lote.
5. **Perspective warp em vez de bounding-rect no crop por contorno.** Quando o contorno É encontrado, `_recortar_contorno` hoje só corta um retângulo alinhado aos eixos — com a carta rotacionada, sobra fundo nas quinas e o texto do ID fica desalinhado, aumentando a chance do Tesseract falhar e cair no fallback LLM (mais lento, e se `gemini`, mais caro). Usar `cv2.getPerspectiveTransform` + `warpPerspective` com os 4 pontos do contorno já detectado corrige isso sem custo adicional de detecção (os pontos já existem), reduzindo quantas cartas precisam do fallback.

## Fora de escopo

- Troca de modelo Ollama (`glm-ocr`, `llama3.2`) ou Gemini (`gemini-3.5-flash-lite`) — já definidos em `gemini_spec.md`.
- Reescrita completa da detecção via modelo de segmentação dedicado — fica como possível v2 se as melhorias incrementais acima não forem suficientes.

## Must have (se esta spec for implementada)

- Nenhuma melhoria aqui deve quebrar o contrato de retorno de `process_image` (`card_id, motivo, cropped_path`) nem dos dois pontos já migrados pro Gemini (`_extrair_id_via_llm`, `_normalize_deck_payload_with_llm`).
- Toda melhoria de performance (seção Ollama) deve ser validável sem custo/chave de API — são mudanças puramente locais.
- Toda melhoria de detecção (seção Gemini) deve ser testável com o par de fotos reais já usado nesta análise antes de considerar concluída.
