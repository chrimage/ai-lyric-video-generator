#!/usr/bin/env python3
"""
AI Image Generator - Creates images for lyric video using AI APIs
"""
import os
import json
import time
import math
import random
import textwrap
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageColor
from io import BytesIO

from lyrics_segmenter import LyricsTimeline, LyricsSegment

# Load environment variables
load_dotenv()

# Check which image generation API is available
AVAILABLE_API = "mock"  # Options: mock, gemini, dall-e, stability

# The specific model that supports image generation
IMAGE_GENERATION_MODEL = "models/gemini-2.0-flash-exp-image-generation"
THINKING_MODEL = "models/gemini-2.0-flash-thinking-exp"

try:
    import google.genai as genai
    from google.genai import types
    
    # Get API key from environment variable
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY:
        # Initialize the Gemini client
        client = genai.Client(api_key=GEMINI_API_KEY)
        AVAILABLE_API = "gemini"
        print("Gemini API available")
    else:
        client = None
        print("Gemini API key not found in environment variables")
except ImportError:
    client = None
    print("Gemini API not available - using mock generation")


# Import the API utilities 
from api_utils import api_call_with_backoff, logger

def retry_api_call(func, *args, **kwargs):
    """Wrapper to use the improved api_call_with_backoff function"""
    return api_call_with_backoff(func, *args, max_retries=8, initial_delay=2.0, max_delay=120.0, **kwargs)


