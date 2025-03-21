"""
API utility functions for handling retries, rate limits, and error handling
"""
import time
import random
import logging
from typing import Callable, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('lyric_videos.log')
    ]
)
logger = logging.getLogger(__name__)

def api_call_with_backoff(func: Callable, *args, max_retries: int = 5, 
                         initial_delay: float = 2.0, max_delay: float = 60.0, 
                         jitter_factor: float = 0.2, **kwargs) -> Optional[Any]:
    """
    Makes an API call with exponential backoff for rate limiting and network issues
    
    Args:
        func: The API function to call
        *args: Arguments to pass to the function
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        jitter_factor: Random jitter factor to add to delay (0.0-1.0)
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the API call or None if all retries fail
    """
    delay = initial_delay
    retries = 0
    
    # Common error messages indicating rate limits or resource exhaustion
    rate_limit_indicators = [
        "rate limit", "quota", "429", "too many requests", 
        "resource exhausted", "capacity", "throttle",
        "limit exceeded", "try again later", "server busy"
    ]
    
    # Network or temporary error indicators
    temporary_error_indicators = [
        "connection", "timeout", "timed out", "reset", "temporary",
        "server error", "503", "502", "504", "network", "unavailable"
    ]
    
    # Content filter or safety indicators
    content_filter_indicators = [
        "content filter", "filtered", "policy violation", "prohibited",
        "unsafe content", "inappropriate", "moderation", "violates policies",
        "blocked by safety", "safety settings", "safety system"
    ]
    
    while retries < max_retries:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            error_type = type(e).__name__
            
            # If this is the last retry, re-raise the exception
            if retries == max_retries - 1:
                logger.error(f"Failed after {retries+1} attempts: {error_type}: {error_str}")
                return None
                
            # Check if this is a rate limit or resource exhaustion error
            is_rate_limit = any(indicator in error_str for indicator in rate_limit_indicators)
            
            # Check if this is a network or temporary error
            is_temporary = any(indicator in error_str for indicator in temporary_error_indicators)
            
            # Check if this is a content filter block
            is_content_filtered = any(indicator in error_str for indicator in content_filter_indicators)
            
            # Special handling for content filter blocks
            if is_content_filtered:
                logger.warning(f"Content filter triggered: {error_type}: {error_str}")
                print(f"Content filter blocked generation: {error_type}")
                # Raise a specialized exception to communicate the content filter issue
                # This allows calling code to detect this specific case
                from types import SimpleNamespace
                content_filter_error = SimpleNamespace()
                content_filter_error.is_content_filtered = True
                content_filter_error.original_error = e
                content_filter_error.error_message = error_str
                return content_filter_error
            
            # Determine if we should retry
            if is_rate_limit or is_temporary:
                # Calculate backoff with jitter
                jitter = random.uniform(1.0 - jitter_factor, 1.0 + jitter_factor)
                sleep_time = min(delay * jitter, max_delay)
                
                logger.warning(f"API call failed (retry {retries+1}/{max_retries}): {error_type}. "
                              f"Waiting {sleep_time:.1f}s before retrying...")
                print(f"API call failed (retry {retries+1}/{max_retries}): {error_type}. "
                     f"Waiting {sleep_time:.1f}s before retrying...")
                
                time.sleep(sleep_time)
                
                # Exponential backoff
                delay = min(delay * 2, max_delay)
                retries += 1
            else:
                # Not a retriable error, re-raise
                logger.error(f"Non-retriable error: {error_type}: {error_str}")
                return None
    
    logger.error(f"API call failed after maximum retries ({max_retries})")
    return None