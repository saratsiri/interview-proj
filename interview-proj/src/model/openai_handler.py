"""
OpenAI API handler with proper error handling and retry logic
Following OpenAI best practices from 2025 documentation
"""
import time
import random
import logging
from typing import Dict, List, Optional
from openai import OpenAI, RateLimitError
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
                    
                    # Check if it's a quota issue vs rate limit
                    error_str = str(e)
                    if "quota" in error_str.lower() or "insufficient_quota" in error_str.lower():
                        logger.error("❌ OpenAI quota exceeded - need to add billing/upgrade plan")
                        logger.info("💳 Visit https://platform.openai.com/account/billing to upgrade")
                        raise  # Don't retry quota issues
                    
                    if num_retries > max_retries:
                        logger.error(f"❌ Max retries ({max_retries}) exceeded for OpenAI API")
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
                    
                except Exception as e:
                    # Other OpenAI errors, don't retry
                    logger.error(f"❌ OpenAI API error: {e}")
                    raise
                    
        return wrapper
    return decorator


class OpenAIHandler:
    """OpenAI API handler with proper error handling"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        logger.info(f"✅ OpenAI handler initialized with model: {model}")
    
    @retry_with_exponential_backoff(max_retries=3)
    def generate_completion(self, messages: List[Dict], **kwargs) -> Dict:
        """Generate completion with automatic retry on rate limits"""
        logger.info(f"🚀 Making OpenAI API call to {self.model}")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            
            logger.info(f"✅ OpenAI API call successful")
            logger.info(f"📊 Tokens used: {response.usage.total_tokens if response.usage else 'N/A'}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ OpenAI API call failed: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test OpenAI API connection with minimal request"""
        try:
            logger.info("🔍 Testing OpenAI API connection...")
            
            response = self.generate_completion(
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=1,
                temperature=0
            )
            
            logger.info("✅ OpenAI API connection test successful!")
            return True
            
        except RateLimitError as e:
            if "quota" in str(e).lower():
                logger.warning("⚠️ OpenAI quota exceeded - API key would work with billing")
                logger.info("💳 Add billing at: https://platform.openai.com/account/billing")
            else:
                logger.warning("⚠️ OpenAI rate limit - will retry automatically during generation")
            return False
            
        except Exception as e:
            logger.error(f"❌ OpenAI connection test failed: {e}")
            return False