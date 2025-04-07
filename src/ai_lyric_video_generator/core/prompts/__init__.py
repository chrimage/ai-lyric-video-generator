"""
Prompts package for AI Lyric Video Generator
"""
from ai_lyric_video_generator.core.prompts.video_concept import VIDEO_CONCEPT_PROMPT
from ai_lyric_video_generator.core.prompts.image_description import IMAGE_DESCRIPTION_PROMPT
from ai_lyric_video_generator.core.prompts.image_generation import IMAGE_GENERATION_PROMPT
from ai_lyric_video_generator.core.prompts.safety import SAFER_DESCRIPTION_PROMPT, ABSTRACT_IMAGE_PROMPT

__all__ = [
    'VIDEO_CONCEPT_PROMPT',
    'IMAGE_DESCRIPTION_PROMPT',
    'IMAGE_GENERATION_PROMPT',
    'SAFER_DESCRIPTION_PROMPT',
    'ABSTRACT_IMAGE_PROMPT'
]
