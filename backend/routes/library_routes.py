from flask import Blueprint, request, jsonify
from repositories.cards_repository import get_all_cards

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
    
