#!/usr/bin/env python3
"""
Unified Configuration System for AI Lyric Video Generator

This module provides a centralized configuration for both CLI and web interfaces.
Configuration can be overridden via environment variables and command-line arguments.
"""
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Base configuration class for the entire application"""
    
    # Base directories
    BASE_DIR = Path(os.path.abspath(os.path.dirname(__file__)))
    OUTPUT_DIR = os.environ.get('OUTPUT_DIR') or str(BASE_DIR / 'output')
    DOWNLOADS_DIR = os.environ.get('DOWNLOADS_DIR') or str(BASE_DIR / 'downloads')
    
    # Ensure directories exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    
    # Flask web app config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'development-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Task configuration
    MAX_CONCURRENT_TASKS = int(os.environ.get('MAX_CONCURRENT_TASKS') or 1)
    
    # API Configuration
    AVAILABLE_API = "mock"  # Options: mock, gemini, dall-e, stability
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    
    # Model Configuration
    IMAGE_GENERATION_MODEL = "models/gemini-2.0-flash-exp-image-generation"
    THINKING_MODEL = "models/gemini-2.0-flash-thinking-exp"
    
    # Image Generation Settings
    DEFAULT_IMAGE_WIDTH = 1280
    DEFAULT_IMAGE_HEIGHT = 720
    
    # Processing Settings
    DEFAULT_BATCH_SIZE = 5
    DEFAULT_BATCH_DELAY = 5.0
    MAX_REVISION_ATTEMPTS = 3
    MAX_API_RETRIES = 3 # Added from image_generator usage
    INITIAL_BACKOFF_DELAY = 1.0 # Added from image_generator usage
    GEMINI_IMAGE_RPM = int(os.environ.get('GEMINI_IMAGE_RPM') or 60) # Added missing config for rate limiting (default 60 RPM)
    
    @classmethod
    def initialize_ai_client(cls):
        """Initialize the AI client if API keys are available"""
        try:
            if cls.GEMINI_API_KEY:
                import google.genai as genai
                client = genai.Client(api_key=cls.GEMINI_API_KEY)
                cls.AVAILABLE_API = "gemini"
                print("Gemini API available")
                return client
            else:
                print("Gemini API key not found in environment variables")
                return None
        except ImportError:
            print("Gemini API not available - using mock generation")
            return None
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'Config':
        """Create a new config instance with overridden values from dict"""
        new_config = Config()
        for key, value in config_dict.items():
            if hasattr(new_config, key):
                setattr(new_config, key, value)
        return new_config
    
    @classmethod
    def from_cli_args(cls, args) -> 'Config':
        """Create a new config instance from command line arguments"""
        config_dict = {}
        
        # Map command line args to config attributes
        if hasattr(args, 'api_key') and args.api_key:
            config_dict['GEMINI_API_KEY'] = args.api_key
            
        if hasattr(args, 'output') and args.output:
            config_dict['OUTPUT_DIR'] = args.output
            
        return cls.from_dict(config_dict)

# Default application config instance
config = Config()

# Initialize AI client
ai_client = Config.initialize_ai_client()
