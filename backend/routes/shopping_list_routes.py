from flask import Blueprint, jsonify, request

from repositories import shopping_list_repository as repo
from services import shopping_list_service as service

shopping_list_bp = Blueprint('shopping_list', __name__)


@shopping_list_bp.route('/shopping-list', methods=['GET'])
def get_list():
    return jsonify(repo.list_items())


@shopping_list_bp.route('/shopping-list/import', methods=['POST'])
def import_list():
    text = (request.get_json(silent=True) or {}).get('text', '')
    if not text.strip():
        return jsonify({'error': 'Text is required'}), 400
    try:
        return jsonify(service.import_text(text))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@shopping_list_bp.route('/shopping-list/items', methods=['POST'])
def add_item():
    data = request.get_json(silent=True) or {}
    try:
        quantity = int(data.get('quantity', 1))
        return jsonify(service.add_item(data.get('code') or '', quantity)), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except LookupError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@shopping_list_bp.route('/shopping-list', methods=['DELETE'])
def clear_list():
    repo.clear()
    return jsonify({'message': 'Shopping list cleared'})
