import ollama
import base64
import cv2
import re

ID_PATTERN = re.compile(r'[A-Z]{2,4}\d{2}-\d{3}|P-\d{3}')
def _extrair_id_via_llm(carta_cv):
    """Fallback: usa LLM local via Ollama para ler o ID quando OCR falha."""
    
    # Envia só a região inferior — menos tokens, mais foco
    h, w = carta_cv.shape[:2]
    regiao = carta_cv[int(0.85*h):, :]
    
    _, buffer = cv2.imencode('.jpg', regiao)
    img_base64 = base64.b64encode(buffer).decode('utf-8')

    response = ollama.chat(
        model='glm-ocr',
        messages=[{
            'role': 'user',
            'content': 'This is the bottom of a One Piece trading card. Read the card ID code. Formats: XX##-### (example: EB03-021, ST03-017, PRB02-012) or P-### (example: P-024). Reply with ONLY the ID code, nothing else. You cannot take more than 30 seconds to identify. This is character whitelist OPSTEBR0123456789-',
            'images': [img_base64]
        }]
    )
    match = ID_PATTERN.search(response['message']['content'].strip())
    return match.group() if match else None

def extrair_lista_cards(texto):
    """Extrai uma lista de IDs de cartas do texto, usando regex."""
    response = ollama.chat(
        model='llama3.2',        
        messages=[{
            'role': 'user',
            'content': """ 
                You are a parser.

                Convert the given deck list into JSON.
                Not all text will be in the same format, some can be a Json others can be a plain text, so you need to be flexible and extract the card IDs regardless of the format.
                Rules:
                    - Output ONLY valid JSON
                    - Do not explain anything
                    - Extract id and count for each card
                    - Ignore card names
                    - Card ID format: XX##-### (e.g., EB03-021)   
                
                Here is the deck list:
                {texto}
            """
        }]        
    )
    print(f"LLM response: {response['message']['content']}")
    return "NOTHING YET"