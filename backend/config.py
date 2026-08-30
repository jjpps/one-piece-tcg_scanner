import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')
DEBUG_IMAGES = os.getenv('DEBUG_IMAGES', 'false').lower() == 'true'
OLLAMA_KEEP_ALIVE = os.getenv('OLLAMA_KEEP_ALIVE', '30m')
PROCESS_WORKERS = int(os.getenv('PROCESS_WORKERS', '4'))
# 429 (cota) é por API key e responde a baixar isso; 503 ("high demand") é
# capacidade do modelo no lado do Google e NÃO melhora serializando — nesse caso
# o retry com jitter é que resolve, não reduzir a concorrência.
# ponytail: se o 503 persistir mesmo com retry, o próximo passo é um
# GEMINI_MODEL_FALLBACK pra um modelo menos disputado.
GEMINI_MAX_CONCURRENCY = int(os.getenv('GEMINI_MAX_CONCURRENCY', '3'))
# Sem timeout, uma request pendurada segura o semáforo pra sempre e o lote trava.
GEMINI_TIMEOUT_SECONDS = int(os.getenv('GEMINI_TIMEOUT_SECONDS', '30'))
# Ler um código de 8 caracteres não precisa de raciocínio — 0 desliga o thinking.
# Se o modelo não aceitar desligar, use -1 pra não mandar a config.
GEMINI_THINKING_BUDGET = int(os.getenv('GEMINI_THINKING_BUDGET', '0'))
