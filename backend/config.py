import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')
DEBUG_IMAGES = os.getenv('DEBUG_IMAGES', 'false').lower() == 'true'
OLLAMA_KEEP_ALIVE = os.getenv('OLLAMA_KEEP_ALIVE', '30m')
PROCESS_WORKERS = int(os.getenv('PROCESS_WORKERS', '4'))
# Cota do Gemini é por API key, não por thread — serializa por padrão (1) pra não
# estourar "high demand"/limite de requisição quando várias cartas processam em paralelo.
GEMINI_MAX_CONCURRENCY = int(os.getenv('GEMINI_MAX_CONCURRENCY', '1'))
