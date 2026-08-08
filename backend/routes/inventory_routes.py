from flask import Blueprint, request, jsonify
from services import inventory_service as service
from services.inventory_service import (
    SessionNotOpenError,
    ItemNotFoundError,
    InvalidQuantityError,
    DuplicateItemError,
    CardAlreadyInLibraryError,
    CardNotFoundError,
)

inventory_bp = Blueprint('inventory', __name__)

ERROR_STATUS = {
    SessionNotOpenError: 409,
    ItemNotFoundError: 404,
    InvalidQuantityError: 400,
    DuplicateItemError: 400,
    CardAlreadyInLibraryError: 409,
    CardNotFoundError: 404,
}


def _handle(fn):
    try:
        return fn()
    except tuple(ERROR_STATUS.keys()) as e:
        return jsonify({'error': str(e) or e.__class__.__name__}), ERROR_STATUS[type(e)]
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@inventory_bp.route('/inventory/session', methods=['GET'])
def get_session():
    return _handle(lambda: (jsonify({'session': service.get_current_session()}), 200))


@inventory_bp.route('/inventory/session', methods=['POST'])
def create_session():
    return _handle(lambda: (jsonify(service.start_new_session()), 201))


@inventory_bp.route('/inventory/session/<int:session_id>/colors', methods=['GET'])
def get_colors(session_id):
    return _handle(lambda: (jsonify(service.get_colors_view(session_id)), 200))


@inventory_bp.route('/inventory/session/<int:session_id>/items', methods=['GET'])
def list_items(session_id):
    def run():
        color = request.args.get('color')
        status = request.args.get('status', 'pending')
        search = request.args.get('search')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))

        items, total = service.get_items_view(session_id, color=color, status=status, search=search, page=page, page_size=page_size)
        return jsonify({'items': items, 'total': total, 'page': page, 'page_size': page_size}), 200
    return _handle(run)


@inventory_bp.route('/inventory/session/<int:session_id>/items/<code>', methods=['PATCH'])
def review_item(session_id, code):
    def run():
        data = request.get_json(force=True) or {}
        changed = bool(data.get('changed'))
        counted_quantity = data.get('counted_quantity')
        item = service.review_item(session_id, code.strip().upper(), changed, counted_quantity)
        return jsonify(item), 200
    return _handle(run)


@inventory_bp.route('/inventory/lookup/<code>', methods=['GET'])
def lookup(code):
    def run():
        card = service.lookup_card(code)
        return jsonify(card.__dict__), 200
    return _handle(run)


@inventory_bp.route('/inventory/session/<int:session_id>/items', methods=['POST'])
def add_item(session_id):
    def run():
        data = request.get_json(force=True) or {}
        item = service.add_new_card(session_id, data.get('code', ''), data.get('counted_quantity'))
        return jsonify(item), 201
    return _handle(run)


@inventory_bp.route('/inventory/session/<int:session_id>/diff', methods=['GET'])
def diff(session_id):
    return _handle(lambda: (jsonify(service.get_diff(session_id)), 200))


@inventory_bp.route('/inventory/session/<int:session_id>/apply', methods=['POST'])
def apply(session_id):
    return _handle(lambda: (jsonify(service.apply(session_id)), 200))
