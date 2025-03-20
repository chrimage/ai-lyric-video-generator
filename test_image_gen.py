#!/usr/bin/env python3

import os
import google.genai as genai
from google.genai import types
from dotenv import load_dotenv
from PIL import Image
import io
import base64
import traceback

# Load environment variables to get API key
load_dotenv()

# Initialize the Gemini client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Specify the model for image generation
IMAGE_MODEL = "models/gemini-2.0-flash-exp-image-generation"

def generate_image(prompt):
    """
    Generate an image using gemini-2.0-flash-exp-image-generation model
    
    Args:
        prompt (str): Description of the image to generate
        
    Returns:
        PIL.Image or None: The generated image or None if generation failed
    """
    try:
        print(f"Generating image with prompt: {prompt}")
        
        # Set up configuration for image generation
        # Include response_modalities with "Image" to ensure we get image output
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=['Image', 'Text'],  # Specify we want image output
                temperature=0.4,  # Use lower temperature for more predictable output
                max_output_tokens=4096,  # Adjust as needed
            )
        )
        
        # Check if we got a response
        if not response.candidates or not response.candidates[0].content.parts:
            print("No response received")
            return None
        
        # Look for an image in the response
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                # Save and return the image
                image_bytes = part.inline_data.data
                image = Image.open(io.BytesIO(image_bytes))
                return image
            elif hasattr(part, 'text') and part.text:
                print(f"Text response: {part.text[:100]}...")
        
        return None
        
    except Exception as e:
        print(f"Error generating image: {e}")
        traceback.print_exc()
        return None

def save_image(image, output_path):
    """Save a PIL image to disk"""
    if image:
        image.save(output_path)
        print(f"Image saved to {output_path}")
        return True
    return False

if __name__ == "__main__":
    # Test image generation
    prompt = "Create a visually striking image for a lyric video with a neon-lit cityscape at night with the moon in the background. The image should be in 16:9 aspect ratio."
    output_path = "test_image.png"
    
    print(f"Using model: {IMAGE_MODEL}")
    
    # Try generating the image
    image = generate_image(prompt)
    
    if image:
        save_image(image, output_path)
    else:
        print("Failed to generate image")