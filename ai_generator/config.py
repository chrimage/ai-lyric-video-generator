"""
Configuration for AI Generator
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
AVAILABLE_API = "mock"  # Options: mock, gemini, dall-e, stability

# Model Configuration
IMAGE_GENERATION_MODEL = "models/gemini-2.0-flash-exp-image-generation"
THINKING_MODEL = "models/gemini-2.0-flash-thinking-exp"

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Image Generation Settings
DEFAULT_IMAGE_WIDTH = 1280
DEFAULT_IMAGE_HEIGHT = 720

# Processing Settings
DEFAULT_BATCH_SIZE = 5
DEFAULT_BATCH_DELAY = 5.0
MAX_REVISION_ATTEMPTS = 3

# Initialize Gemini client if available
try:
    import google.genai as genai
    
    # Initialize the Gemini client if API key exists
    if GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
        AVAILABLE_API = "gemini"
        print("Gemini API available")
    else:
        client = None
        print("Gemini API key not found in environment variables")
except ImportError:
    client = None
    print("Gemini API not available - using mock generation")
