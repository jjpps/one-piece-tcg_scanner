# Gemini Spec MD

## Overview

- nessa feature iremos substituir o uso de OLLAMA pelo uso de gemini.
vamos usar um modelo especifico que faça com baixo custo.

## Spec details

- hoje nosso sistema utiliza OLLAMA (`ollama.chat`) em dois pontos, ambos em código de produção:
  - `_extrair_id_via_llm` (`backend/image_tools/llm_processor.py`) — fallback de visão quando o OCR (tesseract) não lê o ID da carta. Modelo atual: `glm-ocr`.
  - `_normalize_deck_payload_with_llm` (`backend/services/upload_service.py`) — parse de texto de deck-list colado pelo usuário. Modelo atual: `llama3.2`. Chamado por `build_deck_payload_from_text`, usado em `routes/upload_routes.py`.
- **Nota:** o método `extrair_lista_cards` citado na v1 deste spec está morto (0 chamadores, retorna `"NOTHING YET"`) — já documentado como código morto em `.spec/othersets_plan.md`. Decisão: **não migrar** esse método; migrar o equivalente real, `_normalize_deck_payload_with_llm`. Será removido (ver "Limpeza de código morto").
- Modelo padrão adotado: `gemini-3.5-flash-lite` — modelo estável da linha 3.5, multimodal (texto, imagem, vídeo, áudio, PDF como input; texto como output), otimizado para baixo custo/baixa latência, cobre os dois casos de uso (imagem→texto no OCR fallback e texto→texto no parse de deck-list). Fica configurável via env, então o valor pode ser trocado sem alterar código.
- Ambos os pontos de chamada passam a checar um switch único (`LLM_PROVIDER`) para decidir entre Ollama (local) e Gemini (cloud) — não um toggle por função.
- SDK proposto: `google-genai` (SDK unificado atual do Google para Gemini API), adicionado ao `backend/requirements.txt`.
- Suporte a env via `python-dotenv` (não há nenhuma infra de env no projeto hoje — sem `.env`, sem `config.py`, sem `os.getenv`).

## Must have
- deve ser adicionado ao projeto suporte a env (`python-dotenv`, carregado em um ponto único de bootstrap do backend)
- deve ser gerado uma ENV para o token do gemini: `GEMINI_API_KEY`
- deve ser gerado uma ENV para determinar se usa IA local ou cloud: `LLM_PROVIDER` (`ollama` | `gemini`), switch único usado tanto no fallback de OCR quanto no parse de deck-list
- deve ser gerado uma ENV para o modelo gemini usado: `GEMINI_MODEL` (default `gemini-3.5-flash-lite`)
- o arquivo `.env` deve estar no `.gitignore` para prevenir subidas erradas (hoje **não está** — precisa ser adicionado)
- deve existir um `.env.example` (sem valores reais) documentando as envs acima
- `_extrair_id_via_llm` e `_normalize_deck_payload_with_llm` devem respeitar `LLM_PROVIDER` e cair no mesmo contrato de retorno que têm hoje (mesma assinatura, mesmo formato de saída) para não quebrar `ocr_processor.py` e `upload_routes.py`
- `google-genai` e `python-dotenv` adicionados ao `backend/requirements.txt`

## Limpeza de código morto
Achados durante a exploração desta feature, sem chamadores em todo o repositório — remover ambos junto com a migração:
- `extrair_lista_cards` (`backend/image_tools/llm_processor.py`) — 0 chamadores, retorna `"NOTHING YET"`, não migrado (substituído por `_normalize_deck_payload_with_llm`).
- `load_hashes_from_db` (`backend/repositories/cards_hash_repository.py`) — 0 chamadores; infra não plugada da feature de comparação de imagem (`.spec/imagem_comparation.spec.md`), sem relação com Gemini/Ollama. Removida aqui por estar morta, não por ser parte desta migração — se a feature de comparação de imagem for retomada, a reintrodução fica a cargo daquela spec.

## Fora de escopo
- bug conhecido de hallucination do fallback (`EB03-021` fantasma, ver `.spec/imagem_comparation.spec.md`) — não é objetivo desta feature corrigir, mas deve ser reavaliado após a troca de provider (pode se comportar diferente com Gemini)
