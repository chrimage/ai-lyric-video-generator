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
        # Print a nice header to show we're generating the video concept
        print("\n" + "="*80)
        print("🎬 GENERATING VIDEO CONCEPT")
        print("="*80)
        print(f"🎵 Song: \"{song_title}\" by {artists}")
        print(f"🧠 Using Gemini thinking model: {THINKING_MODEL}")
        print("-"*80)
        print("💭 Thinking about song themes, mood, and visual style...")
        
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
        
        # Animated thinking process
        for i in range(5):
            time.sleep(0.4)
            dots = "." * (i % 4 + 1)
            spaces = " " * (3 - i % 4)
            print(f"🧠 Thinking{dots}{spaces}", end="\r", flush=True)
        
        # Get the concept
        concept = self.thinking_generate(prompt)
        
        # Show the concept
        print("\n" + "-"*80)
        print("✨ VIDEO CONCEPT GENERATED:")
        print("-"*80)
        
        # Format the concept nicely with wrapping
        concept_wrapped = textwrap.fill(concept, width=76)
        for line in concept_wrapped.split('\n'):
            print(f"  {line}")
        
        print("="*80 + "\n")
        
        return concept
    
    def _generate_mock_concept(self, song_title, artists):
        """Generate a mock concept for testing"""
        # Print a nice header to show we're using a mock concept
        print("\n" + "="*80)
        print("🎬 GENERATING MOCK VIDEO CONCEPT")
        print("="*80)
        print(f"🎵 Song: \"{song_title}\" by {artists}")
        print(f"🔍 Using mock generation (API unavailable)")
        print("-"*80)
        print("🎨 Selecting from pre-defined artistic styles...")
        
        # Animated selection process
        for i in range(3):
            time.sleep(0.3)
            dots = "." * (i % 3 + 1)
            spaces = " " * (2 - i % 3)
            print(f"🎲 Selecting style{dots}{spaces}", end="\r", flush=True)
            
        concepts = [
            f"A neon-lit urban landscape for {song_title} by {artists}. Vibrant purple and blue hues dominate the visuals, with each scene featuring stylized city elements like skyscrapers, street lights, and reflective surfaces. The lyrics appear as glowing neon signs integrated into the urban environment.",
            
            f"A minimalist, paper-cut art style for {song_title} by {artists}. Each scene uses a limited palette of pastel colors with white space. Elements appear as carefully arranged paper cutouts with subtle shadows. Lyrics are handwritten in a flowing calligraphy that complements the delicate visual style.",
            
            f"A retro 80s synthwave aesthetic for {song_title} by {artists}. Sunset gradients of pink, purple and orange create the backdrop for grid-lined horizons and geometric shapes. Chrome text with glowing outlines presents the lyrics, while vintage computer graphics and wireframe objects populate each scene."
        ]
        
        # Choose a random concept
        concept = random.choice(concepts)
        
        # Show the concept
        print("\n" + "-"*80)
        print("✨ MOCK VIDEO CONCEPT SELECTED:")
        print("-"*80)
        
        # Format the concept nicely with wrapping
        concept_wrapped = textwrap.fill(concept, width=76)
        for line in concept_wrapped.split('\n'):
            print(f"  {line}")
        
        print("="*80 + "\n")
        
        return concept
    

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
        
        CRITICAL REQUIREMENT - SELF-CONTAINED DESCRIPTIONS:
        * Each image description MUST be completely self-contained and standalone
        * NEVER use phrases like "same as before", "similar to image X", "continuing from previous", etc.
        * NEVER reference other images by their number
        * NEVER reference characters or elements from previous images without fully describing them again
        * If similar content appears in multiple images, fully describe it each time as if it's new
        * Each description must be complete enough to generate the image without any reference to other descriptions
        
        IMPORTANT INSTRUCTIONS:
        - For segments with lyrics, the text MUST be visually incorporated into the scene in a creative way
        - For instrumental segments, design images that maintain narrative flow and build anticipation
        - Create a cohesive visual journey where each image builds upon the previous ones
        - Ensure visual elements and themes evolve gradually, not abruptly
        - Each image should be a self-contained scene while fully describing all visual elements
        
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
                # For lyrics, create fully self-contained descriptions
                text_presentation = random.choice(['illuminated', 'embossed', 'floating', 'integrated', 'artistic', 'stylized'])
                
                descriptions.append(
                    f"{base_scene} A complete visual composition with '{segment.text}' as the central focus. "
                    f"The text is {text_presentation} within the scene, with {visual_element1} and {visual_element2} framing it artistically. "
                    f"Rich {primary_color} and {secondary_color} tones create depth and emotional resonance throughout the entire image. "
                    f"The {recurring_motifs[0]} and {recurring_motifs[1]} motifs appear as detailed visual elements that enhance the meaning of the text."
                )
            else:
                # For instrumental segments - completely self-contained
                if "Intro" in segment.text:
                    descriptions.append(
                        f"{base_scene} A complete visual composition representing an instrumental introduction. "
                        f"The scene features dynamic {visual_element1} elements throughout the frame, with {recurring_motifs[0]} imagery rendered in detail. "
                        f"Rich {primary_color} and {secondary_color} tones create an atmospheric quality across the entire image. "
                        f"The composition has a sense of beginning and establishment, with balanced visual elements creating a cohesive aesthetic."
                    )
                elif "Outro" in segment.text:
                    descriptions.append(
                        f"{base_scene} A standalone visual composition representing a musical conclusion. "
                        f"The image features harmoniously arranged {recurring_motifs[0]} and {recurring_motifs[1]} elements throughout the frame. "
                        f"{visual_element1} and {visual_element2} create visual texture across the composition. "
                        f"A gradient of {primary_color} to {secondary_color} tones creates a sense of completion and resolution across the entire scene."
                    )
                else:  # Instrumental Break
                    descriptions.append(
                        f"{base_scene} A full composition representing an instrumental musical passage. "
                        f"The image features dynamic {visual_element1} and {visual_element2} elements creating visual rhythm across the frame. "
                        f"{primary_color} and {secondary_color} tones create atmospheric depth throughout the entire scene. "
                        f"Detailed {recurring_motifs[0]} and {recurring_motifs[1]} imagery fills the composition with rich visual interest."
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
            
            # Generate descriptions based on segment type, but make them fully self-contained
            # We'll still use context for inspiration, but without direct references
            if prev_segment and prev_segment.image_description:
                if prev_segment.segment_type == "instrumental":
                    # Inspired by transition from instrumental to lyrics, but self-contained
                    return f"{base_desc}A complete visual scene featuring '{lyrics_text}' as the central focus. The text is artistically integrated into a composition with dynamic {color1} lighting that creates emotional resonance. Rich {motif} imagery surrounds the text, with subtle {element1} and {element2} elements creating depth and visual interest throughout the frame."
                else:
                    # Inspired by lyric-to-lyric transition, but fully self-contained
                    return f"{base_desc}A standalone visual composition centered on the lyrics '{lyrics_text}'. The text is artistically incorporated into a scene with {color1} and {color2} color harmonies. Detailed {motif} imagery fills the composition, with carefully arranged {element1} elements creating visual depth and emphasis on the emotional quality of these words."
            
            if next_segment and next_segment.image_description:
                if next_segment.segment_type == "instrumental":
                    # Inspired by transition to instrumental, but completely self-contained
                    return f"{base_desc}A complete visual scene showcasing '{lyrics_text}' as the primary focus. The text is artistically rendered as part of a harmonious composition with {motif} imagery throughout. The scene features rich {color1} and {color2} color treatments that create an emotionally resonant atmosphere, with {element1} elements adding visual complexity and depth to the entire frame."
            
            # Generic lyrics description with style consistency
            return f"{base_desc}A powerful visual representation of '{lyrics_text}', with the text integrated as a key element in the composition. The scene captures the emotional essence of these words, using {color1} highlights to emphasize key aspects. The {motif} imagery reinforces the meaning behind these lyrics."
        
        else:
            # For instrumental segments - completely self-contained
            segment_type = segment.text.lower()
            
            if "intro" in segment_type:
                # Intro segment - fully standalone
                return f"{base_desc}A captivating establishing scene for an instrumental introduction. A complete visual composition featuring {motif} imagery in a {color1} and {color2} color palette. The scene has a sense of beginning and potential, with {element1} elements arranged to create visual rhythm. Dynamic lighting creates depth across the entire frame, establishing a distinct aesthetic with artistic composition."
            
            elif "outro" in segment_type:
                # Outro segment - fully standalone
                return f"{base_desc}A complete visual scene representing a musical conclusion. A harmoniously balanced composition with {motif} imagery rendered in gradually shifting {color1} to {color2} tones. The scene has a sense of resolution and completion, with {element1} and {element2} elements arranged in a visually satisfying pattern. The lighting creates a sense of conclusion through subtle gradients across the frame."
            
            else:
                # Instrumental break/bridge - fully standalone
                if prev_segment and next_segment and prev_segment.segment_type == "lyrics" and next_segment.segment_type == "lyrics":
                    # Inspired by bridging position but fully standalone
                    return f"{base_desc}A complete visual scene representing an instrumental musical moment. A balanced composition featuring abstract {motif} imagery with {element1} elements creating visual movement. The scene uses a full spectrum of {color1} and {color2} tones to create a sense of progression and emotional depth. Dynamic lighting creates visual interest throughout the entire frame, with textural elements adding complexity."
                
                # Generic instrumental description - fully standalone
                return f"{base_desc}A standalone atmospheric visual scene representing an instrumental musical passage. The composition features rich {motif} imagery with carefully arranged {element1} and {element2} elements throughout the frame. {color1.capitalize()} and {color2} colors create emotional resonance, with variations in lighting bringing depth to different areas of the scene. The complete composition stands on its own as a visual interpretation of the music."
    
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
        print("\n" + "="*80)
        print(f"🎬 GENERATING LYRIC VIDEO IMAGERY")
        print("="*80)
        print(f"📊 Total segments: {total_segments}")
        print(f"📦 Batch size: {batch_size}")
        print(f"⏱️ Batch delay: {batch_delay:.1f}s")
        print("-"*80)
        
        # Track content filter issues for reporting
        content_filter_count = 0
        content_filter_resolved = 0
        
        # Process images in batches to avoid rate limits
        for batch_start in range(0, total_segments, batch_size):
            batch_end = min(batch_start + batch_size, total_segments)
            batch_num = batch_start // batch_size + 1
            total_batches = (total_segments + batch_size - 1) // batch_size
            
            logger.info(f"Processing image batch {batch_start+1}-{batch_end} of {total_segments}")
            
            # Calculate progress percentage
            progress_pct = batch_start / total_segments * 100
            
            # Create a visual progress bar
            bar_width = 40
            filled_width = int(bar_width * batch_start / total_segments)
            bar = '█' * filled_width + '░' * (bar_width - filled_width)
            
            print(f"\n🔄 BATCH {batch_num}/{total_batches}: Segments {batch_start+1}-{batch_end} of {total_segments}")
            print(f"[{bar}] {progress_pct:.1f}%")
            
            for i in range(batch_start, batch_end):
                segment = timeline.segments[i]
                
                # Generate a filename
                safe_text = segment.text[:20].replace(' ', '_').replace('/', '_')
                filename = f"{i:03d}_{safe_text}.png"
                filepath = os.path.join(self.output_dir, filename)
                
                # Create a segment identifier for display
                segment_type_emoji = "🎵" if segment.segment_type == "lyrics" else "🎹"
                segment_text = segment.text.strip()
                if len(segment_text) > 30:
                    segment_text = segment_text[:27] + "..."
                
                print(f"\n  {segment_type_emoji} Segment {i+1}/{total_segments}: \"{segment_text}\"")
                
                # Check if the image already exists
                if os.path.exists(filepath):
                    logger.info(f"Image already exists: {filename}")
                    print(f"  ✓ Image already exists: {filename}")
                    segment.image_path = filepath
                    continue
                
                # Show the image description - this reveals Gemini's creative process
                print(f"\n  📝 IMAGE DESCRIPTION:")
                description_wrapped = textwrap.fill(segment.image_description, width=76)
                for line in description_wrapped.split('\n'):
                    print(f"  {line}")
                print("\n  🎨 Generating image...")
                
                # Generate the image
                success = False
                content_filtered = False
                
                try:
                    if self.api == "gemini" and self.api_key and self.client:
                        success = self._generate_image_with_gemini(segment.image_description, filepath)
                        
                        # Check if the original description was updated due to content filtering
                        if success and hasattr(success, 'description_revised'):
                            content_filter_count += 1
                            content_filter_resolved += 1
                            # Update the segment with the safer description that worked
                            segment.image_description = success.description_revised
                            logger.info(f"Updated segment {i+1} with safer description that passed content filters")
                            # Set success to True since the image was generated after revisions
                            success = True
                    else:
                        success = self._generate_mock_image(segment.image_description, filepath, segment.text, segment.segment_type)
                except Exception as e:
                    error_str = str(e).lower()
                    # Check if this was a content filter issue
                    if any(term in error_str for term in ["content filter", "safety", "policy", "inappropriate"]):
                        content_filter_count += 1
                        content_filtered = True
                        logger.warning(f"Content filter blocked image for segment {i+1}: {error_str[:100]}...")
                        print(f"Content filter blocked image for segment {i+1}")
                    else:
                        logger.error(f"Error generating image for segment {i+1}: {e}")
                        print(f"Error generating image for segment {i+1}: {e}")
                    success = False
                
                # If API generation failed, fall back to mock image
                if not success and self.api == "gemini":
                    if content_filtered:
                        logger.warning(f"Using mock image for segment {i+1} due to content filtering")
                        print(f"Using mock image for segment {i+1} due to content filtering")
                    else:
                        logger.warning(f"Falling back to mock image for segment {i+1}")
                        print(f"Falling back to mock image for segment {i+1}")
                    
                    success = self._generate_mock_image(segment.image_description, filepath, segment.text, segment.segment_type)
                
                if success:
                    segment.image_path = filepath
                
                # Add a small delay between images within a batch
                if i < batch_end - 1:  # Skip delay after the last image in a batch
                    time.sleep(random.uniform(0.5, 1.5))
            
            # Show a batch summary
            batch_success = sum(1 for i in range(batch_start, batch_end) 
                               if timeline.segments[i].image_path)
            batch_total = batch_end - batch_start
            
            # Calculate the final progress after this batch
            progress_pct = batch_end / total_segments * 100
            filled_width = int(bar_width * batch_end / total_segments)
            bar = '█' * filled_width + '░' * (bar_width - filled_width)
            
            print(f"\n  ✨ Batch {batch_num}/{total_batches} complete!")
            print(f"  📊 Success rate: {batch_success}/{batch_total} images generated")
            print(f"  [.] {'-' * 40} [.]")
            print(f"  [{bar}] {progress_pct:.1f}%")
            
            # Add a longer delay between batches
            if batch_end < total_segments:
                logger.info(f"Batch complete. Waiting {batch_delay:.1f}s before next batch...")
                print(f"  ⏳ Waiting {batch_delay:.1f}s before next batch...")
                
                # Show a countdown animation
                for i in range(int(batch_delay), 0, -1):
                    print(f"  ⌛ Next batch in {i}s...", end="\r", flush=True)
                    time.sleep(1)
                print("  🚀 Starting next batch!                ")
                time.sleep(0.5)
        
        # Report on content filter issues if any occurred
        print("\n" + "="*80)
        print("📊 GENERATION SUMMARY")
        print("="*80)
        print(f"🖼️ Total images processed: {total_segments}")
        print(f"✅ Successfully generated: {sum(1 for segment in timeline.segments if segment.image_path)}")
        
        if content_filter_count > 0:
            success_rate = (content_filter_resolved / content_filter_count) * 100 if content_filter_count > 0 else 0
            logger.info(f"Content filter summary: {content_filter_count} images triggered content filters")
            logger.info(f"Successfully resolved {content_filter_resolved} of {content_filter_count} content filter issues")
            
            print(f"🚫 Content filter blocks: {content_filter_count}")
            print(f"🔄 Successful revisions: {content_filter_resolved} ({success_rate:.1f}%)")
            
            if content_filter_resolved > 0:
                print("\n🎨 REVISION TECHNIQUES USED:")
                print("  • Abstracting potentially problematic content")
                print("  • Transforming literal elements to symbolic representations")
                print("  • Using color and composition to convey emotional tone")
                print("  • Applying metaphorical imagery instead of direct depictions")
                print("  • Censoring sensitive words in lyrics with asterisks")
                print("  • Progressively removing explicit lyrics references")
                print("  • Converting content to pure abstract expression")
        else:
            print(f"🎉 No content filter blocks encountered!")
            
        print("="*80)
        
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
    
    def _generate_safer_description(self, original_description, block_reason=""):
        """Generate a safer, more appropriate image description if content was filtered"""
        if not self.client:
            return None
            
        print("\n" + "="*80)
        print("🔄 REVISING BLOCKED DESCRIPTION")
        print("="*80)
        print(f"🚫 ORIGINAL: \"{original_description[:100]}{'...' if len(original_description) > 100 else ''}\"")
        
        if block_reason:
            print(f"⚠️ BLOCK REASON: {block_reason}")
        
        print("-"*80)
        
        # Extract any lyrics or quoted text from the description
        quoted_text = ""
        if "'" in original_description and "'" in original_description:
            try:
                # Try to extract any quoted text which might be lyrics
                quoted_parts = original_description.split("'")
                if len(quoted_parts) >= 3:  # Need at least one complete quote
                    for i in range(1, len(quoted_parts), 2):
                        if quoted_parts[i].strip():
                            quoted_text = quoted_parts[i].strip()
                            break
            except:
                quoted_text = ""
        
        # If we found quoted text, suggest approaches to handle it
        lyrics_guidance = ""
        if quoted_text:
            words = quoted_text.split()
            censored_words = []
            for word in words:
                if len(word) > 3:  # Only censor longer words
                    censored_words.append(word[0] + "*" * (len(word) - 2) + word[-1])
                else:
                    censored_words.append(word)
            censored_text = " ".join(censored_words)
            
            lyrics_guidance = f"""
            I notice the description contains lyrics: '{quoted_text}'
            
            These lyrics may be triggering the content filter. Please try these approaches:
            1. Remove the lyrics completely and focus on the emotional tone instead
            2. Replace the lyrics with a general description like "lyrics expressing [emotion/theme]"
            3. Transform the lyrics into abstract imagery representing their emotional essence
            4. Use sophisticated artistic metaphors instead of literal interpretations
            """
            
            print(f"  📌 Found potential problematic lyrics: '{quoted_text}'")
        
        # Use the block reason to provide more specific guidance
        specific_guidance = ""
        if block_reason:
            if "safety" in block_reason.lower():
                specific_guidance = """
                The content was blocked for safety reasons. Please:
                - Focus on abstract artistic elements only
                - Remove any potentially violent, disturbing, or adult content
                - Use color, form, and composition to convey emotion rather than literal depictions
                - Create a completely symbolic representation without any controversial elements
                """
            elif "prohibited" in block_reason.lower():
                specific_guidance = """
                The content contains prohibited material. Please:
                - Completely remove any explicit, offensive, or controversial language
                - Create a purely abstract artistic interpretation 
                - Use only neutral, non-controversial visual elements
                - Focus on color, shape, and light rather than subject matter
                """
            
        revision_prompt = f"""
        The following image description was flagged by content filters as potentially problematic:
        
        "{original_description}"
        
        {f"BLOCK REASON: {block_reason}" if block_reason else ""}
        
        Please rewrite this description to make it more appropriate for a general audience music video while 
        preserving the artistic essence. Your new description should:
        
        1. Remove any potentially problematic content
        2. Use abstract artistic imagery, metaphors, and symbolism instead of explicit references
        3. Focus on colors, lighting, composition, and emotional atmosphere
        4. Replace any potentially sensitive elements with safe, artistic alternatives
        5. Be suitable for a general audience music video
        6. Maintain the core artistic intention and emotional resonance
        
        {specific_guidance}
        {lyrics_guidance}
        
        Use abstract visual elements, artistic symbolism, and creative techniques to convey 
        the emotional essence without any content that could trigger moderation filters.
        
        Create a description that is extremely unlikely to be flagged by ANY content filter.
        Think about how you would represent this artistic concept in the most acceptable way possible.
        
        Please also provide a brief explanation of how you transformed the description to be more appropriate.
        Format your response as:
        
        REVISED DESCRIPTION: [Your revised description here]
        
        CREATIVE PROCESS: [Brief explanation of your transformation approach]
        """
        
        try:
            print("🧠 Asking Gemini to revise the description...")
            
            # Use the same model that generates image descriptions - "models/gemini-2.0-flash"
            # Which is the model defined in the _generate_descriptions_with_gemini method
            response = self.client.models.generate_content(
                model="models/gemini-2.0-flash",
                contents=revision_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2  # Lower temperature for more consistent, safe results
                )
            )
            
            if response.candidates and response.candidates[0].content.parts:
                full_response = response.candidates[0].content.parts[0].text.strip()
                
                # Extract the revised description and creative process explanation
                revised_description = ""
                creative_process = ""
                
                if "REVISED DESCRIPTION:" in full_response:
                    parts = full_response.split("REVISED DESCRIPTION:")
                    if len(parts) > 1:
                        desc_part = parts[1].strip()
                        if "CREATIVE PROCESS:" in desc_part:
                            desc_parts = desc_part.split("CREATIVE PROCESS:")
                            revised_description = desc_parts[0].strip()
                            if len(desc_parts) > 1:
                                creative_process = desc_parts[1].strip()
                        else:
                            revised_description = desc_part
                else:
                    # If the model didn't follow the format, just use the whole response
                    revised_description = full_response
                
                # Log the information
                logger.info(f"Generated revised description: {revised_description[:100]}...")
                
                # Print the results in a nicely formatted way
                print("-"*80)
                print(f"✅ REVISED: \"{revised_description[:100]}{'...' if len(revised_description) > 100 else ''}\"")
                
                if creative_process:
                    print("-"*80)
                    print("🎨 CREATIVE PROCESS:")
                    wrapped_process = textwrap.fill(creative_process, width=76)
                    for line in wrapped_process.split('\n'):
                        print(f"  {line}")
                
                print("="*80 + "\n")
                
                return revised_description
            return None
        except Exception as e:
            logger.error(f"Error generating revised description: {e}")
            print(f"❌ Error generating revised description: {e}")
            return None
    
    def _generate_image_with_gemini(self, description, filepath):
        """Generate image using Gemini API with the flash-exp model"""
        original_description = description
        max_revision_attempts = 3
        
        # Show a little "sending to Gemini" animation
        print("  💫 Sending to Gemini image generator", end="", flush=True)
        for _ in range(3):
            time.sleep(0.2)
            print(".", end="", flush=True)
        print(" model: flash-exp-image-generation")
        current_attempt = 0
        
        while current_attempt <= max_revision_attempts:
            prompt = f"""
            Create a high-quality still image for a lyric video with the following description:
            
            {description}
            
            IMPORTANT: This image must be entirely self-contained and stand alone, with no assumptions about any other images in the sequence. The image should be designed to make sense without any references to previous or future images.
            
            The image should:
            - Be in 16:9 aspect ratio (1280x720 or similar)
            - Have high contrast and readability for any text elements
            - Be visually striking and suitable for a music video
            - No humans or faces should be included
            - Contain all visual elements fully described in the prompt above
            
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
                    
                    # Check for content filter blocks in the response
                    if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                        # Check if the prompt was blocked
                        if hasattr(response.prompt_feedback, 'block_reason') and response.prompt_feedback.block_reason:
                            block_reason = response.prompt_feedback.block_reason
                            print(f"\n❌ CONTENT FILTER BLOCKED: {block_reason}")
                            logger.warning(f"Content filter blocked generation. Reason: {block_reason}")
                            
                            # Return a content filter error object to trigger our revision process
                            from types import SimpleNamespace
                            content_filter_error = SimpleNamespace()
                            content_filter_error.is_content_filtered = True
                            content_filter_error.block_reason = block_reason
                            content_filter_error.original_prompt = prompt
                            return content_filter_error
                    
                    # Also check for no candidates or empty candidates, which can indicate filtering
                    if not response.candidates or len(response.candidates) == 0:
                        print("\n❌ CONTENT FILTER BLOCKED: No candidates returned")
                        logger.warning("Content filter likely blocked generation - no candidates returned")
                        
                        # Return a content filter error object
                        from types import SimpleNamespace
                        content_filter_error = SimpleNamespace()
                        content_filter_error.is_content_filtered = True
                        content_filter_error.block_reason = "No candidates returned (likely filtered)"
                        content_filter_error.original_prompt = prompt
                        return content_filter_error
                    
                    # Process and save the image if we have valid candidates
                    candidate = response.candidates[0]
                    
                    # Check safety ratings (if they exist)
                    if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                        # Log all safety ratings
                        for rating in candidate.safety_ratings:
                            if hasattr(rating, 'category') and hasattr(rating, 'probability'):
                                logger.info(f"Safety rating - Category: {rating.category}, Probability: {rating.probability}")
                    
                    # Further check if content parts are missing or empty (another indicator of filtering)
                    if not hasattr(candidate, 'content') or not candidate.content:
                        print("\n❌ CONTENT FILTER BLOCKED: Empty content in response")
                        logger.warning("Content filter likely blocked generation - empty content in response")
                        
                        # Return a content filter error object
                        from types import SimpleNamespace
                        content_filter_error = SimpleNamespace()
                        content_filter_error.is_content_filtered = True
                        content_filter_error.block_reason = "Empty content in response (likely filtered)"
                        content_filter_error.original_prompt = prompt
                        return content_filter_error
                        
                    if not hasattr(candidate.content, 'parts') or not candidate.content.parts:
                        print("\n❌ CONTENT FILTER BLOCKED: No parts in content")
                        logger.warning("Content filter likely blocked generation - no parts in content")
                        
                        # Return a content filter error object
                        from types import SimpleNamespace
                        content_filter_error = SimpleNamespace()
                        content_filter_error.is_content_filtered = True
                        content_filter_error.block_reason = "No parts in content (likely filtered)"
                        content_filter_error.original_prompt = prompt
                        return content_filter_error
                    
                    # Process the content parts if they exist
                    for part in candidate.content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            # Save the image data
                            with open(filepath, 'wb') as f:
                                f.write(part.inline_data.data)
                            print("\n" + "="*80)
                            print(f"✅ SUCCESS! Image generated on first attempt")
                            print(f"🖼️ Image saved to: {filepath}")
                            print("="*80)
                            return True
                        elif hasattr(part, 'text') and part.text:
                            print(f"Image generation message: {part.text[:100]}...")
                    
                    # If we get here, no image was found but response seemed valid otherwise
                    print("No image data found in the successful response")
                    logger.warning("No image data found in the successful response - possible filtering")
                    
                    # Treat this as a content filter as well
                    from types import SimpleNamespace
                    content_filter_error = SimpleNamespace()
                    content_filter_error.is_content_filtered = True
                    content_filter_error.block_reason = "No image data in response (likely filtered)"
                    content_filter_error.original_prompt = prompt
                    return content_filter_error
                    
                except Exception as e:
                    # Log the exception but check if it's a safety/filtering error
                    error_str = str(e).lower()
                    if "safety" in error_str or "content" in error_str or "filter" in error_str or "block" in error_str or "prohibit" in error_str:
                        print(f"\n❌ CONTENT FILTER ERROR: {type(e).__name__}: {str(e)[:100]}...")
                        logger.warning(f"Content filter error: {type(e).__name__}: {str(e)}")
                        
                        # Return a content filter error object
                        from types import SimpleNamespace
                        content_filter_error = SimpleNamespace()
                        content_filter_error.is_content_filtered = True
                        content_filter_error.block_reason = str(e)
                        content_filter_error.original_prompt = prompt
                        return content_filter_error
                    else:
                        # Not a content filter error, log it and allow retry
                        print(f"Exception in generate_image: {type(e).__name__}: {str(e)[:100]}...")
                        raise  # Re-raise for retry_api_call to handle
            
            # Try with current description
            result = retry_api_call(generate_image)
            
            # Check if the function returned a content filter error
            if result is not None and hasattr(result, 'is_content_filtered'):
                current_attempt += 1
                if current_attempt <= max_revision_attempts:
                    logger.warning(f"Content filter triggered (attempt {current_attempt}/{max_revision_attempts}). Generating safer description...")
                    print(f"Content filter triggered (attempt {current_attempt}/{max_revision_attempts}). Generating safer description...")
                    
                    # Check if we have a block reason to inform the revision
                    block_reason = ""
                    if hasattr(result, 'block_reason'):
                        block_reason = result.block_reason
                        print(f"🔍 Block reason: {block_reason}")
                    
                    # Generate a safer description with the block reason
                    safer_description = self._generate_safer_description(description, block_reason)
                    if safer_description:
                        description = safer_description
                        logger.info(f"Trying again with safer description: {description[:100]}...")
                        print(f"Trying again with safer description based on feedback...")
                        continue
                    else:
                        # If we couldn't generate a safer description, make a simplified one
                        description = f"Abstract artistic composition with {', '.join(description.split()[:5])}... represented through colors, shapes, and symbolic imagery."
                        logger.info(f"Using simplified description: {description}")
                        print(f"Using simplified description for next attempt")
                        continue
                else:
                    logger.warning(f"Reached maximum revision attempts ({max_revision_attempts}). Falling back to standard model...")
                    print(f"Reached maximum revision attempts ({max_revision_attempts}). Falling back to standard model...")
                    break
            elif result:
                # Success! If we succeeded after revising descriptions, track this
                if description != original_description:
                    # Return a custom object with the success and the revised description
                    from types import SimpleNamespace
                    success_result = SimpleNamespace()
                    success_result.success = True
                    success_result.description_revised = description
                    return success_result
                # Otherwise just return True
                return True
            else:
                # Failed but not due to content filtering
                break
        
        # If we get here, either we've exhausted our revision attempts or encountered non-content-filter errors
        # Instead of falling back to a different model, try more abstract descriptions with the same model
        print("\n" + "="*80)
        print("🌈 CREATING ABSTRACT INTERPRETATIONS")
        print("="*80)
        print(f"🎭 ORIGINAL DESCRIPTION TOO CHALLENGING FOR DIRECT VISUALIZATION")
        print("-"*80)
        
        # Reset the attempt counter for a different approach
        current_attempt = 0
        
        # Start with a very abstract version of the original description
        abstract_description = f"Abstract artistic interpretation of '{original_description}' using colors, shapes, and symbolic visual elements. Represented through metaphorical imagery with emphasis on mood and atmosphere rather than literal depiction."
        description = abstract_description
        
        print(f"🧩 ABSTRACT APPROACH: Transforming to pure artistic expression")
        print(f"📝 LEVEL 1 ABSTRACTION: \"{description[:100]}{'...' if len(description) > 100 else ''}\"")
        print("="*80)
        
        while current_attempt <= max_revision_attempts:
            abstract_prompt = f"""
            Create a high-quality artistic image based on this abstract description:
            
            {description}
            
            Make it visually striking with dynamic colors and artistic composition.
            
            KEEP IT ABSTRACT:
            - Use metaphorical and symbolic representation only
            - Focus on colors, shapes, and composition to convey emotion
            - Transform any potentially sensitive concepts into pure artistic expression
            - Create a completely abstract interpretation using color and form
            
            STRICTLY AVOID:
            - Any literal depictions of potentially problematic content
            - Any concrete representations that could trigger content filters
            - Realistic imagery of any sensitive subject matter
            
            For artistic expression, use:
            - Abstract color fields and geometric shapes
            - Artistic stylization and non-representational elements
            - Symbolic use of light, shadow, and texture
            - Visual poetry through pure form and composition
            """
            
            def generate_abstract_image():
                try:
                    # Continue to use the same image generation model
                    response = self.client.models.generate_content(
                        model=IMAGE_GENERATION_MODEL,  # Still use the specific image generation model
                        contents=abstract_prompt,
                        config=types.GenerateContentConfig(
                            response_modalities=['Image', 'Text'],
                            temperature=0.4,
                            max_output_tokens=4096
                        )
                    )
                    
                    # Process and save the image
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                # Save the image data
                                with open(filepath, 'wb') as f:
                                    f.write(part.inline_data.data)
                                print("\n" + "="*80)
                                print(f"✅ SUCCESS! Abstract approach worked!")
                                print(f"🖼️ Image saved to: {filepath}")
                                print("="*80)
                                return True
                    
                    return False
                except Exception as e:
                    print(f"Abstract image generation exception: {type(e).__name__}: {str(e)[:100]}...")
                    raise  # Re-raise for retry_api_call to handle
            
            # Show what we're sending to Gemini (more insight into creative process)
            print("\n  💠 ABSTRACT APPROACH PROMPT:")
            wrapped_keywords = textwrap.fill(description, width=70)
            for line in wrapped_keywords.split('\n'):
                print(f"  • {line}")
            
            # Show a little animation
            print("\n  🔮 Generating abstract interpretation", end="", flush=True)
            for _ in range(3):
                time.sleep(0.2)
                print(".", end="", flush=True)
            print("")
            
            # Try with more abstract description
            result = retry_api_call(generate_abstract_image)
            
            # Check if the function returned a content filter error
            if result is not None and hasattr(result, 'is_content_filtered'):
                current_attempt += 1
                if current_attempt <= max_revision_attempts:
                    logger.warning(f"Content filter still triggered (attempt {current_attempt}/{max_revision_attempts}). Creating even more abstract description...")
                    print(f"Content filter still triggered (attempt {current_attempt}/{max_revision_attempts}). Creating even more abstract description...")
                    
                    # Extract the segment text if it exists in the original description
                    segment_text = ""
                    if "'" in original_description and "'" in original_description:
                        try:
                            # Try to extract any quoted text which might be lyrics
                            quoted_parts = original_description.split("'")
                            if len(quoted_parts) >= 3:  # Need at least one complete quote
                                for i in range(1, len(quoted_parts), 2):
                                    if quoted_parts[i].strip():
                                        segment_text = quoted_parts[i].strip()
                                        break
                        except:
                            segment_text = ""
                    
                    # Make description progressively more abstract with each attempt
                    if current_attempt == 1:
                        # First level: censor any lyrics with asterisks but keep them
                        censored_text = ""
                        if segment_text:
                            words = segment_text.split()
                            censored_words = []
                            for word in words:
                                if len(word) > 3:  # Only censor longer words
                                    censored_words.append(word[0] + "*" * (len(word) - 2) + word[-1])
                                else:
                                    censored_words.append(word)
                            censored_text = " ".join(censored_words)
                            
                            description = f"Abstract composition expressing the emotional essence of '{censored_text}' through colors and shapes with artistic stylization."
                            print("\n" + "-"*80)
                            print(f"📝 LEVEL 2 ABSTRACTION: \"{description}\"")
                            print(f"💭 Using censored lyrics in abstract composition")
                        else:
                            description = "Abstract composition with colors and shapes expressing emotional atmosphere through artistic stylization."
                            print("\n" + "-"*80)
                            print(f"📝 LEVEL 2 ABSTRACTION: \"{description}\"")
                            print(f"💭 Moving to composition-focused abstract approach with emotional atmosphere")
                    
                    elif current_attempt == 2:
                        # Second level: remove lyrics completely, focus on emotional tone only
                        description = "Pure abstract art with color fields and geometric forms conveying emotional tone without any text content."
                        print("\n" + "-"*80)
                        print(f"📝 LEVEL 3 ABSTRACTION: \"{description}\"")
                        print(f"💭 Removing all lyrics, using pure abstract art with basic color fields and geometry")
                    
                    else:
                        # Final level: minimal abstract elements only, no reference to content
                        description = "Minimal abstract composition with basic color and form expressing only mood through non-representational elements."
                        print("\n" + "-"*80)
                        print(f"📝 LEVEL 4 ABSTRACTION (MAXIMUM): \"{description}\"")
                        print(f"💭 Final attempt with minimal abstract elements only, no content reference")
                    
                    logger.info(f"Trying again with ultra-abstract description: {description}")
                    print("-"*80)
                    continue
                else:
                    # We've exhausted all options with the AI models
                    logger.warning(f"Content filtering persists after all attempts. Using mock image.")
                    print(f"Content filtering persists after all attempts. Using mock image.")
                    return self._generate_mock_image(original_description, filepath)
            elif result:
                # Success with abstract approach! Track the revised description
                if description != original_description:
                    # Return a custom object with the success and the revised description
                    from types import SimpleNamespace
                    success_result = SimpleNamespace()
                    success_result.success = True
                    success_result.description_revised = description
                    return success_result
                # Otherwise just return True
                return True
            else:
                # Not a content filter issue, but still failed
                break
        
        # If we get here, all attempts failed - use mock image generator
        print("All image generation attempts failed, using mock image generator")
        return self._generate_mock_image(original_description, filepath)
    
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
    # If we already have song info, don't search again
    if os.path.exists(os.path.join(output_dir, "video_info.json")):
        import json
        try:
            with open(os.path.join(output_dir, "video_info.json"), "r") as f:
                video_info = json.load(f)
                song_info = {
                    'videoId': video_info.get('video_id'),
                    'title': video_info.get('title'),
                    'artists': video_info.get('artists'),
                    'original_query': video_info.get('query')
                }
                print(f"Using existing song info from {output_dir}/video_info.json")
        except Exception as e:
            print(f"Error loading existing song info: {e}")
            print("Searching for song info...")
            song_info = search_song(song_query)
    else:
        song_info = search_song(song_query)
    
    if not song_info:
        print("Song not found. Cannot create lyric video.")
        return None
    
    video_id = song_info['videoId']
    print(f"Found: {song_info['title']} by {', '.join(song_info['artists'])}")
    
    # Step 2: Download audio (only if it doesn't exist)
    audio_path = None
    for file in os.listdir(output_dir):
        if file.endswith(".mp3"):
            audio_path = os.path.join(output_dir, file)
            print(f"Using existing audio file: {audio_path}")
            break
    
    if not audio_path:
        print(f"Downloading audio...")
        # Save the audio directly to the song-specific output directory
        audio_path = download_audio(video_id, output_dir=output_dir)
    
    # Step 3: Get lyrics with timestamps (only if we don't have a timeline file)
    if os.path.exists(os.path.join(output_dir, "timeline_raw.json")):
        print("Using existing timeline with lyrics")
        from lyrics_segmenter import LyricsTimeline
        timeline = LyricsTimeline.load_from_file(os.path.join(output_dir, "timeline_raw.json"))
        lyrics_data = True  # Just a placeholder to indicate we have lyrics
    else:
        # Check if the song has timestamped lyrics before trying to retrieve them
        from lib.song_utils import check_lyrics_availability
        print("Checking lyrics availability...")
        lyrics_status = check_lyrics_availability(video_id)
        
        # If no timestamped lyrics, abort early 
        if not lyrics_status['has_timestamps']:
            print("\n" + "="*80)
            print("❌ LYRICS CHECK FAILED: CANNOT CREATE LYRIC VIDEO")
            print("="*80)
            print(f"🎵 Song: {song_info['title']} by {', '.join(song_info['artists'])}")
            print(f"ℹ️ Status: {lyrics_status['message']}")
            print(f"⚠️ This application requires songs with timestamped lyrics.")
            print("="*80)
            return None
            
        # Great! We have timestamped lyrics
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