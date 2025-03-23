import os
from pathlib import Path

class Config:
    """Base configuration class"""
    # Flask config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'development-key-change-in-production'
    
    # SQLAlchemy config
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Output directory configuration
    # Use Path for cross-platform path handling
    BASE_DIR = Path(os.path.abspath(os.path.dirname(__file__))).parent
    OUTPUT_DIR = os.environ.get('OUTPUT_DIR') or str(BASE_DIR / 'output')
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Task configuration
    MAX_CONCURRENT_TASKS = int(os.environ.get('MAX_CONCURRENT_TASKS') or 1)
    
    # API key config for AI services
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
