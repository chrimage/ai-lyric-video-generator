"""
AI Image Generator - Creates images for lyric video using AI APIs
"""
import os
import time
import random
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

from ai_generator.config import (
    GEMINI_API_KEY, AVAILABLE_API, IMAGE_GENERATION_MODEL, 
    DEFAULT_IMAGE_WIDTH, DEFAULT_IMAGE_HEIGHT, client
)
from ai_generator.prompts import (
    IMAGE_DESCRIPTION_PROMPT, IMAGE_GENERATION_PROMPT
)
from ai_generator.utils import retry_api_call, format_text_display, logger
from lyrics_segmenter import LyricsTimeline, LyricsSegment

try:
    from google.genai import types
except ImportError:
    types = None


class AIImageGenerator:
    """Generates images for each segment of the lyrics timeline"""
    
    def __init__(self, output_dir="generated_images", api_key=None):
        self.output_dir = output_dir
        self.api_key = api_key or GEMINI_API_KEY
        self.api = AVAILABLE_API
        
        # Initialize client if different API key is provided
        if api_key and api_key != GEMINI_API_KEY and types:
            import google.genai as genai
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = client
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_image_descriptions(self, timeline: LyricsTimeline) -> LyricsTimeline:
        """Generate image descriptions for each segment based on the video concept"""
        if not timeline.video_concept:
            raise ValueError("Timeline must have a video concept before generating image descriptions")
        
        song_title = timeline.song_info['title']
        artists = ', '.join(timeline.song_info['artists'])
        
        # Format segments for prompt
        segments_text = []
        for i, segment in enumerate(timeline.segments):
            segments_text.append(f"{i+1}. [{segment.segment_type}] {segment.text}")
        
        segments_formatted = "\n".join(segments_text)
        
        # Prepare prompt
        prompt = IMAGE_DESCRIPTION_PROMPT.format(
            song_title=song_title, 
            artists=artists,
            video_concept=timeline.video_concept,
            segments_text=segments_formatted
        )
        
        # Generate descriptions
        if self.api == "gemini" and self.api_key and self.client:
            descriptions = self._generate_descriptions_with_gemini(prompt)
        else:
            descriptions = self._generate_mock_descriptions(timeline.segments)
        
        # Update timeline with descriptions
        for i, desc in enumerate(descriptions):
            if i < len(timeline.segments):
                timeline.segments[i].image_description = desc
        
        # Ensure all segments have descriptions (use defaults for any missing)
        for i, segment in enumerate(timeline.segments):
            if not segment.image_description:
                segment.image_description = f"A visual representation of '{segment.text}' for a music video."
        
        return timeline
    
    def _generate_descriptions_with_gemini(self, prompt: str) -> List[str]:
        """Generate image descriptions using Gemini API"""
        print("\n--- Generating image descriptions with Gemini ---")
        
        def generate_descriptions():
            response = self.client.models.generate_content(
                model="models/gemini-2.0-flash",
                contents=prompt
            )
            
            if response.candidates and response.candidates[0].content.parts:
                return self._parse_numbered_response(response.candidates[0].content.parts[0].text)
            return []
        
        try:
            return retry_api_call(generate_descriptions)
        except Exception as e:
            print(f"Error generating descriptions: {e}")
            return []
    
    def _generate_mock_descriptions(self, segments: List[LyricsSegment]) -> List[str]:
        """Generate mock descriptions when API not available"""
        print("\n--- Generating mock image descriptions ---")
        
        descriptions = []
        color_schemes = [
            ["blue", "cyan", "purple"], 
            ["red", "orange", "gold"],
            ["green", "teal", "emerald"]
        ]
        color_palette = random.choice(color_schemes)
        
        for i, segment in enumerate(segments):
            colors = f"{color_palette[i % len(color_palette)]} and {color_palette[(i+1) % len(color_palette)]}"
            
            if segment.segment_type == "lyrics":
                descriptions.append(
                    f"A visual scene with '{segment.text}' as the central focus. "
                    f"The text appears stylized with {colors} tones and artistic lighting."
                )
            else:
                descriptions.append(
                    f"An instrumental visual scene with atmospheric {colors} lighting and "
                    f"geometric elements creating visual interest throughout the composition."
                )
                
        return descriptions
        
    def _parse_numbered_response(self, response_text: str) -> List[str]:
        """Parse a numbered list response from the AI"""
        import re
        
        lines = response_text.strip().split('\n')
        descriptions = []
        
        current_description = ""
        current_number = None
        
        for line in lines:
            # Check if line starts a new numbered item
            match = re.match(r'^\s*(\d+)\.\s*(.*)', line)
            
            if match:
                # If we were already building a description, save it
                if current_number is not None and current_description:
                    descriptions.append(current_description.strip())
                
                # Start a new description
                current_number = int(match.group(1))
                current_description = match.group(2)
            else:
                # Continue building current description if we have one
                if current_number is not None:
                    current_description += " " + line.strip()
        
        # Add the last description if there is one
        if current_number is not None and current_description:
            descriptions.append(current_description.strip())
        
        return descriptions
    
    def generate_images(self, timeline: LyricsTimeline) -> LyricsTimeline:
        """Generate images for each segment based on descriptions"""
        print("\n--- Generating images for lyrics segments ---")
        
        # Process each segment
        for i, segment in enumerate(timeline.segments):
            # Generate filename and path
            safe_text = segment.text[:20].replace(' ', '_').replace('/', '_')
            filename = f"{i:03d}_{safe_text}.png"
            filepath = os.path.join(self.output_dir, filename)
            
            print(f"\nSegment {i+1}/{len(timeline.segments)}: {segment.text[:30]}...")
            
            # Check if image already exists
            if os.path.exists(filepath):
                print(f"Image already exists: {filepath}")
                segment.image_path = filepath
                continue
            
            # Show description
            print(f"Description: {segment.image_description[:100]}...")
            
            # Generate image
            try:
                if self.api == "gemini" and self.api_key and self.client:
                    success = self._generate_image_with_gemini(segment.image_description, filepath)
                else:
                    success = self._generate_mock_image(segment.image_description, filepath, segment.text, segment.segment_type)
                
                if success:
                    segment.image_path = filepath
                    print(f"Image generated: {filepath}")
                else:
                    # If API generation fails, fall back to mock image
                    print("Falling back to text-only image")
                    success = self._generate_mock_image(segment.image_description, filepath, segment.text, segment.segment_type)
                    if success:
                        segment.image_path = filepath
                
            except Exception as e:
                print(f"Error generating image: {e}")
                # Try mock image as fallback
                success = self._generate_mock_image(segment.image_description, filepath, segment.text, segment.segment_type)
                if success:
                    segment.image_path = filepath
            
            # Add small delay between generations
            time.sleep(1.0)
            
        return timeline
    
    def _generate_image_with_gemini(self, description: str, filepath: str) -> bool:
        """Generate image using Gemini API"""
        # Format the prompt with the description
        prompt = IMAGE_GENERATION_PROMPT.format(description=description)
        
        def generate_image():
            # Use the dedicated image generation model
            response = self.client.models.generate_content(
                model=IMAGE_GENERATION_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=['Image', 'Text'],
                    temperature=0.4
                )
            )
            
            # Process response
            if not response.candidates or not response.candidates[0].content.parts:
                return False
            
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    # Save the image data
                    with open(filepath, 'wb') as f:
                        f.write(part.inline_data.data)
                    return True
            
            return False
        
        try:
            return retry_api_call(generate_image)
        except Exception as e:
            print(f"API Image generation error: {e}")
            return False
    
    def _generate_mock_image(self, description: str, filepath: str, text: Optional[str] = None, segment_type: Optional[str] = None) -> bool:
        """Generate a simple text-only image as fallback"""
        try:
            # Create a black image
            img = Image.new('RGB', (DEFAULT_IMAGE_WIDTH, DEFAULT_IMAGE_HEIGHT), (0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Determine display text
            if segment_type == "instrumental" or not text:
                display_text = "♪" if not description else description[:100] + "..."
            else:
                display_text = text
            
            # Try to load a font
            try:
                font = ImageFont.truetype("Arial.ttf", 36)
            except:
                font = ImageFont.load_default()
            
            # Draw text centered
            text_width, text_height = draw.textsize(display_text, font=font) if hasattr(draw, 'textsize') else (font.getmask(display_text).getbbox()[2], font.getmask(display_text).getbbox()[3])
            position = ((DEFAULT_IMAGE_WIDTH - text_width) / 2, (DEFAULT_IMAGE_HEIGHT - text_height) / 2)
            
            # Draw outline
            for dx, dy in [(-2,-2), (-2,2), (2,-2), (2,2)]:
                draw.text((position[0]+dx, position[1]+dy), display_text, fill=(0, 0, 0), font=font)
            
            # Draw text
            draw.text(position, display_text, fill=(255, 255, 255), font=font)
            
            # Save image
            img.save(filepath)
            return True
            
        except Exception as e:
            print(f"Mock image generation error: {e}")
            return False
