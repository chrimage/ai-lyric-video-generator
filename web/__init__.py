import os
from flask import Flask
from web.models import db
from web.config import Config

def create_app(config_class=Config):
    """Create and configure the Flask application"""
    app = Flask(__name__, static_folder='static')
    app.config.from_object(config_class)
    
    # Initialize SQLAlchemy
    db.init_app(app)
    
    # Import and register blueprints
    from web.routes import main_bp, api_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
    
    return app
