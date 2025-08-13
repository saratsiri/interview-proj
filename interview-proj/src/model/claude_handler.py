"""
Claude API handler with proper error handling and retry logic
Using Anthropic's Claude API
"""
import time
import random
import logging
from typing import Dict, List, Optional
from anthropic import Anthropic, RateLimitError, APIError
from functools import wraps

logger = logging.getLogger(__name__)

def retry_with_exponential_backoff(
    initial_delay: float = 1,
    exponential_base: float = 2,
    jitter: bool = True,
    max_retries: int = 3,
    max_delay: float = 60
):
    """Decorator to retry function calls with exponential backoff on rate limit errors"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            num_retries = 0
            delay = initial_delay
            
            while True:
                try:
                    return func(*args, **kwargs)
                    
                except RateLimitError as e:
                    num_retries += 1
                    
                    if num_retries > max_retries:
                        logger.error(f"❌ Max retries ({max_retries}) exceeded for Claude API")
                        raise
                    
                    # Calculate delay with jitter
                    if jitter:
                        delay_with_jitter = delay * (0.5 + random.random() * 0.5)
                    else:
                        delay_with_jitter = delay
                    
                    delay_with_jitter = min(delay_with_jitter, max_delay)
                    
                    logger.warning(f"⏳ Rate limit hit, retrying in {delay_with_jitter:.2f}s (attempt {num_retries}/{max_retries})")
                    time.sleep(delay_with_jitter)
                    
                    # Exponential backoff
                    delay *= exponential_base
                    
                except APIError as e:
                    logger.error(f"❌ Claude API error: {e}")
                    raise
                except Exception as e:
                    logger.error(f"❌ Unexpected error: {e}")
                    raise
                    
        return wrapper
    return decorator


class ClaudeHandler:
    """Claude API handler with proper error handling"""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        self.client = Anthropic(api_key=api_key)
        self.model = model
        logger.info(f"✅ Claude handler initialized with model: {model}")
    
    @retry_with_exponential_backoff(max_retries=3)
    def generate_completion(self, messages: List[Dict], **kwargs) -> Dict:
        """Generate completion with automatic retry on rate limits"""
        logger.info(f"🚀 Making Claude API call to {self.model}")
        
        try:
            # Convert messages format for Claude
            # Claude expects a single user message or alternating user/assistant
            if len(messages) == 2 and messages[0].get("role") == "system":
                # System + user message format
                system_message = messages[0]["content"]
                user_message = messages[1]["content"]
                
                response = self.client.messages.create(
                    model=self.model,
                    system=system_message,
                    messages=[{"role": "user", "content": user_message}],
                    max_tokens=kwargs.get("max_tokens", 1000),
                    temperature=kwargs.get("temperature", 0.7)
                )
            else:
                # Direct messages format
                response = self.client.messages.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=kwargs.get("max_tokens", 1000),
                    temperature=kwargs.get("temperature", 0.7)
                )
            
            logger.info(f"✅ Claude API call successful")
            logger.info(f"📊 Input tokens: {response.usage.input_tokens}, Output tokens: {response.usage.output_tokens}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Claude API call failed: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test Claude API connection with minimal request"""
        try:
            logger.info("🔍 Testing Claude API connection...")
            
            response = self.generate_completion(
                messages=[{"role": "user", "content": "Say hello"}],
                max_tokens=10
            )
            
            logger.info("✅ Claude API connection test successful!")
            logger.info(f"📝 Response: {response.content[0].text}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Claude connection test failed: {e}")
            return False