from flask import Blueprint, request, jsonify, send_from_directory, url_for
from services.tcg_api_client import get_card_by_code
from repositories.cards_repository import add_card_quantity, card_exists, get_all_cards, save_to_db
import os

ERROR_IMAGES_FOLDER = 'images_with_errors'


library_bp = Blueprint('library', __name__)
@library_bp.route('/library', methods=['GET'])
def get_library():
    cards = get_all_cards()
    library = [
        {
            "code": card[0],
            "image_url": card[1],
            "card_name": card[2],
            "quantity": card[3]
        }
        for card in cards
    ]

    return jsonify(library)
    
@library_bp.route('/library/errors', methods=['GET'])
def get_error_images():
    if not os.path.exists(ERROR_IMAGES_FOLDER):
        return jsonify([])

    error_files = [
        f
        for f in os.listdir(ERROR_IMAGES_FOLDER)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]
    library = [
        {
            "id": card,
            "code": 'UNKNOWN',
            "image_url": url_for('library.serve_error_image', filename=card, _external=True),
            "card_name": 'UNKNOWN',
            "quantity": 1
        }
        for card in error_files
    ]

    return jsonify(library)


@library_bp.route('/library/images_with_errors/<path:filename>', methods=['GET'])
def serve_error_image(filename):
    return send_from_directory(ERROR_IMAGES_FOLDER, filename)


@library_bp.route('/library/errors/<card_id>', methods=['POST'])
def save_error_card(card_id):
    try:
        data = request.get_json()
        code = data.get('code')
        
        if not code:
            return jsonify({'error': 'Code is required'}), 400
        
        if code:
            if card_exists(code):
                add_card_quantity(code)
                print(f"Cartão já existe. Quantidade atualizada: {code}")
            else:
                card = get_card_by_code(code)
                if card:
                    save_to_db(card.code,card.images.large,card.name)
                    print(f"Cartão salvo: {code}")

            os.remove(os.path.join(ERROR_IMAGES_FOLDER, os.path.basename(card_id)))
        else:
            print(f"Falha ao processar: {card_id}")
            os.rename(card_id, os.path.join(ERROR_IMAGES_FOLDER, os.path.basename(card_id)))
           
        
        return jsonify({'message': 'Card saved successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500