class VideoCreativeDirector:
    """Generates a creative direction for the lyric video"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or GEMINI_API_KEY
        self.api = AVAILABLE_API
        
        # Initialize client if different API key is provided
        if api_key and api_key != GEMINI_API_KEY:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = client
    
    def thinking_generate(self, prompt):
        """Generate content using a thinking model"""
        if self.client is None:
            return "Error: No client available"
        
        # Use the thinking model with retries
        def generate_with_thinking():
            response = self.client.models.generate_content(
                model=THINKING_MODEL,
                contents=prompt,
                # Add thinking configuration if supported by the model
                config=types.GenerateContentConfig(
                    temperature=0.2  # Lower temperature for more focused thinking
                )
            )
            
            if response.candidates and response.candidates[0].content.parts:
                return response.candidates[0].content.parts[0].text
            return "Error generating concept with thinking model"
        
        try:
            return retry_api_call(generate_with_thinking)
        except Exception as e:
            print(f"Error with thinking model: {e}")
            # Fall back to standard model
            try:
                def generate_with_standard():
                    response = self.client.models.generate_content(
                        model="models/gemini-2.0-flash",  # Fall back to standard flash model
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.2
                        )
                    )
                    if response.candidates and response.candidates[0].content.parts:
                        return response.candidates[0].content.parts[0].text
                    return "Error generating concept with standard model"
                
                return retry_api_call(generate_with_standard)
            except Exception as e2:
                print(f"Error with fallback model: {e2}")
            return "Error generating concept"
    
    def generate_video_concept(self, timeline: LyricsTimeline) -> str:
        """Generate a creative concept for the entire video"""
        song_title = timeline.song_info['title']
        artists = ', '.join(timeline.song_info['artists'])
        
        # Extract all lyrics text from segments
        lyrics = []
        for segment in timeline.segments:
            if segment.segment_type == "lyrics":
                lyrics.append(segment.text)
        
        full_lyrics = "\n".join(lyrics)
        
        if self.api == "gemini" and self.api_key:
            return self._generate_concept_with_gemini(song_title, artists, full_lyrics)
        else:
            return self._generate_mock_concept(song_title, artists)
    
    def _generate_concept_with_gemini(self, song_title, artists, full_lyrics):
        """Generate video concept using Gemini API with thinking model"""
        prompt = f"""
        You are designing a lyric video for the song "{song_title}" by "{artists}". 
        Here are the complete lyrics:
        
        {full_lyrics}
        
        Create a cohesive visual concept for a lyric video with these constraints:
        1. The video will consist of still images that change with the lyrics
        2. No camera movements can be depicted (only static scenes)
        3. Any action must be represented in a single frame
        4. Choose a consistent visual style, color palette, and thematic elements
        5. Consider the song's mood, message, and cultural context
        
        Think deeply about the song's meaning, themes, and emotional tone.
        Describe your overall concept for the video in 3-5 paragraphs.
        """
        
        return self.thinking_generate(prompt)
    
    def _generate_mock_concept(self, song_title, artists):
        """Generate a mock concept for testing"""
        concepts = [
            f"A neon-lit urban landscape for {song_title} by {artists}. Vibrant purple and blue hues dominate the visuals, with each scene featuring stylized city elements like skyscrapers, street lights, and reflective surfaces. The lyrics appear as glowing neon signs integrated into the urban environment.",
            
            f"A minimalist, paper-cut art style for {song_title} by {artists}. Each scene uses a limited palette of pastel colors with white space. Elements appear as carefully arranged paper cutouts with subtle shadows. Lyrics are handwritten in a flowing calligraphy that complements the delicate visual style.",
            
            f"A retro 80s synthwave aesthetic for {song_title} by {artists}. Sunset gradients of pink, purple and orange create the backdrop for grid-lined horizons and geometric shapes. Chrome text with glowing outlines presents the lyrics, while vintage computer graphics and wireframe objects populate each scene."
        ]
        return random.choice(concepts)
    

class AIImageGenerator:
    """Generates images for each segment of the lyrics timeline"""
    
    def __init__(self, output_dir="generated_images", api_key=None):
        self.output_dir = output_dir
        self.api_key = api_key or GEMINI_API_KEY
        self.api = AVAILABLE_API
        
        # Initialize client if different API key is provided
        if api_key and api_key != GEMINI_API_KEY:
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
        
        if self.api == "gemini" and self.api_key and self.client:
            descriptions = self._generate_descriptions_with_gemini(
                song_title, artists, timeline.video_concept, segments_formatted
            )
        else:
            descriptions = self._generate_mock_descriptions(timeline.segments)
        
        # Update timeline with descriptions
        if len(descriptions) == len(timeline.segments):
            for i, desc in enumerate(descriptions):
                timeline.segments[i].image_description = desc
        else:
            print(f"Warning: Generated {len(descriptions)} descriptions for {len(timeline.segments)} segments")
            logger.warning(f"Generated {len(descriptions)} descriptions for {len(timeline.segments)} segments")
            
            # First, assign the available descriptions
            for i, desc in enumerate(descriptions):
                if i < len(timeline.segments):
                    timeline.segments[i].image_description = desc
            
            # Then generate contextual fallback descriptions for any missing ones
            missing_count = 0
            
            # Extract visual style from existing descriptions if available
            visual_style_info = self._extract_visual_style(timeline)
            
            for i, segment in enumerate(timeline.segments):
                if not segment.image_description:
                    missing_count += 1
                    
                    # Get context from surrounding segments for continuity
                    prev_segment = timeline.segments[i-1] if i > 0 else None
                    next_segment = timeline.segments[i+1] if i < len(timeline.segments)-1 else None
                    
                    # Generate a contextual fallback description
                    fallback_desc = self._generate_contextual_fallback(
                        segment, i, prev_segment, next_segment, visual_style_info, timeline.video_concept
                    )
                    
                    segment.image_description = fallback_desc
                    print(f"Created contextual fallback description for segment {i+1}: {segment.text[:30]}...")
                    logger.info(f"Created contextual fallback description for segment {i+1}: {segment.text[:30]}...")
            
            if missing_count > 0:
                print(f"Created {missing_count} fallback descriptions to ensure all segments have descriptions")
                logger.info(f"Created {missing_count} fallback descriptions to ensure all segments have descriptions")
        
        # Double-check to make sure ALL segments have descriptions
        for i, segment in enumerate(timeline.segments):
            if not segment.image_description:
                print(f"ERROR: Segment {i+1} still missing description after fallback - adding emergency description")
                logger.error(f"Segment {i+1} still missing description after fallback - adding emergency description")
                segment.image_description = f"A visual representation of the song. {segment.text if segment.text else 'Musical interlude'}."
        
        return timeline
    
    def _generate_descriptions_with_gemini(self, song_title, artists, video_concept, segments_text):
        """Generate image descriptions using Gemini API with pro model"""
        prompt = f"""
        You are creating still images for a lyric video for "{song_title}" by "{artists}".
        The overall concept for this video is:
        
        {video_concept}
        
        IMPORTANT GUIDELINES FOR VISUAL CONTINUITY:
        1. This is a sequence of images shown in chronological order, telling a visual story
        2. Create a clear visual progression and continuity between all images
        3. Maintain consistent visual style, color palette, and motifs throughout
        4. For instrumental segments (no lyrics), create transitional scenes that connect the narrative
        5. Each image should make sense in relation to what came before and after it
        
        Below is a numbered list of segments from the song. Create an image description for each numbered segment.
        
        SEGMENTS:
        {segments_text}
        
        For each segment, provide ONLY the image description as a numbered list matching the segment numbers above.
        
        IMPORTANT INSTRUCTIONS:
        - For segments with lyrics, the text MUST be visually incorporated into the scene in a creative way
        - For instrumental segments, design images that maintain narrative flow and build anticipation
        - Create a cohesive visual journey where each image builds upon the previous ones
        - Ensure visual elements and themes evolve gradually, not abruptly
        - Each image should be a self-contained scene while maintaining the overall visual narrative
        
        HANDLING SENSITIVE LYRICS:
        - When dealing with provocative, violent, explicit, or adult-themed lyrics, use sophisticated artistic techniques:
          * Use metaphors and symbolism to convey the emotional impact rather than literal depictions
          * Employ abstract visual representations that capture the feeling without explicit content
          * Use silhouettes, shadows, artistic lighting, and creative framing
          * Focus on the broader themes, emotions, and artistic meaning behind the lyrics
          * Transform potentially problematic concepts into visually poetic, artistic interpretations
          * Consider visual allegories, surrealism, or stylized representations that preserve artistic intent
        - STRICTLY AVOID:
          * Any gore, blood, wounds, or physical injuries
          * Macabre or morbid imagery like graveyards, coffins, dead bodies
          * Disturbing, frightening, or excessively dark imagery
          * Weapons shown in threatening contexts
          * Anything that depicts suffering or pain
        - Instead, for dark themes:
          * Use symbolic representations like withered flowers instead of death imagery
          * Employ abstract color schemes (dark blues/purples) to convey mood
          * Use weather elements (storms, lightning) to represent conflict or tension
          * Incorporate symbolic objects (broken glass, chains breaking) instead of explicit violence
        - Remember that artistic expression can be powerful without being explicit
        - Think like a creative director for a music video that needs to air on television
        
        Your response should be formatted EXACTLY like this:
        1. [Detailed image description for segment 1]
        2. [Detailed image description for segment 2]
        ...
        """
        
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
    
    def _generate_mock_descriptions(self, segments):
        """Generate mock descriptions for testing with continuity between scenes"""
        descriptions = []
        
        # Define consistent visual elements for the entire video
        visual_elements = [
            "floating particles", "light rays", "silhouettes", "reflective surfaces",
            "geometric patterns", "translucent layers", "depth of field effects", 
            "textured backgrounds", "color gradients", "atmospheric lighting"
        ]
        
        # Choose a consistent color palette
        color_schemes = [
            ["deep blue", "royal blue", "cyan", "white"],
            ["purple", "magenta", "pink", "lavender"],
            ["forest green", "emerald", "mint", "seafoam"],
            ["crimson", "scarlet", "orange", "gold"],
            ["midnight blue", "indigo", "violet", "periwinkle"]
        ]
        color_palette = random.choice(color_schemes)
        
        # Select recurring motifs
        motifs = [
            "nature elements", "urban landscape", "abstract shapes", "cosmic imagery",
            "water reflections", "architectural elements", "technological elements"
        ]
        recurring_motifs = random.sample(motifs, 2)  # Choose 2 recurring motifs
        
        # Base scene description that ties everything together
        base_scene = f"A visually striking scene in a consistent style using {color_palette[0]} and {color_palette[1]} " \
                     f"as primary colors, with elements of {recurring_motifs[0]} and {recurring_motifs[1]} recurring throughout."
        
        # Generate descriptions with continuity in mind
        for i, segment in enumerate(segments):
            prev_segment_type = segments[i-1].segment_type if i > 0 else None
            next_segment_type = segments[i+1].segment_type if i < len(segments)-1 else None
            
            # Choose visual elements that evolve through the video
            visual_element1 = visual_elements[i % len(visual_elements)]
            visual_element2 = visual_elements[(i + 3) % len(visual_elements)]
            
            # Gradually shift through the color palette
            primary_color = color_palette[i % len(color_palette)]
            secondary_color = color_palette[(i + 1) % len(color_palette)]
            
            if segment.segment_type == "lyrics":
                # For lyrics, create a description that incorporates the text and maintains continuity
                if prev_segment_type == "instrumental":
                    # Transitioning from instrumental to lyrics
                    descriptions.append(
                        f"{base_scene} The scene evolves from the previous instrumental moment, as '{segment.text}' appears "
                        f"integrated into the composition. {visual_element1} and {visual_element2} frame the text, "
                        f"with {primary_color} highlights emphasizing emotional resonance. The lyric text flows naturally "
                        f"within the scene, appearing as if it belongs to this visual world."
                    )
                else:
                    # Continuing lyrics or starting with lyrics
                    descriptions.append(
                        f"{base_scene} A composition featuring '{segment.text}' as an integral visual element. "
                        f"The scene uses {visual_element1} and subtle {primary_color} to {secondary_color} gradients "
                        f"to reflect the emotional tone of these lyrics. The text appears as {random.choice(['illuminated', 'embossed', 'floating', 'integrated'])} "
                        f"elements within the composition, maintaining visual flow from the previous scene."
                    )
            else:
                # For instrumental segments
                if "Intro" in segment.text:
                    descriptions.append(
                        f"{base_scene} An establishing shot that introduces the visual theme of the video. "
                        f"{visual_element1} emerge from darkness, gradually revealing the {recurring_motifs[0]} motif "
                        f"that will recur throughout the video. {primary_color} and {secondary_color} tones "
                        f"blend to create depth and atmosphere as the music begins, setting the visual tone for what follows."
                    )
                elif "Outro" in segment.text:
                    descriptions.append(
                        f"{base_scene} A concluding image that brings closure to the visual narrative. "
                        f"Elements from throughout the video—{recurring_motifs[0]}, {recurring_motifs[1]}, and {visual_element1}—"
                        f"converge in a harmonious composition. {primary_color} light gradually fades, "
                        f"creating a sense of resolution and completion to the visual journey."
                    )
                else:  # Instrumental Break
                    if prev_segment_type == "lyrics" and next_segment_type == "lyrics":
                        # Bridge between lyric segments
                        descriptions.append(
                            f"{base_scene} A transitional scene that bridges the narrative between lyrics. "
                            f"The {visual_element1} from the previous scene transform and flow toward what comes next. "
                            f"{primary_color} and {secondary_color} create visual rhythm, maintaining the established "
                            f"atmosphere while building anticipation for the next lyrical moment."
                        )
                    else:
                        # Standalone instrumental section
                        descriptions.append(
                            f"{base_scene} An atmospheric instrumental moment with dynamic visual energy. "
                            f"{visual_element1} and {visual_element2} create subtle movement across the composition, "
                            f"with {primary_color} accents punctuating the {recurring_motifs[0]} motif. "
                            f"The scene evolves visually in harmony with the music, maintaining the emotional tone."
                        )
        
        return descriptions
    
    def _extract_visual_style(self, timeline):
        """Extract visual style information from existing descriptions"""
        # Initialize visual style information
        visual_style = {
            'colors': set(),
            'elements': set(),
            'motifs': set(),
            'techniques': set()
        }
        
        # Common visual elements to look for
        color_keywords = ["blue", "red", "green", "purple", "yellow", "orange", "pink", "teal", 
                          "cyan", "magenta", "gold", "silver", "black", "white", "gray", "brown"]
        
        element_keywords = ["light", "shadow", "silhouette", "gradient", "particle", "ray", 
                           "geometric", "pattern", "texture", "layer", "blur", "focus"]
        
        motif_keywords = ["nature", "urban", "cosmic", "water", "fire", "earth", "air", 
                         "abstract", "landscape", "architecture", "technology"]
        
        technique_keywords = ["depth of field", "bokeh", "contrast", "saturation", "minimalist", 
                             "detailed", "surreal", "realistic", "stylized", "glowing"]
        
        # Extract information from existing descriptions
        for segment in timeline.segments:
            if segment.image_description:
                desc = segment.image_description.lower()
                
                # Extract colors
                for color in color_keywords:
                    if color in desc:
                        visual_style['colors'].add(color)
                
                # Extract elements
                for element in element_keywords:
                    if element in desc:
                        visual_style['elements'].add(element)
                
                # Extract motifs
                for motif in motif_keywords:
                    if motif in desc:
                        visual_style['motifs'].add(motif)
                
                # Extract techniques
                for technique in technique_keywords:
                    if technique in desc:
                        visual_style['techniques'].add(technique)
        
        # If we have a video concept, extract from there too
        if timeline.video_concept:
            concept = timeline.video_concept.lower()
            for color in color_keywords:
                if color in concept:
                    visual_style['colors'].add(color)
            for element in element_keywords:
                if element in concept:
                    visual_style['elements'].add(element)
            for motif in motif_keywords:
                if motif in concept:
                    visual_style['motifs'].add(motif)
            for technique in technique_keywords:
                if technique in concept:
                    visual_style['techniques'].add(technique)
        
        # Default values if nothing was extracted
        if not visual_style['colors']:
            visual_style['colors'] = {"blue", "purple", "cyan"}
        if not visual_style['elements']:
            visual_style['elements'] = {"light", "shadow", "geometric"}
        if not visual_style['motifs']:
            visual_style['motifs'] = {"abstract"}
        if not visual_style['techniques']:
            visual_style['techniques'] = {"depth of field"}
        
        return visual_style
    
    def _generate_contextual_fallback(self, segment, index, prev_segment, next_segment, visual_style, video_concept):
        """Generate a contextual fallback description based on surrounding segments"""
        # Extract style information
        colors = list(visual_style['colors'])
        elements = list(visual_style['elements'])
        motifs = list(visual_style['motifs'])
        techniques = list(visual_style['techniques'])
        
        # Choose elements to maintain continuity
        color1 = random.choice(colors)
        color2 = random.choice([c for c in colors if c != color1]) if len(colors) > 1 else color1
        element1 = random.choice(elements)
        element2 = random.choice([e for e in elements if e != element1]) if len(elements) > 1 else element1
        motif = random.choice(motifs)
        technique = random.choice(techniques)
        
        # Create base description with consistent style
        base_desc = f"A visually cohesive scene using {color1} and {color2} tones, with {element1} and {element2} elements, "
        base_desc += f"incorporating {motif} motifs and {technique} technique to maintain the established visual style. "
        
        # Add contextual elements based on segment position and type
        if segment.segment_type == "lyrics":
            # For lyrics segments
            lyrics_text = segment.text
            
            # Check if we have context from surrounding segments
            if prev_segment and prev_segment.image_description:
                # Transitioning from previous segment
                if prev_segment.segment_type == "instrumental":
                    # Transitioning from instrumental to lyrics
                    return f"{base_desc}The scene transitions from the previous instrumental moment, as '{lyrics_text}' becomes the visual focus. The text appears integrated within the composition, maintaining visual continuity while emphasizing this new lyrical element. The {color1} tones intensify to highlight the emotional shift as lyrics begin."
                else:
                    # Transitioning from lyrics to lyrics
                    return f"{base_desc}Building on the previous lyrical scene, this image features '{lyrics_text}' as its focal point. The {element1} elements evolve from the previous scene, showing progression while maintaining the established visual language. The text appears as a natural continuation of the visual narrative."
            
            if next_segment and next_segment.image_description:
                # Consider what comes next
                if next_segment.segment_type == "instrumental":
                    # Transitioning to instrumental
                    return f"{base_desc}A lyrical scene featuring '{lyrics_text}' prominently, while subtly preparing for the instrumental section that follows. The {motif} imagery begins to expand beyond the text, with {color1} and {color2} tones creating visual harmony. The composition balances the current lyrics with hints of what's coming next."
            
            # Generic lyrics description with style consistency
            return f"{base_desc}A powerful visual representation of '{lyrics_text}', with the text integrated as a key element in the composition. The scene captures the emotional essence of these words, using {color1} highlights to emphasize key aspects. The {motif} imagery reinforces the meaning behind these lyrics."
        
        else:
            # For instrumental segments
            segment_type = segment.text.lower()
            
            if "intro" in segment_type:
                # Intro segment
                return f"{base_desc}An establishing shot that introduces the visual world of the video. {color1.capitalize()} and {color2} tones emerge gradually, revealing the {motif} motifs that will recur throughout the video. The {element1} elements begin to take form, establishing the visual language that will evolve as the song progresses."
            
            elif "outro" in segment_type:
                # Outro segment
                return f"{base_desc}A concluding scene that brings visual closure to the narrative. Elements seen throughout the video—the {motif} imagery, {element1} and {element2} elements—converge in a final composition. The {color1} tones gradually transition toward {color2}, creating a sense of resolution and completion."
            
            else:
                # Instrumental break/bridge
                if prev_segment and next_segment:
                    if prev_segment.segment_type == "lyrics" and next_segment.segment_type == "lyrics":
                        # Bridge between lyrics
                        return f"{base_desc}A transitional scene that bridges between lyrical moments. The visuals maintain the {motif} imagery established earlier while using {element1} elements to create a sense of movement and progression. {color1.capitalize()} tones shift subtly toward {color2}, building anticipation for the return of lyrics while preserving narrative continuity."
                
                # Generic instrumental description
                return f"{base_desc}An atmospheric instrumental scene that maintains the visual flow of the video. The {element1} and {element2} elements create subtle visual interest without overpowering the established style. {color1.capitalize()} accents punctuate the {motif} imagery, maintaining emotional resonance with the music."
    
    def _parse_numbered_response(self, response_text):
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
        """Generate actual images for each segment based on descriptions with batch processing"""
        # Check for missing descriptions and warn rather than fail
        missing_desc_count = sum(1 for segment in timeline.segments if not segment.image_description)
        if missing_desc_count > 0:
            logger.warning(f"Found {missing_desc_count} segments without descriptions. Adding emergency descriptions.")
            print(f"Warning: Found {missing_desc_count} segments without descriptions. Adding emergency descriptions.")
            
            # Add emergency descriptions for any missing ones
            for i, segment in enumerate(timeline.segments):
                if not segment.image_description:
                    segment.image_description = f"A visual representation of '{segment.text}' for a music video scene."
                    logger.info(f"Added emergency description for segment {i+1}")
        
        # Batch processing settings
        batch_size = 5  # Process 5 images at a time
        batch_delay = random.uniform(3.0, 5.0)  # Delay between batches
        total_segments = len(timeline.segments)
        
        logger.info(f"Generating {total_segments} images using batch processing")
        print(f"Generating {total_segments} images using batch processing")
        
        # Process images in batches to avoid rate limits
        for batch_start in range(0, total_segments, batch_size):
            batch_end = min(batch_start + batch_size, total_segments)
            logger.info(f"Processing image batch {batch_start+1}-{batch_end} of {total_segments}")
            print(f"Processing image batch {batch_start+1}-{batch_end} of {total_segments}")
            
            for i in range(batch_start, batch_end):
                segment = timeline.segments[i]
                
                # Generate a filename
                safe_text = segment.text[:20].replace(' ', '_').replace('/', '_')
                filename = f"{i:03d}_{safe_text}.png"
                filepath = os.path.join(self.output_dir, filename)
                
                # Check if the image already exists
                if os.path.exists(filepath):
                    logger.info(f"Image already exists: {filename}")
                    print(f"Image already exists: {filename}")
                    segment.image_path = filepath
                    continue
                
                # Generate the image
                success = False
                try:
                    if self.api == "gemini" and self.api_key and self.client:
                        success = self._generate_image_with_gemini(segment.image_description, filepath)
                    else:
                        success = self._generate_mock_image(segment.image_description, filepath, segment.text, segment.segment_type)
                except Exception as e:
                    logger.error(f"Error generating image for segment {i+1}: {e}")
                    print(f"Error generating image for segment {i+1}: {e}")
                    success = False
                
                # If API generation failed, fall back to mock image
                if not success and self.api == "gemini":
                    logger.warning(f"Falling back to mock image for segment {i+1}")
                    print(f"Falling back to mock image for segment {i+1}")
                    success = self._generate_mock_image(segment.image_description, filepath, segment.text, segment.segment_type)
                
                if success:
                    segment.image_path = filepath
                
                # Add a small delay between images within a batch
                if i < batch_end - 1:  # Skip delay after the last image in a batch
                    time.sleep(random.uniform(0.5, 1.5))
            
            # Add a longer delay between batches
            if batch_end < total_segments:
                logger.info(f"Batch complete. Waiting {batch_delay:.1f}s before next batch...")
                print(f"Batch complete. Waiting {batch_delay:.1f}s before next batch...")
                time.sleep(batch_delay)
        
        # Verify all images were created and retry any missing ones
        missing_images = []
        for i, segment in enumerate(timeline.segments):
            if not segment.image_path or not os.path.exists(segment.image_path):
                missing_images.append((i, segment))
        
        # Retry generating missing images
        if missing_images:
            logger.warning(f"Found {len(missing_images)} missing images. Attempting to regenerate...")
            print(f"\nFound {len(missing_images)} missing images. Attempting to regenerate...")
            
            # Add a delay before retries
            time.sleep(3.0)
            
            for i, segment in missing_images:
                logger.info(f"Regenerating missing image {i+1}/{total_segments}")
                print(f"Regenerating missing image {i+1}/{total_segments}")
                
                safe_text = segment.text[:20].replace(' ', '_').replace('/', '_')
                filename = f"{i:03d}_{safe_text}.png"
                filepath = os.path.join(self.output_dir, filename)
                
                # Try again with a more abstract description
                abstract_description = f"A visual representation of '{segment.text}' in the style of the music video."
                
                success = False
                try:
                    if self.api == "gemini" and self.api_key and self.client:
                        success = self._generate_image_with_gemini(abstract_description, filepath)
                    else:
                        success = self._generate_mock_image(abstract_description, filepath, segment.text, segment.segment_type)
                except Exception as e:
                    logger.error(f"Error regenerating image for segment {i+1}: {e}")
                    print(f"Error regenerating image for segment {i+1}: {e}")
                    success = False
                
                # Always fall back to mock image if still failing
                if not success:
                    logger.warning(f"Using fallback mock image for segment {i+1}")
                    print(f"Using fallback mock image for segment {i+1}")
                    success = self._generate_mock_image(abstract_description, filepath, segment.text, segment.segment_type)
                
                if success:
                    segment.image_path = filepath
                
                # Add a delay between retries
                time.sleep(random.uniform(2.0, 3.0))
        
        return timeline
    
    def _generate_image_with_gemini(self, description, filepath):
        """Generate image using Gemini API with the flash-exp model"""
        prompt = f"""
        Create a high-quality still image for a lyric video with the following description:
        
        {description}
        
        The image should:
        - Be in 16:9 aspect ratio (1280x720 or similar)
        - Have high contrast and readability for any text elements
        - Be visually striking and suitable for a music video
        - No humans or faces should be included
        
        ARTISTIC GUIDANCE FOR SENSITIVE CONTENT:
        If the description contains provocative, violent, explicit, or adult-themed references:
        - Use abstract artistic interpretations rather than literal depictions
        - Employ metaphors, symbolism, and visual poetry to convey emotional impact
        - Focus on mood, atmosphere, and artistic expression rather than explicit content
        - Use creative techniques like silhouettes, shadows, artistic lighting
        - Transform potentially problematic elements into artistic visual metaphors
        - Think in terms of award-winning music video aesthetics that convey meaning through artistic expression
        - Find the deeper emotional theme and express it through color, composition, and symbolic imagery
        
        STRICTLY AVOID creating images with:
        - Any gore, blood, wounds, physical injuries or bodily harm
        - Macabre or morbid imagery (graveyards, coffins, dead bodies, skulls)
        - Disturbing, frightening, horror-themed or excessively dark visuals
        - Weapons shown in threatening or violent contexts
        - Imagery depicting suffering, torture, or physical/emotional pain
        
        For dark or intense themes, instead use:
        - Symbolic imagery (withered flowers, broken objects, stormy skies)
        - Abstract color schemes and lighting to convey emotional tone
        - Natural elements (weather, landscapes) to represent emotional states
        - Visual symbolism that suggests themes without explicit depiction
        - Artistic stylization that transforms literal content into abstract concepts
        """
        
        def generate_image():
            # Use the dedicated image generation model
            try:
                response = self.client.models.generate_content(
                    model=IMAGE_GENERATION_MODEL,  # Use the specific image generation model
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=['Image', 'Text'],  # Request image first, text second
                        temperature=0.4,  # Slightly lower temperature for more predictable results
                        max_output_tokens=4096  # Ensure enough tokens for image generation
                    )
                )
                
                # Process and save the image
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            # Save the image data
                            with open(filepath, 'wb') as f:
                                f.write(part.inline_data.data)
                            print(f"Image saved to {filepath}")
                            return True
                        elif hasattr(part, 'text') and part.text:
                            print(f"Image generation message: {part.text[:100]}...")
                
                print("No image was generated in the response")
                return False
            except Exception as e:
                # Log the exception but allow retry_api_call to handle it
                print(f"Exception in generate_image: {type(e).__name__}: {str(e)[:100]}...")
                raise  # Re-raise for retry_api_call to handle
        
        # First try with flash-exp model
        try:
            success = retry_api_call(generate_image)
            if success:
                return True
            
            # If the flash-exp model fails, try the standard flash model
            print("Falling back to standard flash model...")
            def generate_image_with_flash():
                # Create a more sophisticated fallback prompt with artistic guidance
                fallback_prompt = f"""
                Generate a creative, artistic image based on this description:
                
                {description}
                
                Make it visually striking with dynamic colors and artistic composition.
                
                If the description contains potentially sensitive content (provocative, violent, explicit themes):
                - Use abstract artistic representations instead of literal imagery
                - Focus on metaphors, symbolism, and emotional expression
                - Transform any sensitive elements into artistic visual poetry
                - Emphasize mood, atmosphere, and thematic elements
                - Create a visually striking image that captures the essence through artistic interpretation
                
                STRICTLY AVOID:
                - Any gore, blood, wounds, injuries or bodily harm
                - Macabre or morbid imagery (graves, coffins, dead bodies, skulls)
                - Disturbing, frightening, or horror-themed visuals
                - Weapons in violent or threatening contexts
                - Depictions of suffering, torture, or pain
                
                For dark themes, use symbolic alternatives:
                - Weather elements (storms, lightning) for conflict
                - Abstract colors and compositions for emotional states
                - Symbolic objects (broken glass, withered flowers) instead of literal depictions
                - Artistic stylization to transform intense content into abstract expressions
                """
                
                response = self.client.models.generate_content(
                    model="models/gemini-2.0-flash",
                    contents=fallback_prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=['Text', 'Image']
                    )
                )
                
                # Process and save the image
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            # Save the image data
                            with open(filepath, 'wb') as f:
                                f.write(part.inline_data.data)
                            print(f"Image saved to {filepath} using standard flash model")
                            return True
                
                return False
            
            # Try the standard flash model with retries
            success = retry_api_call(generate_image_with_flash)
            if success:
                return True
            
            # If both models fail, use the mock generator
            print("Both API models failed, using mock image generator")
            return self._generate_mock_image(description, filepath)
        except Exception as e:
            print(f"All image generation attempts failed: {type(e).__name__}: {str(e)[:100]}...")
            return self._generate_mock_image(description, filepath)
    
    def _generate_mock_image(self, description, filepath, lyrics_text=None, segment_type=None):
        """Generate a simple text-only image for fallback"""
        try:
            # Create a clean black image
            img_width, img_height = 1280, 720
            img = Image.new('RGB', (img_width, img_height), (0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Special case handling for instrumental segments or when description text is needed
            if segment_type == "instrumental" or not lyrics_text:
                # For instrumental segments or when lyrics are not available,
                # we'll display an appropriate symbol or the full description properly formatted
                
                if not description or description.strip() == "":
                    # No description available - show music note
                    display_text = "♪"
                    is_full_description = False
                else:
                    # Show a well-formatted description (but keep it short)
                    # Clean up the description - remove extra whitespace and normalize quotes
                    cleaned_description = description.replace("\n", " ").strip()
                    cleaned_description = ' '.join(cleaned_description.split())
                    
                    # Truncate extremely long descriptions (keep it reasonable)
                    if len(cleaned_description) > 300:
                        display_text = cleaned_description[:297] + "..."
                    else:
                        display_text = cleaned_description
                    
                    is_full_description = True
            else:
                # For lyric segments, just show the lyrics
                display_text = lyrics_text
                is_full_description = False
            
            # Adaptive font size based on text length and type
            if is_full_description:
                # Smaller font for descriptions
                base_font_size = 36
                if len(display_text) > 200:
                    font_size = 28
                elif len(display_text) > 100:
                    font_size = 32
                else:
                    font_size = base_font_size
            else:
                # Regular sizing for lyrics
                font_size = 60  # Default size
                if len(display_text) > 120:
                    font_size = 42  # Much smaller for very long text
                elif len(display_text) > 80:
                    font_size = 48  # Smaller for long text
            
            # Try to load a nice font
            try:
                font = ImageFont.truetype("Arial Bold.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype("Arial.ttf", font_size)
                except:
                    try:
                        font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
            
            # Adjust line wrapping based on content type
            if is_full_description:
                # More aggressive wrapping for descriptions - create paragraph-like text
                # with more lines and smaller width
                words = display_text.split()
                text_lines = []
                current_line = []
                
                # Approximate characters per line for the font size
                chars_per_line = int(img_width * 0.8 / (font_size * 0.5))
                
                current_length = 0
                for word in words:
                    if current_length + len(word) + 1 <= chars_per_line:
                        current_line.append(word)
                        current_length += len(word) + 1
                    else:
                        if current_line:
                            text_lines.append(" ".join(current_line))
                        current_line = [word]
                        current_length = len(word)
                
                if current_line:
                    text_lines.append(" ".join(current_line))
                
                # Limit to a reasonable number of lines
                max_lines = 8
                if len(text_lines) > max_lines:
                    text_lines = text_lines[:max_lines-1] + ["..."]
            else:
                # Standard line wrapping for lyrics
                if len(display_text) > 180:  # Extremely long - 4 lines
                    parts = display_text.split()
                    quarter = len(parts) // 4
                    text_lines = [
                        " ".join(parts[:quarter]),
                        " ".join(parts[quarter:2*quarter]),
                        " ".join(parts[2*quarter:3*quarter]),
                        " ".join(parts[3*quarter:])
                    ]
                elif len(display_text) > 120:  # Very long - 3 lines
                    parts = display_text.split()
                    third = len(parts) // 3
                    text_lines = [
                        " ".join(parts[:third]),
                        " ".join(parts[third:2*third]),
                        " ".join(parts[2*third:])
                    ]
                elif len(display_text) > 40:  # Medium - 2 lines
                    parts = display_text.split()
                    midpoint = len(parts) // 2
                    text_lines = [
                        " ".join(parts[:midpoint]),
                        " ".join(parts[midpoint:])
                    ]
                else:  # Short - 1 line
                    text_lines = [display_text]
            
            # Calculate total height for vertical centering
            line_count = len(text_lines)
            line_spacing = 16 if is_full_description else 20  # Tighter spacing for descriptions
            total_height = (font_size * line_count) + (line_spacing * (line_count-1))
            
            # Adjust vertical position - for descriptions, start higher to fit more text
            if is_full_description:
                start_y = max(50, (img_height - total_height) / 2 - 50)  # Higher position for descriptions
            else:
                start_y = (img_height - total_height) / 2  # Center for lyrics
            
            # Draw each line centered
            current_y = start_y
            for line in text_lines:
                # Calculate text width for centering
                text_width = 0
                if hasattr(draw, 'textlength'):
                    text_width = draw.textlength(line, font=font)
                else:
                    try:
                        text_width = font.getmask(line).getbbox()[2]
                    except:
                        text_width = len(line) * (font_size * 0.6)
                
                x_position = (img_width - text_width) / 2
                
                # Draw text outline for better contrast
                outline_thickness = 3 if is_full_description else 4  # Thinner outline for descriptions
                for dy in range(-outline_thickness, outline_thickness+1):
                    for dx in range(-outline_thickness, outline_thickness+1):
                        if dx*dx + dy*dy <= outline_thickness*outline_thickness:
                            draw.text((x_position + dx, current_y + dy), line, fill=(0, 0, 0), font=font)
                
                # Draw white text
                draw.text((x_position, current_y), line, fill=(255, 255, 255), font=font)
                current_y += font_size + line_spacing
            
            # Save the image
            img.save(filepath)
            if is_full_description:
                logger.info(f"Generated description image: {filepath}")
                print(f"Generated description image: {filepath}")
            else:
                logger.info(f"Generated lyrics image: {filepath}")
                print(f"Generated lyrics image: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating mock image: {e}")
            print(f"Error generating mock image: {e}")
            
            # Ultimate emergency fallback with minimal dependencies
            try:
                img = Image.new('RGB', (1280, 720), (0, 0, 0))
                draw = ImageDraw.Draw(img)
                
                # Even in the emergency fallback, try to display something meaningful
                if segment_type == "instrumental":
                    emergency_text = "♪"
                elif lyrics_text:
                    emergency_text = lyrics_text
                else:
                    # Truncate description to fit
                    emergency_text = description[:50] + "..." if description and len(description) > 50 else "♪"
                
                font = ImageFont.load_default()
                draw.text((640, 360), emergency_text, fill=(255, 255, 255), font=font, anchor="mm")
                img.save(filepath)
                return True
            except:
                return False


def create_ai_directed_video(song_query, api_key=None, output_dir="output"):
    """Main function to create an AI-directed lyric video"""
    from lib.song_utils import search_song, download_audio, get_lyrics_with_timestamps
    
    # Create output directories
    os.makedirs(output_dir, exist_ok=True)
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    
    # Step 1: Search for song and get lyrics
    print(f"Searching for: {song_query}...")
    song_info = search_song(song_query)
    
    if not song_info:
        print("Song not found. Cannot create lyric video.")
        return None
    
    video_id = song_info['videoId']
    print(f"Found: {song_info['title']} by {', '.join(song_info['artists'])}")
    
    # Step 2: Download audio
    print(f"Downloading audio...")
    # Save the audio directly to the song-specific output directory
    audio_path = download_audio(video_id, output_dir=output_dir)
    
    # Step 3: Get lyrics with timestamps
    print("Retrieving lyrics with timestamps...")
    expected_title = song_info['title']
    lyrics_data = get_lyrics_with_timestamps(video_id, expected_title=expected_title)
    
    if not lyrics_data:
        print("Failed to retrieve lyrics. Cannot create lyric video.")
        return None
        
    # Verify that lyrics appear to match the requested song
    print("\n=== SONG AND LYRICS VERIFICATION FOR AI GENERATION ===")
    print(f"Original search query: '{song_query}'")
    print(f"Selected song: '{expected_title}' by {', '.join(song_info['artists'])}")
    print(f"Song ID: {video_id}")
    print("If the lyrics don't match the expected song, please abort and retry with a more specific query.")
    print("================================\n")
    
    # Step 4: Create lyrics timeline
    from lyrics_segmenter import create_timeline_from_lyrics, update_timeline_with_audio_duration
    timeline = create_timeline_from_lyrics(lyrics_data, song_info)
    
    # Check if we have segments before continuing
    if not timeline.segments:
        print("\n=== ERROR: NO LYRICS SEGMENTS CREATED ===")
        print("The timeline has 0 segments, which means either:")
        print("1. No timestamps were found in the lyrics")
        print("2. The lyrics format was not recognized")
        print("3. There was an error processing the lyrics")
        print("\nAborting video creation - timestamped lyrics are required.")
        print("Try another song or use a more specific search query.\n")
        return None
    
    # Get audio duration to update timeline
    from moviepy.editor import AudioFileClip
    audio_clip = AudioFileClip(audio_path)
    timeline = update_timeline_with_audio_duration(timeline, audio_clip.duration)
    
    # Save raw timeline to song-specific directory
    timeline_path = os.path.join(output_dir, "timeline_raw.json")
    timeline.save_to_file(timeline_path)
    
    # Step 5: Generate video concept
    print("Generating video concept with thinking model...")
    director = VideoCreativeDirector(api_key=api_key)
    video_concept = director.generate_video_concept(timeline)
    timeline.video_concept = video_concept
    
    # Save timeline with concept
    timeline_path = os.path.join(output_dir, "timeline_with_concept.json")
    timeline.save_to_file(timeline_path)
    
    # Step 6: Generate image descriptions
    print("Generating image descriptions with pro model...")
    image_generator = AIImageGenerator(output_dir=images_dir, api_key=api_key)
    timeline = image_generator.generate_image_descriptions(timeline)
    
    # Save timeline with descriptions
    timeline_path = os.path.join(output_dir, "timeline_with_descriptions.json")
    timeline.save_to_file(timeline_path)
    
    # Step 7: Generate images
    print("Generating images with flash-exp model...")
    timeline = image_generator.generate_images(timeline)
    
    # Save final timeline
    timeline_path = os.path.join(output_dir, "timeline_final.json")
    timeline.save_to_file(timeline_path)
    
    # Save video info file with song details
    safe_title = song_info['title'].replace(' ', '_').replace('/', '_')
    video_info = {
        "title": song_info['title'],
        "artists": song_info['artists'],
        "video_id": video_id,
        "query": song_query,
        "output_video": f"{safe_title}_lyric_video.mp4"
    }
    
    with open(os.path.join(output_dir, "video_info.json"), 'w') as f:
        json.dump(video_info, f, indent=2)
    
    print(f"AI-directed video assets prepared in {output_dir}")
    print(f"- Timeline: {timeline_path}")
    print(f"- Images: {images_dir}")
    print(f"- Audio: {audio_path}")
    
    return {
        "timeline": timeline,
        "audio_path": audio_path,
        "images_dir": images_dir
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Create AI-directed lyric video')
    parser.add_argument('song_query', help='Song name and artist to search for')
    parser.add_argument('--api-key', help='API key for AI service (overrides environment variable)')
    parser.add_argument('--output', help='Output directory', default='output')
    
    args = parser.parse_args()
    
    create_ai_directed_video(args.song_query, api_key=args.api_key, output_dir=args.output)