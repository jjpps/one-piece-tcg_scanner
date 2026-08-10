# Padrao unico de ID de carta, compartilhado entre OCR, LLM e upload de decks.
# Prefixos suportados: OP, ST, EB, PRB (2 digitos de set + 3 digitos de numero)
# e o formato promocional P-### (sem numero de set).
CARD_ID_PATTERN = r'(?:OP|ST|EB|PRB)\d{2}-\d{3}|P-\d{3}'
