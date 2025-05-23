#!/usr/bin/env python3
import base64
import os
import mimetypes
from pathlib import Path
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from .env file
load_dotenv()


def save_binary_file(file_name, data):
    """Save binary data to a file."""
    with open(file_name, "wb") as f:
        f.write(data)
    print(f"File saved to: {file_name}")


def generate_image():
    """Generate an image using Gemini 2.0 Flash Exp Image Generation model."""
    # Initialize client with API key from environment
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Neither GEMINI_API_KEY nor GOOGLE_API_KEY environment variable is set")
    
    client = genai.Client(api_key=api_key)

    # Define the model and prompt
    model = "gemini-2.0-flash-exp-image-generation"
    
    # Create the prompt content
    prompt = "Generate an image of a purple fairy unicorn flying through a magical forest at sunset"
    
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=prompt),
            ],
        ),
    ]
    
    # Configure response to include image modality
    generate_content_config = types.GenerateContentConfig(
        response_modalities=["image", "text"],
        response_mime_type="text/plain",
    )

    print(f"Generating image with prompt: '{prompt}'")
    print("This may take a moment...")
    
    # Use streaming to get image chunks
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        # Skip empty chunks
        if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
            continue
            
        # Handle image data
        part = chunk.candidates[0].content.parts[0]
        if part.inline_data:
            # Create output directory if it doesn't exist
            output_dir = Path("output/generated_images")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the image with appropriate extension
            inline_data = part.inline_data
            file_extension = mimetypes.guess_extension(inline_data.mime_type) or ".png"
            file_name = output_dir / f"purple_fairy_unicorn{file_extension}"
            
            save_binary_file(str(file_name), inline_data.data)
            print(f"Image of mime type {inline_data.mime_type} saved to: {file_name}")
        else:
            # Print any text response
            print(chunk.text)


if __name__ == "__main__":
    generate_image()
