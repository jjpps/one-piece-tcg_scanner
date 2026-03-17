from flask import Flask, jsonify
from flask_cors import CORS
from database import init_db
from routes import register_routes


def create_app():
    app = Flask(__name__)
    CORS(app)
    # Inicializa banco
    init_db()
    # Registra rotas
    register_routes(app)

    @app.route('/')
    def home():
        return jsonify({
            "message": "Scanner API is running"
        })

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
