from .upload_routes import upload_bp

def register_routes(app):
    app.register_blueprint(upload_bp, url_prefix='/api')
