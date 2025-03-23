"""
Prompt templates for safety and content revisions
"""

SAFER_DESCRIPTION_PROMPT = """
The following image description was flagged by content filters as potentially problematic:

"{original_description}"

{block_reason_text}

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

ABSTRACT_IMAGE_PROMPT = """
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
