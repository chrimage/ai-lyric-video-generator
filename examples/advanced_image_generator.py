#!/usr/bin/env python3
"""
Advanced Image Generator for Google's Gemini API

This script demonstrates more advanced usage of Gemini's image generation capabilities,
including batch generation, styling options, and error handling.

Usage:
  python advanced_image_generator.py --prompt "A cat wearing a space suit on Mars" --style "digital art" --count 3
  python advanced_image_generator.py --batch prompts.txt --output-dir custom_images
"""
import argparse
import base64
import mimetypes
import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("Error: Required packages not installed. Run: pip install -q -U google-genai")
    sys.exit(1)


class GeminiImageGenerator:
    """Class for generating images with Gemini API with advanced options."""
    
    DEFAULT_MODEL = "gemini-2.0-flash-exp-image-generation"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the image generator.
        
        Args:
            api_key: Gemini API key. If None, will try to get from GEMINI_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("No API key provided. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable or pass via constructor.")
        
        self.client = genai.Client(api_key=self.api_key)
    
    def generate_image(
        self, 
        prompt: str, 
        output_name: Optional[str] = None,
        output_dir: Optional[str] = None,
        style: Optional[str] = None,
        negative_prompt: Optional[str] = None,
    ) -> str:
        """
        Generate an image using Gemini model.
        
        Args:
            prompt: Text prompt describing the desired image
            output_name: Filename for output image (without extension)
            output_dir: Directory to save the image (defaults to output/generated_images)
            style: Optional style to apply ("painting", "photo", "digital art", etc.)
            negative_prompt: Optional text describing what to avoid in the image
            
        Returns:
            Path to the generated image file
        """
        # Enhance prompt with style if provided
        full_prompt = prompt
        if style:
            full_prompt = f"{prompt}, {style} style"
        
        # Add negative prompt if provided
        if negative_prompt:
            full_prompt = f"{full_prompt}. Avoid: {negative_prompt}"
        
        # Create content for the model
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=full_prompt),
                ],
            ),
        ]
        
        # Configure response
        generate_content_config = types.GenerateContentConfig(
            response_modalities=["image", "text"],
            response_mime_type="text/plain",
        )

        print(f"Generating image: '{full_prompt}'")
        
        # Set up output directory
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = Path("output/generated_images")
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate default output filename if not provided
        if not output_name:
            sanitized_prompt = prompt.lower().replace(' ', '_')[:30]
            timestamp = int(time.time())
            output_name = f"{sanitized_prompt}_{timestamp}"
        
        # Try to generate with retries for resilience
        for attempt in range(self.MAX_RETRIES):
            try:
                for chunk in self.client.models.generate_content_stream(
                    model=self.DEFAULT_MODEL,
                    contents=contents,
                    config=generate_content_config,
                ):
                    # Skip empty chunks
                    if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
                        continue
                        
                    # Handle different types of response
                    part = chunk.candidates[0].content.parts[0]
                    if part.inline_data:
                        # Save image with appropriate extension
                        inline_data = part.inline_data
                        file_extension = mimetypes.guess_extension(inline_data.mime_type) or ".png"
                        file_path = output_path / f"{output_name}{file_extension}"
                        
                        # Save the file
                        with open(file_path, "wb") as f:
                            f.write(inline_data.data)
                        
                        print(f"✓ Image saved to: {file_path}")
                        return str(file_path)
                    else:
                        # Print any text response
                        if chunk.text:
                            print(f"Model message: {chunk.text}")
                
                # If we got here without returning, no image was generated
                print(f"Warning: No image data in response (attempt {attempt+1}/{self.MAX_RETRIES})")
                
            except Exception as e:
                print(f"Error during generation (attempt {attempt+1}/{self.MAX_RETRIES}): {str(e)}")
                if attempt < self.MAX_RETRIES - 1:
                    print(f"Retrying in {self.RETRY_DELAY} seconds...")
                    time.sleep(self.RETRY_DELAY)
                else:
                    print("Maximum retry attempts reached.")
                    raise
        
        raise RuntimeError("Failed to generate image after multiple attempts")
    
    def batch_generate(
        self, 
        prompts: List[str], 
        output_dir: Optional[str] = None,
        style: Optional[str] = None,
    ) -> List[str]:
        """
        Generate multiple images from a list of prompts.
        
        Args:
            prompts: List of text prompts
            output_dir: Directory to save images
            style: Optional style to apply to all images
            
        Returns:
            List of paths to generated image files
        """
        results = []
        total = len(prompts)
        
        print(f"Starting batch generation of {total} images...")
        
        for idx, prompt in enumerate(prompts, 1):
            print(f"\n[{idx}/{total}] Processing: '{prompt}'")
            try:
                # Use a numbered filename for each prompt in the batch
                output_name = f"batch_{idx:03d}"
                image_path = self.generate_image(
                    prompt=prompt,
                    output_name=output_name,
                    output_dir=output_dir,
                    style=style,
                )
                results.append(image_path)
            except Exception as e:
                print(f"Error generating image for prompt #{idx}: {str(e)}")
                results.append(None)
        
        # Print summary
        success_count = sum(1 for path in results if path is not None)
        print(f"\nBatch generation complete: {success_count}/{total} images successful")
        
        return results


def read_prompts_file(file_path: str) -> List[str]:
    """Read a file containing one prompt per line."""
    with open(file_path, "r") as f:
        return [line.strip() for line in f if line.strip()]


def main():
    """Parse command line arguments and generate images."""
    parser = argparse.ArgumentParser(
        description="Generate images using Google's Gemini image generation API",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--prompt", "-p",
        help="Text prompt describing the image you want to generate"
    )
    input_group.add_argument(
        "--batch", "-b",
        help="Path to a text file with one prompt per line for batch generation"
    )
    
    # Output options
    parser.add_argument(
        "--output", "-o",
        help="Base filename for the output image (without extension)"
    )
    parser.add_argument(
        "--output-dir", "-d",
        help="Directory to save generated images",
        default="output/generated_images"
    )
    
    # Generation options
    parser.add_argument(
        "--style", "-s",
        help="Style to apply (e.g., 'oil painting', 'digital art', 'photo')"
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=1,
        help="Number of variations to generate (single prompt mode only)"
    )
    parser.add_argument(
        "--negative-prompt", "-n",
        help="What to avoid in the generated image"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize the generator
        generator = GeminiImageGenerator()
        
        # Process batch file if provided
        if args.batch:
            prompts = read_prompts_file(args.batch)
            print(f"Read {len(prompts)} prompts from {args.batch}")
            generator.batch_generate(
                prompts=prompts,
                output_dir=args.output_dir,
                style=args.style,
            )
            return
        
        # Otherwise process single prompt, potentially with multiple variations
        if args.count > 1:
            print(f"Generating {args.count} variations for: '{args.prompt}'")
            for i in range(args.count):
                output_name = args.output
                if args.output and args.count > 1:
                    output_name = f"{args.output}_{i+1}"
                
                generator.generate_image(
                    prompt=args.prompt,
                    output_name=output_name,
                    output_dir=args.output_dir,
                    style=args.style,
                    negative_prompt=args.negative_prompt,
                )
        else:
            generator.generate_image(
                prompt=args.prompt,
                output_name=args.output,
                output_dir=args.output_dir,
                style=args.style,
                negative_prompt=args.negative_prompt,
            )
    
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
