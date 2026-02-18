from flask import Blueprint, request, jsonify
import os

upload_bp = Blueprint('upload', __name__)

IMAGES_FOLDER = 'images'
os.makedirs(IMAGES_FOLDER, exist_ok=True)


@upload_bp.route('/upload', methods=['POST'])
def upload_images():
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

    return jsonify({
        "uploaded": uploaded,
        "errors": errors,
        "total_uploaded": len(uploaded)
    })
