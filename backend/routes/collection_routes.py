from flask import Blueprint, jsonify

from services import collection_service as service

collection_bp = Blueprint('collections', __name__)


@collection_bp.route('/collections', methods=['GET'])
def get_collections():
    return jsonify(service.tracker())
