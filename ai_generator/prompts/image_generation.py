"""
Prompt template for generating images
"""

IMAGE_GENERATION_PROMPT = """
Create a high-quality still image for a lyric video with the following description:

{description}

IMPORTANT: This image is completely independent and must make sense on its own without any context from other images. It MUST fully depict everything described in the prompt without relying on or referencing any other images.

CRITICAL REQUIREMENTS:
- Create EXACTLY what is described in the prompt
- Do not assume any knowledge of previous images or scenes
- Treat this as a completely standalone, independent image
- Include all elements mentioned in the description
- This is for a single frame in a lyric video

The image should:
- Be in 16:9 aspect ratio (1280x720 or similar)
- Have high contrast and readability for any text elements
- Be visually striking and suitable for a music video
- No humans or faces should be included
- Contain all visual elements fully described in the prompt above
- Use a consistent artistic style throughout the entire image

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
