from .upload_routes import upload_bp
from .processor_routes import processor_bp

def register_routes(app):
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(processor_bp, url_prefix='/api')
