# tcg_scanner - Projeto para leitura de código de cartas One Piece

Estrutura sugerida:
- main.py: script principal
- db.sqlite: banco de dados local
- images/: pasta para imagens a serem processadas

O fluxo será:
1. Usuário coloca uma imagem em images/
2. Executa o script main.py
3. O script faz OCR no canto inferior direito e salva o código extraído no banco SQLite

Dependências sugeridas:
- opencv-python
- pytesseract
- pillow
- sqlite3 (nativo)

Próximo passo: criar main.py e requirements.txt
