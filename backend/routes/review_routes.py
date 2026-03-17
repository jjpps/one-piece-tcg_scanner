from pathlib import Path

from flask import Blueprint, request, jsonify, send_from_directory, url_for

from dtos.local_card_dto import LocalCard
from services.review_service import get_local_cards_as_dicts, approve_card, reprove_card

IMAGES_FOLDER = "images"

review_bp = Blueprint('review', __name__)


@review_bp.route('/reviews', methods=['GET'])
def get_reviews():
    """Return the list of local cards read from processed_cards.json."""
    cards = get_local_cards_as_dicts()

    # Convert local_imagem paths to an accessible URL for front-end consumption
    enriched = []
    for card in cards:
        filename = Path(card.get('local_imagem', '')).name
        card['local_image_url'] = url_for('review.serve_local_image', filename=filename, _external=True)
        enriched.append(card)

    return jsonify(enriched)


@review_bp.route('/reviews/images/<path:filename>', methods=['GET'])
def serve_local_image(filename):
    """Serve local card images from the images folder."""
    return send_from_directory(IMAGES_FOLDER, filename)

@review_bp.route('/reviews/approve', methods=['POST'])
def approve():  
    cardData = request.get_json(force=True)
    if(cardData is None):
        return jsonify({"status": "error", "message": "No card data provided"}), 400
    
    card = LocalCard(
        local_imagem=cardData.get("local_imagem"),
        card_image=cardData.get("card_image", ""),
        card_name=cardData.get("card_name"),
        card_set_id=cardData.get("card_set_id", ""),
        exists=cardData.get("exists", False)
    )
    if approve_card(card):
        return jsonify({},201)
    else:
        return jsonify({"status": "error", "message": "Failed to approve card"}), 400

@review_bp.route('/reviews/reprove', methods=['POST'])
def reprove():  
    cardData = request.get_json(force=True)
    if(cardData is None):
        return jsonify({"status": "error", "message": "No card data provided"}), 400
    
    card = LocalCard(
        local_imagem=cardData.get("local_imagem"),
        card_image=cardData.get("card_image", ""),
        card_name=cardData.get("card_name"),
        card_set_id=cardData.get("card_set_id", ""),
        exists=cardData.get("exists", False)
    )
    if reprove_card(card):
        return jsonify({},201)
    else:
        return jsonify({"status": "error", "message": "Failed to reprove card"}), 400