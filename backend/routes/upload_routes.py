from flask import Blueprint, request, jsonify
import os
import processor
from services.upload_service import build_deck_payload_from_text, check_deck_cards

upload_bp = Blueprint('upload', __name__)

IMAGES_FOLDER = 'images'
ERROR_IMAGES_FOLDER = 'images_with_errors'
os.makedirs(IMAGES_FOLDER, exist_ok=True)
os.makedirs(ERROR_IMAGES_FOLDER, exist_ok=True)


@upload_bp.route('/upload', methods=['POST'])
def upload_images():
    print("Recebendo solicitação de upload de imagens")
    if 'images' not in request.files:
        return jsonify({"error": "Nenhuma imagem enviada"}), 400

    files = request.files.getlist('images')

    if not files:
        return jsonify({"error": "Lista de arquivos vazia"}), 400

    allowed_extensions = ('.png', '.jpg', '.jpeg')

    uploaded = []
    errors = []

    for file in files:
        if file.filename == '':
            errors.append("Arquivo com nome vazio ignorado")
            continue

        if not file.filename.lower().endswith(allowed_extensions):
            errors.append(f"{file.filename} - extensão não permitida")
            continue

        filepath = os.path.join(IMAGES_FOLDER, file.filename)
        file.save(filepath)
        uploaded.append(file.filename)
    
    processor.start_processing(IMAGES_FOLDER)

    return jsonify({
        "uploaded": uploaded,
        "errors": errors,
        "total_uploaded": len(uploaded)
    })

@upload_bp.route('/upload/deck', methods=['POST'])
def upload_deck():    
    try:
        data = request.get_json()
        if isinstance(data, list):
            payload = build_deck_payload_from_text('\n'.join(str(item) for item in data))
            deckName = payload.get('deckName', 'Deck')
            cards = payload.get('cards', [])
        elif isinstance(data, dict) and 'cards' in data and isinstance(data.get('cards'), list):
            deckName = data.get('deckName', 'Deck')
            cards = data.get('cards', [])
        else:
            deckName = data.get('metadata', {}).get('name')
            cards = data.get('deck',{}).get('Main Deck',[])

        if isinstance(cards, list) and cards and isinstance(cards[0], str):
            payload = build_deck_payload_from_text('\n'.join(str(item) for item in cards))
            cards = payload.get('cards', [])

        if not cards:
            return jsonify({"error": "Nenhuma carta válida foi normalizada pela LLM"}), 400

        normalized_cards = []
        for card in cards:
            if isinstance(card, dict):
                normalized_cards.append({
                    'code': card.get('code') or card.get('id') or '',
                    'quantity': card.get('quantity') or card.get('count') or card.get('quantityRequired') or 1
                })
            else:
                normalized_cards.append({'code': str(card), 'quantity': 1})

        anyCardOwned, processedDeckCards = check_deck_cards(normalized_cards)
        if anyCardOwned:
            return jsonify({
                "deckName": deckName,
                "cards": [card.__dict__ for card in processedDeckCards]
            }), 200
        else:
            return jsonify({
                "deckName": deckName,
                "cards": None
            }),404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
