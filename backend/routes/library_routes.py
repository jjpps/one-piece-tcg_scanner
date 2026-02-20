from flask import Blueprint, request, jsonify
import os

library_bp = Blueprint('library', __name__)
@library_bp.route('/library', methods=['GET'])
def get_library():
    return jsonify({'library':'This is the library endpoint.'})
    
