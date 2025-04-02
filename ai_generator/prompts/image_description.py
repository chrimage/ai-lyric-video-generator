"""
Prompt template for generating image descriptions based on a structured video concept.
"""

IMAGE_DESCRIPTION_PROMPT = """
You are an AI assistant creating image descriptions for a lyric video for the song "{song_title}" by "{artists}".
Follow the established creative direction meticulously.

--- CREATIVE DIRECTION ---
Visual Style: {visual_style}
Color Palette: {color_palette_desc} (Dominant colors: {color_palette_colors})
Key Themes/Motifs: {key_themes_or_motifs}
Overall Concept: {overall_concept}
--- END CREATIVE DIRECTION ---

IMPORTANT GUIDELINES FOR VISUAL CONTINUITY & STYLE:
1. STRICTLY adhere to the specified Visual Style, Color Palette, and Key Themes/Motifs in EVERY description.
2. This is a sequence of still images shown chronologically. Imply visual progression subtly.
3. For instrumental segments (no lyrics), create atmospheric or transitional scenes that fit the narrative and style, incorporating the Key Themes/Motifs.
4. Ensure each image description makes sense visually and thematically within the overall concept.

Below is a numbered list of segments from the song. Create a detailed image description for EACH numbered segment.

--- SONG SEGMENTS ---
{segments_text}
--- END SONG SEGMENTS ---

For each segment, provide ONLY the image description as a numbered list matching the segment numbers above.

⚠️ ABSOLUTELY CRITICAL REQUIREMENT - SELF-CONTAINED DESCRIPTIONS ⚠️
* Each description MUST be 100% self-contained and understandable in complete isolation.
* The AI generating each image will have NO KNOWLEDGE of any other images or descriptions.
* ❌ CRITICAL ERROR: NEVER use phrases like "from the previous image", "same as before", "continues the scene", "still wearing", "the character", "the object", etc., unless the object/character is FULLY re-described within that same description.
* ❌ CRITICAL ERROR: NEVER reference other images by number or context (e.g., "similar to image 3", "like we saw earlier").
* ❌ CRITICAL ERROR: If a recurring element (e.g., a specific crown, a unique tree) appears, describe it COMPLETELY every single time as if it's the first time. Example: Instead of "The crown again", write "An ornate clockwork crown made of brass gears and glowing blue tubes sits..."
* ❌ CRITICAL ERROR: Avoid using "the" to refer to something not explicitly introduced *within the current description*. Use "a" or descriptive adjectives instead.
* IMAGINE: Each description is given to a different artist who sees only that one description.
* IMAGINE: Each description feeds an independent image generator with no memory.

SPECIFICALLY PROHIBITED PHRASES (WILL CAUSE MAJOR ERRORS):
- "from the previous image", "same as before", "as seen earlier", "continuing the scene", "the [anything] from [any other image]", "still [doing anything]", "once again", "previously", "returning to", "the same [anything]", "again", "mentioned earlier", "now [doing something]", "image #", "in the last/previous frame/scene/image", "consistent with the [anything]"

IMPORTANT INSTRUCTIONS:
- Integrate the specified Visual Style, Color Palette, and Key Themes/Motifs into every description.
- For segments with lyrics, the text MUST be visually incorporated into the scene in a creative way that matches the style (e.g., carved into stone, projected onto fog, formed by stars, part of a digital display). Describe *how* the text appears.
- Fully describe every visual element as if it's being introduced for the first time in each image.
- Use vivid, descriptive language suitable for an image generation model.

HANDLING SENSITIVE LYRICS (Apply Artistic Interpretation):
- If lyrics are provocative, violent, explicit, or adult-themed, DO NOT depict them literally.
- Use sophisticated artistic techniques: metaphors, symbolism, abstract visuals, silhouettes, shadows, creative framing, focus on emotion.
- Transform problematic concepts into visually poetic, artistic interpretations aligned with the overall style and themes.
- STRICTLY AVOID: Gore, blood, wounds, injuries, macabre/morbid imagery (graveyards, coffins, dead bodies, skulls), disturbing/frightening visuals, weapons in threatening contexts, depictions of suffering/pain.
- Instead, for dark themes: Use symbolic representations (withered flowers, broken glass, storms, chains breaking), abstract color schemes (dark blues/purples), weather elements, symbolic objects.
- Think like a creative director for a broadcast-safe music video. Express the *essence* artistically.

Your response must be formatted EXACTLY like this, providing only the numbered descriptions:
1. [Detailed, self-contained image description for segment 1, adhering to style, palette, themes]
2. [Detailed, self-contained image description for segment 2, adhering to style, palette, themes]
...
"""
