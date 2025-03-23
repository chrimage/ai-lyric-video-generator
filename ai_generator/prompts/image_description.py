"""
Prompt template for generating image descriptions
"""

IMAGE_DESCRIPTION_PROMPT = """
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

⚠️ ABSOLUTELY CRITICAL REQUIREMENT - SELF-CONTAINED DESCRIPTIONS ⚠️
* Each image description MUST be COMPLETELY self-contained and standalone with NO external references
* ❌ CRITICAL ERROR: NEVER use phrases like "from the previous image", "same as before", "the clockwork crown from the previous image", "similar to image X", "continuing from previous", etc.
* ❌ CRITICAL ERROR: NEVER reference other images by their number or mention previous or future images at all
* ❌ CRITICAL ERROR: NEVER reference characters, objects, or elements without fully describing them in each image
* ❌ CRITICAL ERROR: If the same crown, character, or element appears in multiple images, describe it completely each time as if it's the first time it appears
* Each description must contain ALL information needed to generate the image without any knowledge of other descriptions
* Imagine each description will be given to a completely different artist who can't see any other descriptions
* EVERY single image must stand completely on its own with full context and description

IMPORTANT INSTRUCTIONS:
- For segments with lyrics, the text MUST be visually incorporated into the scene in a creative way
- For instrumental segments, design images that maintain narrative flow and build anticipation
- Create a cohesive visual journey where each image builds upon the previous ones
- Ensure visual elements and themes evolve gradually, not abruptly 
- Each image should be a self-contained scene while fully describing all visual elements
- REMEMBER: While maintaining narrative continuity, you must ALWAYS describe every element fully in each image
- To maintain continuity without direct references: Instead of "The clockwork crown from the previous image," write "A detailed clockwork crown with intricate gold and silver gears"

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
