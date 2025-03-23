"""
Prompt template for generating video concepts
"""

VIDEO_CONCEPT_PROMPT = """
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
