"""
Prompt template for generating video concepts
"""

VIDEO_CONCEPT_PROMPT = """
You are an expert creative director designing a lyric video concept for the song "{song_title}" by "{artists}".
Consider the song's mood, genre (if known), target audience, and cultural context.

Here are the complete lyrics:
--- LYRICS START ---
{full_lyrics}
--- LYRICS END ---

Analyze the lyrics, themes, and emotional arc of the song. Based on this analysis, create a cohesive visual concept for a lyric video composed of still images.

Constraints:
1. The video uses only still images that change with the lyrics.
2. Depict static scenes only; no camera movement.
3. Any action must be representable in a single, static frame.
4. Maintain consistency in visual style, color palette, and motifs throughout.

Output Requirements:
Provide your response as a JSON object with the following structure:
{{
  "overall_concept": "A detailed description (3-5 paragraphs) of the visual narrative, mood, and progression of the video.",
  "visual_style": "Describe the primary artistic style (e.g., 'cinematic realism', 'anime illustration', 'abstract geometric', 'watercolor painting', '80s synthwave', 'paper cutouts').",
  "color_palette": "List 3-5 dominant colors and describe the overall color mood (e.g., ['#FF5733', '#C70039', '#900C3F', '#581845'], 'Warm, intense, passionate').",
  "key_themes_or_motifs": ["List 5-7 core visual themes or recurring motifs derived from the lyrics and concept (e.g., 'broken mirrors', 'blooming flowers', 'city lights at night', 'intertwined hands', 'celestial bodies')."],
  "potential_genre_mood": "(Optional) Briefly describe the perceived genre and mood if you can infer it from the lyrics (e.g., ' melancholic indie folk', 'upbeat synth-pop', 'introspective ballad')."
}}

Ensure the JSON is valid. Focus on creating a unique and compelling visual interpretation of the song.
"""
