import os
from flask import Flask
from ai_lyric_video_generator.web.models import db

def create_app(config=None):
    """
    Create and configure the Flask application
    
    Args:
        config: Configuration object to use (from config.py)
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__, static_folder='static')
    
    # Load configuration
    if config:
        app.config.from_object(config)
    else:
        # Import here to avoid circular imports
        from ai_lyric_video_generator.config import config as default_config
        app.config.from_object(default_config)

    # Set SQLAlchemy database URI
    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    
    # Initialize SQLAlchemy
    db.init_app(app)

    # Import and register blueprints
    from ai_lyric_video_generator.web.routes import main_bp, api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
    
    return app
