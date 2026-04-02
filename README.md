# tcg_scanner

Project for automatic reading and processing of One Piece card codes from images.

## Overview

The project consists of two parts:
- `backend/` — Flask API responsible for receiving uploads, processing images with OCR, and storing cards in SQLite.
- `frontend/` — Angular app that allows uploading images, tracking processing status, reviewing cards, and managing the library.

## How it works

1. The user uploads images through the frontend.
2. The backend saves the files to `backend/images/` and starts a worker in `backend/processor.py`.
3. The worker processes each image with `backend/image_tools/ocr_processor.py` and tries to extract the card code.
4. If the code is extracted, the backend queries an external API in `backend/services/tcg_api_client.py` to fetch card metadata.
5. Valid cards can be:
   - marked as existing in the database (`backend/db.sqlite`), or
   - added to the local review queue in `backend/processed_cards.json`.
6. Unrecognized images or OCR failures are moved to `backend/images_with_errors/`.

## Requirements

- Python 3
- Node.js / npm
- Tesseract OCR installed
- Python dependencies in `backend/requirements.txt`
- Node dependencies in `frontend/package.json`

## Backend

### Installation

```bash
cd backend
pip install -r requirements.txt
```

### Run

```bash
python app.py
```

The Flask server starts at `http://localhost:5000`.

### Ollama and the OCR fallback model

The backend uses Ollama as a local LLM fallback when regular OCR fails.
The model used is `glm-ocr`, configured in `backend/image_tools/llm_processor.py`.
Ollama is required for this fallback path, and the Python package `ollama` is imported in the backend.

Download Ollama here:
- https://ollama.ai/download

### Main endpoints

- `GET /` — checks if the API is running.
- `POST /api/upload` — accepts multipart upload with field `images` and starts processing.
- `GET /api/status` — returns the current processing status.
- `GET /api/library` — lists cards saved in the database.
- `GET /api/library/errors` — lists images that failed OCR.
- `POST /api/library/errors/:fileName` — saves a card manually from an OCR error.
- `POST /api/library/addCard` — increases the quantity of an existing card.
- `DELETE /api/library/removeCard/:code` — decreases the quantity of a card.
- `GET /api/reviews` — returns locally detected cards in `processed_cards.json` for review.
- `POST /api/reviews/approve` — approves a locally detected card.
- `POST /api/reviews/reprove` — rejects a locally detected card.

### Tesseract configuration

The backend sets the default Windows Tesseract executable path in `backend/image_tools/ocr_processor.py`:

```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

If Tesseract is installed in a different location, update this path.

## Frontend

### Installation

```bash
cd frontend
npm install
```

### Run

```bash
npm run start
```

The Angular app runs at `http://localhost:4200`.

## Frontend usage

### Main pages

- **Home** — shows how many cards are waiting for review and provides navigation.
- **Scan Cards** — upload images and monitor processing.
- **Library** — lists saved cards, search by code or name, and adjust quantities.
- **Scan Errors** — shows images that were not recognized and allows manual code entry.
- **Cards Review** — review locally extracted cards and approve or reject each item.

### Recommended flow

1. Open `Scan Cards` and upload card images.
2. Wait for processing to complete using the status bar.
3. Check `Cards Review` to approve or reject local detections.
4. Open `Library` to view or adjust saved card quantities.
5. Use `Scan Errors` to manually correct images that failed OCR.

## Data structure

- `backend/db.sqlite` — SQLite database where approved cards are saved.
- `backend/processed_cards.json` — locally detected cards stored for review.
- `backend/images/` — images uploaded by the frontend.
- `backend/images_with_errors/` — images moved after OCR failure or invalid lookup.

## Notes

- The backend uses the external `OPTTCG` API in `backend/services/tcg_api_client.py` to fetch card details by code.
- Card code recognition depends on OCR and may fail on low-quality images.
- Failed images are saved with unique GUID filenames in `backend/images_with_errors/`.
- the first image to be traded from OCR or LLM model usually takes longer

## Development

- Backend code is in `backend/app.py` and `backend/routes/`.
- Frontend code is in `frontend/src/app/`.
- OCR adjustments are in `backend/image_tools/ocr_processor.py`.
- Asynchronous processing logic is in `backend/processor.py`.

## Picture Angle 

Today the code are configured to read a picture in this [angle](picture.jpg). If you need to change the angle or need to adjust to your picute the code you have to change can be found on `backend/image_tools/ocr_processor.py`
```python
ID_REGION = {'y1': 0.85, 'y2': 0.97, 'x1': 0.55, 'x2': 0.92}
```
