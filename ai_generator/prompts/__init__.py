"""
Prompt templates for AI generation
"""
from ai_generator.prompts.video_concept import VIDEO_CONCEPT_PROMPT
from ai_generator.prompts.image_description import IMAGE_DESCRIPTION_PROMPT
from ai_generator.prompts.image_generation import IMAGE_GENERATION_PROMPT
from ai_generator.prompts.safety import SAFER_DESCRIPTION_PROMPT, ABSTRACT_IMAGE_PROMPT

__all__ = [
    'VIDEO_CONCEPT_PROMPT',
    'IMAGE_DESCRIPTION_PROMPT',
    'IMAGE_GENERATION_PROMPT',
    'SAFER_DESCRIPTION_PROMPT',
    'ABSTRACT_IMAGE_PROMPT'
]
