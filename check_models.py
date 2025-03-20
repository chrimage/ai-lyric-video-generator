#!/usr/bin/env python3

import os
import google.genai as genai
from dotenv import load_dotenv
from google.genai import types
import inspect

# Load environment variables to get API key
load_dotenv()

# Initialize the Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Get the list of available models
print("Available models:")
try:
    # Show all gemini-2.0-flash models
    flash_models = []
    for model in client.models.list():
        if "gemini-2.0-flash" in model.name:
            flash_models.append(model)
    
    # Print details about the flash models
    print(f"\nFound {len(flash_models)} gemini-2.0-flash models:")
    for model in flash_models:
        print(f"\n* {model.name}")
        
        # Print all attributes of the model object
        for attr in dir(model):
            if not attr.startswith('_') and attr != 'name':  # Skip private attributes and name
                try:
                    value = getattr(model, attr)
                    if not callable(value):  # Skip methods
                        print(f"  ├── {attr}: {value}")
                except Exception as e:
                    print(f"  ├── {attr}: Error accessing: {e}")
    
    # Specifically check the model that might support image generation
    image_model_name = "models/gemini-2.0-flash-exp-image-generation"
    print(f"\n\nExamining image generation model: {image_model_name}")
    
    # Show the GenerateContentConfig options
    print("\nGenerateContentConfig options:")
    for param_name, param in inspect.signature(types.GenerateContentConfig).parameters.items():
        if param_name != 'self':
            print(f"  - {param_name}: {param.annotation}")
            
    # Check ResponseModality options
    print("\nAvailable response modalities:")
    if hasattr(types, 'ResponseModality'):
        for attr in dir(types.ResponseModality):
            if not attr.startswith('_'):
                print(f"  - {attr}")

except Exception as e:
    print(f"Error: {e}")