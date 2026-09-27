from flask import Blueprint, request, jsonify
from services import sync_service as service
from services.sync_service import (
    SessionNotOpenError,
    SessionConflictError,
    InvalidCsvError,
    InvalidResolutionError,
    ItemNotFoundError,
    PendingItemsError,
)

sync_bp = Blueprint('sync', __name__)

ERROR_STATUS = {
    SessionNotOpenError: 409,
    SessionConflictError: 409,
    InvalidCsvError: 400,
    InvalidResolutionError: 400,
    ItemNotFoundError: 404,
    PendingItemsError: 409,
}


def _handle(fn):
    try:
        return fn()
    except InvalidCsvError as e:
        return jsonify({'error': str(e), 'errors': e.errors}), 400
    except tuple(ERROR_STATUS.keys()) as e:
        return jsonify({'error': str(e) or e.__class__.__name__}), ERROR_STATUS[type(e)]
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@sync_bp.route('/sync/session', methods=['GET'])
def get_session():
    return _handle(lambda: (jsonify({'session': service.get_current_session()}), 200))


@sync_bp.route('/sync/session', methods=['POST'])
def create_session():
    def run():
        file = request.files.get('file')
        if not file:
            return jsonify({'error': 'Envie o CSV do Binder no campo "file"'}), 400
        # utf-8-sig: tolera BOM de CSVs exportados por planilhas
        return jsonify(service.start_session(file.read().decode('utf-8-sig'))), 201
    return _handle(run)


@sync_bp.route('/sync/session/<int:session_id>/discard', methods=['POST'])
def discard(session_id):
    def run():
        service.discard_session(session_id)
        return jsonify({'discarded': session_id}), 200
    return _handle(run)


@sync_bp.route('/sync/session/<int:session_id>/items', methods=['GET'])
def list_items(session_id):
    def run():
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
        items, total = service.get_items_view(
            session_id,
            kind=request.args.get('kind'),
            color=request.args.get('color'),
            status=request.args.get('status'),
            search=request.args.get('search'),
            page=page,
            page_size=page_size,
        )
        return jsonify({'items': items, 'total': total, 'page': page, 'page_size': page_size}), 200
    return _handle(run)


@sync_bp.route('/sync/session/<int:session_id>/items/<code>', methods=['PATCH'])
def resolve_item(session_id, code):
    def run():
        data = request.get_json(force=True) or {}
        return jsonify(service.resolve_item(session_id, code.strip().upper(), data.get('resolution'))), 200
    return _handle(run)


@sync_bp.route('/sync/session/<int:session_id>/resolve', methods=['POST'])
def resolve_bulk(session_id):
    def run():
        data = request.get_json(force=True) or {}
        result = service.resolve_bulk(session_id, data.get('resolution'), data.get('kind'), data.get('color'))
        return jsonify(result), 200
    return _handle(run)


@sync_bp.route('/sync/session/<int:session_id>/commit', methods=['POST'])
def commit(session_id):
    return _handle(lambda: (jsonify(service.commit(session_id)), 200))
