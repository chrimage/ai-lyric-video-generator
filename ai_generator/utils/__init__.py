"""
Utility functions for AI generator, including logging setup.
"""
import time
import random
import textwrap
import logging
import sys
from typing import Callable, Any, Optional

# --- Logging Setup ---
# Check if logger is already configured (e.g., by Flask app)
logger = logging.getLogger('ai_generator')

# Configure only if no handlers are present
if not logger.handlers:
    logger.setLevel(logging.INFO) # Set default level (can be overridden by env var or config)

    # Create handler (console)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO) # Set handler level

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # Add handler to the logger
    logger.addHandler(handler)

    # Prevent propagation to root logger if it has handlers (like Flask's default)
    # logger.propagate = False # Keep propagation for now, might be useful

    logger.info("AI Generator logger configured.")
# --- End Logging Setup ---


def retry_api_call(
        func: Callable, 
        *args, 
        max_retries: int = 8, 
        initial_delay: float = 2.0, 
        max_delay: float = 120.0, 
        **kwargs
    ) -> Any:
    """
    Execute an API call with exponential backoff for retries
    
    Args:
        func: The function to call
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        
    Returns:
        The result of the function call
    """
    retries = 0
    delay = initial_delay
    
    while True:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            retries += 1
            if retries > max_retries:
                logger.error(f"Failed after {max_retries} retries: {e}")
                raise
            
            # Calculate backoff with jitter
            delay = min(delay * 2, max_delay)
            jitter = random.uniform(0.8, 1.2)
            sleep_time = delay * jitter
            
            logger.warning(f"Retry {retries}/{max_retries} after error: {e}. Waiting {sleep_time:.2f}s")
            time.sleep(sleep_time)


def format_text_display(text: str, width: int = 76) -> str:
    """
    Format text with wrapping.

    Args:
        text: The text to format.
        width: The width to wrap at.

    Returns:
        The wrapped text as a single string with newline characters.
    """
    if not isinstance(text, str): # Add basic type check for safety
        logger.warning(f"format_text_display received non-string input: {type(text)}. Returning empty string.")
        return ""
    return textwrap.fill(text, width=width)


def extract_quoted_text(text: str) -> Optional[str]:
    """
    Extract text between single quotes
    
    Args:
        text: Text containing quoted segments
        
    Returns:
        The first quoted segment or None if none found
    """
    if "'" in text and "'" in text:
        try:
            quoted_parts = text.split("'")
            if len(quoted_parts) >= 3:  # Need at least one complete quote
                for i in range(1, len(quoted_parts), 2):
                    if quoted_parts[i].strip():
                        return quoted_parts[i].strip()
        except:
            pass
    return None


def censor_text(text: str) -> str:
    """
    Censor text by replacing middle characters with asterisks
    
    Args:
        text: The text to censor
    
    Returns:
        Censored text
    """
    if not text:
        return ""
        
    words = text.split()
    censored_words = []
    for word in words:
        if len(word) > 3:  # Only censor longer words
            censored_words.append(word[0] + "*" * (len(word) - 2) + word[-1])
        else:
            censored_words.append(word)
    return " ".join(censored_words)
