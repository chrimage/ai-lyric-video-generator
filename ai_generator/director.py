"""
Video Creative Director - Generates creative concepts for lyric videos
"""
import time
from typing import Optional

from ai_generator.config import GEMINI_API_KEY, AVAILABLE_API, THINKING_MODEL, client
from ai_generator.prompts import VIDEO_CONCEPT_PROMPT
from ai_generator.utils import retry_api_call, format_text_display
from lyrics_segmenter import LyricsTimeline

try:
    from google.genai import types
except ImportError:
    types = None


class VideoCreativeDirector:
    """Generates a creative direction for the lyric video"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the director with an API key
        
        Args:
            api_key: Optional API key to override the default
        """
        self.api_key = api_key or GEMINI_API_KEY
        self.api = AVAILABLE_API
        
        # Initialize client if different API key is provided
        if api_key and api_key != GEMINI_API_KEY and types:
            import google.genai as genai
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = client
    
    def thinking_generate(self, prompt: str) -> str:
        """
        Generate content using a thinking model
        
        Args:
            prompt: The prompt for the model
            
        Returns:
            Generated text from the model
        """
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
        """
        Generate a creative concept for the entire video
        
        Args:
            timeline: The lyrics timeline object
            
        Returns:
            A creative concept for the video
        """
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
    
    def _generate_concept_with_gemini(self, song_title: str, artists: str, full_lyrics: str) -> str:
        """
        Generate video concept using Gemini API with thinking model
        
        Args:
            song_title: The title of the song
            artists: The artists' names
            full_lyrics: The full lyrics text
            
        Returns:
            A generated concept for the video
        """
        # Print a nice header to show we're generating the video concept
        print("\n" + "="*80)
        print("🎬 GENERATING VIDEO CONCEPT")
        print("="*80)
        print(f"🎵 Song: \"{song_title}\" by {artists}")
        print(f"🧠 Using Gemini thinking model: {THINKING_MODEL}")
        print("-"*80)
        print("💭 Thinking about song themes, mood, and visual style...")
        
        # Format the prompt with song details
        prompt = VIDEO_CONCEPT_PROMPT.format(
            song_title=song_title,
            artists=artists,
            full_lyrics=full_lyrics
        )
        
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
        format_text_display(concept)
        
        print("="*80 + "\n")
        
        return concept
    
    def _generate_mock_concept(self, song_title: str, artists: str) -> str:
        """
        Generate a mock concept for testing
        
        Args:
            song_title: The title of the song
            artists: The artists' names
            
        Returns:
            A mock concept for the video
        """
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
        import random
        concept = random.choice(concepts)
        
        # Show the concept
        print("\n" + "-"*80)
        print("✨ MOCK VIDEO CONCEPT SELECTED:")
        print("-"*80)
        
        # Format the concept nicely with wrapping
        format_text_display(concept)
        
        print("="*80 + "\n")
        
        return concept
