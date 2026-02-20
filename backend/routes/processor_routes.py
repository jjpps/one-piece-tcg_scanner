from flask import Blueprint, request, jsonify
import os

from processor import get_status

processor_bp = Blueprint('processor', __name__)
@processor_bp.route('/status', methods=['GET'])
def get_status_processor():
    return jsonify(get_status())
    
