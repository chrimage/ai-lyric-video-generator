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
* Each description must be treated as if it will be processed COMPLETELY INDEPENDENTLY without any access to other descriptions
* The AI generating each image will have NO KNOWLEDGE of any other images in the sequence
* ❌ CRITICAL ERROR: NEVER use phrases like "from the previous image", "same as before", "continues the scene", "once again", "still wearing", etc.
* ❌ CRITICAL ERROR: NEVER say "the clockwork crown from the previous image", "the same character as before", "similar to image X", etc.
* ❌ CRITICAL ERROR: NEVER reference other images by their number or mention previous or future images at all
* ❌ CRITICAL ERROR: NEVER reference characters, objects, or elements without fully describing them in each image
* ❌ CRITICAL ERROR: If the same crown, character, or element appears in multiple images, describe it completely each time as if it's the first time it appears
* ❌ CRITICAL ERROR: NEVER use "the" to describe something that hasn't been introduced within this description
* IMAGINE: Each description will be given to a completely different artist who can only see that one description and nothing else
* IMAGINE: I will feed each description into a separate, independent image generator that has no memory or knowledge of any other images
* This is not a storyboard where one image builds off another - each is ENTIRELY self-contained

SPECIFICALLY PROHIBITED PHRASES (WILL CAUSE ERRORS):
- "from the previous image"
- "same as before/earlier"
- "as seen earlier"
- "continuing the scene"
- "the [anything] from [any other image]"
- "still [doing anything]"
- "once again"
- "previously"
- "returning to"
- "the same [anything]"
- "again"
- "mentioned earlier"
- "now [doing something]"
- "image #"
- "in the last/previous frame/scene/image"
- "consistent with the [anything]"

IMPORTANT INSTRUCTIONS:
- For segments with lyrics, the text MUST be visually incorporated into the scene in a creative way
- Fully describe every visual element as if it's being introduced for the first time in each image
- For recurring elements: Instead of "The clockwork crown from before," write "A detailed clockwork crown with intricate gold and silver gears"
- For visual progression, use distinct descriptions that imply a narrative without directly referencing other images
- Concrete example: Instead of "The same forest path, now with moonlight" write "A serene forest path illuminated by silvery moonlight filtering through ancient oak trees"

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
