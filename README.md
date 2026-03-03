# tcg_scanner

Projeto para leitura e processamento automático de códigos de cartas One Piece a partir de imagens.

Estrutura do repositório
- `frontend/` — aplicação Angular (UI) responsável pelo upload e interação do usuário.
- `backend/` — API Flask que processa imagens, realiza OCR e persiste informações em banco SQLite.
- `images/` — pasta para armazenar imagens enviadas para processamento.
- `images_with_errors/` — imagens que falharam no processamento (renomeadas com GUID para evitar colisões).

Principais funcionalidades
- Processamento de imagens para extrair o código das cartas (OCR via Tesseract).
- Consulta à API externa (`services/tcg_api_client.py`) para obter metadados da carta a partir do código.
- Persistência em banco SQLite (`db.sqlite`) através de funções em `repositories/cards_repository.py`.
- Endpoint REST para iniciar processamento e consultar status.

Backend — dependências (atualizadas)
- flask
- flask-cors
- requests
- opencv-python
- pillow
- pytesseract

Configuração e execução (backend)
1. Instale dependências do backend:

```bash
pip install -r backend/requirements.txt
```

2. Execute a API (modo desenvolvimento):

```bash
python backend/app.py
```

Configuração e execução (frontend)
1. Instale dependências do frontend:

```bash
npm install
```

2. Execute do frontend (modo desenvolvimento):

```bash
npm run start
```

Configuração do Tesseract (Windows)
- O caminho do executável do Tesseract é configurado por `backend/image_processor.py` quando executado no Windows:
	- `C:\Program Files\Tesseract-OCR\tesseract.exe` (ajuste se seu Tesseract estiver em outro local).

Como funciona o processamento
- Coloque imagens na pasta `images/` (a UI do `frontend` também faz upload para lá).
- Um worker em `backend/processor.py` varre a pasta, usa `image_processor.process_image()` para extrair o código, consulta a API externa e salva no banco.
- Imagens processadas com sucesso são removidas; imagens com falha são movidas para `images_with_errors/` e renomeadas com um GUID (para evitar conflitos).

Banco de dados
- Arquivo: `backend/db.sqlite` (criando automaticamente na primeira execução).
- Esquema básico definido em `backend/database.py` e funções de acesso em `backend/repositories/cards_repository.py`.

API (rotas principais)
- Upload e endpoints de processamento estão em `backend/routes/`.
- `GET /` retorna uma mensagem simples de status.

Contribuições e desenvolvimento
- Abra issues ou PRs para melhorias, correções de OCR ou suporte a outras coleções de cartas.

### Biblioteca de Cartas Fornecidas por [apitcg](apitcg.com/platform)

