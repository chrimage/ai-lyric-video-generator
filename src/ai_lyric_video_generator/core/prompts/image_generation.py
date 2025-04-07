"""
Prompt template for generating images based on a detailed description.
"""

IMAGE_GENERATION_PROMPT = """
Generate a single, high-quality, visually striking still image based *only* on the following detailed description. This image is for one frame of a lyric video.

--- DESCRIPTION ---
{description}
--- END DESCRIPTION ---

CRITICAL REQUIREMENTS:
1.  **Standalone Image:** Create EXACTLY what is described above. Assume NO context from any other images or descriptions. This image must be fully understandable on its own.
2.  **Completeness:** Include ALL visual elements, styles, colors, themes, and text placements mentioned in the description.
3.  **Aspect Ratio:** Generate the image in a 16:9 aspect ratio (e.g., 1280x720 pixels).
4.  **No Humans/Faces:** Unless explicitly requested and described in detail, avoid depicting realistic human figures or faces. Stylized or abstract representations are acceptable if described.
5.  **Text Readability:** If the description includes incorporating lyric text, ensure it is clearly readable and integrated aesthetically according to the specified style.
6.  **Artistic Style:** Strictly adhere to the artistic style mentioned in the description (e.g., watercolor, neon noir, abstract).

NEGATIVE PROMPTS (AVOID THESE):
- Blurry or out-of-focus images
- Watermarks, signatures, or text unrelated to the description
- Multiple panels or collage-style images (generate only ONE single image)
- Generic or low-effort backgrounds unless specified
- Elements not mentioned in the description
- Assuming context from potential previous images (e.g., "continuing the scene")

ARTISTIC GUIDANCE FOR SENSITIVE CONTENT (If applicable based on description):
- If the description hints at sensitive themes (violence, adult content, etc.), interpret it ARTISTICALLY and ABSTRACTLY.
- Use metaphors, symbolism, color, light, and composition to convey the *emotion* or *essence* without literal or explicit depiction.
- Employ techniques like silhouettes, shadows, suggestive framing, or symbolic objects.
- Transform potentially problematic concepts into visually poetic, broadcast-safe artistic statements.
- Focus on mood and atmosphere.

STRICTLY AVOID generating images containing:
- Gore, blood, wounds, explicit violence, physical harm.
- Macabre or morbid elements (realistic skulls, dead bodies, etc.).
- Disturbing, frightening, or horror content.
- Weapons used threateningly.
- Depictions of suffering or pain.
- Anything violating safety guidelines for general audiences.

Generate the image now based SOLELY on the provided description.
"""
