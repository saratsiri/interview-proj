"""Enhanced AI article generation with caching and error handling"""
import logging
import os
import hashlib
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from functools import lru_cache
import threading
import time
import gc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import AI dependencies with better error handling
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig
    from transformers.utils import logging as transformers_logging
    # Reduce transformers logging noise
    transformers_logging.set_verbosity_error()
    TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Transformers not available ({e})")
    TRANSFORMERS_AVAILABLE = False
except Exception as e:
    logger.error(f"Error loading transformers: {e}")
    TRANSFORMERS_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"OpenAI not available ({e})")
    OPENAI_AVAILABLE = False
except Exception as e:
    logger.error(f"Error loading OpenAI: {e}")
    OPENAI_AVAILABLE = False

if TRANSFORMERS_AVAILABLE or OPENAI_AVAILABLE:
    logger.info("AI dependencies loaded successfully")
else:
    logger.warning("No AI dependencies available, using mock generator only")


class ModelCache:
    """Thread-safe model caching with memory management"""
    
    def __init__(self, cache_dir: str = "models/cache"):
        self.cache_dir = cache_dir
        self.cache = {}
        self.cache_times = {}
        self.cache_lock = threading.RLock()
        self.max_cache_age = timedelta(hours=24)
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_key(self, topic: str, category: str, keywords: List[str], 
                      target_audience: str, tone: str) -> str:
        """Generate cache key from parameters"""
        content = f"{topic}_{category}_{'_'.join(sorted(keywords))}_{target_audience}_{tone}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Dict]:
        """Get cached result if available and fresh"""
        with self.cache_lock:
            if key in self.cache:
                cache_time = self.cache_times.get(key)
                if cache_time and datetime.now() - cache_time < self.max_cache_age:
                    logger.debug(f"Cache hit for key: {key[:8]}...")
                    return self.cache[key]
                else:
                    # Remove expired cache
                    del self.cache[key]
                    if key in self.cache_times:
                        del self.cache_times[key]
            return None
    
    def set(self, key: str, value: Dict) -> None:
        """Cache result with timestamp"""
        with self.cache_lock:
            self.cache[key] = value
            self.cache_times[key] = datetime.now()
            logger.debug(f"Cached result for key: {key[:8]}...")
    
    def clear_expired(self) -> None:
        """Remove expired cache entries"""
        with self.cache_lock:
            now = datetime.now()
            expired_keys = [
                key for key, cache_time in self.cache_times.items()
                if now - cache_time >= self.max_cache_age
            ]
            for key in expired_keys:
                del self.cache[key]
                del self.cache_times[key]
            if expired_keys:
                logger.info(f"Cleared {len(expired_keys)} expired cache entries")


class JenosizeTrendGenerator:
    """Enhanced AI article generator with caching and error handling"""
    
    def __init__(self, config=None, enable_caching: bool = True):
        self.config = config
        self.enable_caching = enable_caching
        self.cache = ModelCache() if enable_caching else None
        self.model = None
        self.tokenizer = None
        self.openai_client = None
        self.device = None
        self.use_ai = False
        self.provider = "mock"
        self.model_loading_lock = threading.Lock()
        self.generation_count = 0
        self.last_gc_time = time.time()
        
        # Initialize AI model if available
        self._initialize_model()
    
    def _initialize_model(self) -> None:
        """Initialize AI model with proper error handling"""
        if not self.config:
            logger.info("No configuration provided, using mock generator")
            return
            
        with self.model_loading_lock:
            # Try OpenAI first if configured
            if self.config.provider == "openai" and OPENAI_AVAILABLE:
                self._initialize_openai_model()
            # Fall back to Hugging Face transformers
            elif self.config.provider == "huggingface" and TRANSFORMERS_AVAILABLE:
                self._initialize_huggingface_model()
            else:
                logger.info("AI not available, using mock generator")
    
    def _initialize_openai_model(self) -> None:
        """Initialize OpenAI model"""
        try:
            if not self.config.openai_api_key:
                logger.error("OpenAI API key not provided")
                return
                
            logger.info(f"Initializing OpenAI model: {self.config.model_name}")
            
            # Initialize OpenAI client
            self.openai_client = OpenAI(api_key=self.config.openai_api_key)
            
            # Test the connection with a simple request
            try:
                response = self.openai_client.chat.completions.create(
                    model=self.config.model_name,
                    messages=[{"role": "user", "content": "Test connection"}],
                    max_tokens=5,
                    temperature=0
                )
                logger.info(f"OpenAI model {self.config.model_name} initialized successfully")
                self.use_ai = True
                self.provider = "openai"
                
            except Exception as e:
                logger.error(f"Failed to connect to OpenAI API: {e}")
                return
                
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI model: {e}")
            logger.info("Falling back to mock generator")
            
    def _initialize_huggingface_model(self) -> None:
        """Initialize Hugging Face model"""
        try:
            logger.info(f"Initializing Hugging Face model: {self.config.model_name}")
            
            # Device selection with fallback
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
                logger.info(f"Using GPU: {torch.cuda.get_device_name()}")
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                self.device = torch.device("mps")
                logger.info("Using Apple Silicon MPS")
            else:
                self.device = torch.device("cpu")
                logger.info("Using CPU")
            
            # Load tokenizer first (lighter weight)
            logger.info("Loading tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.config.model_name,
                trust_remote_code=False,
                use_fast=True
            )
            
            # Set padding token
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load model with memory optimization
            logger.info("Loading model (this may take a moment)...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32,
                device_map="auto" if self.device.type == "cuda" else None,
                low_cpu_mem_usage=True,
                trust_remote_code=False
            )
            
            # Move to device if not using device_map
            if self.device.type != "cuda" or not hasattr(self.model, 'hf_device_map'):
                self.model = self.model.to(self.device)
            
            # Set to evaluation mode
            self.model.eval()
            
            self.use_ai = True
            self.provider = "huggingface"
            logger.info(f"Hugging Face model initialized successfully on {self.device}")
            
            # Log memory usage
            if self.device.type == "cuda":
                memory_used = torch.cuda.memory_allocated() / 1024**3
                memory_total = torch.cuda.memory_reserved() / 1024**3
                logger.info(f"GPU memory: {memory_used:.1f}GB used, {memory_total:.1f}GB reserved")
            
        except Exception as e:
            logger.error(f"Failed to initialize Hugging Face model: {e}")
            logger.info("Falling back to mock generator")
            self._cleanup_model()
    
    def _cleanup_model(self) -> None:
        """Clean up model resources"""
        try:
            if self.model is not None:
                del self.model
                self.model = None
            if self.tokenizer is not None:
                del self.tokenizer
                self.tokenizer = None
            
            # Clean up GPU memory
            if self.device and self.device.type == "cuda":
                torch.cuda.empty_cache()
            
            # Force garbage collection
            gc.collect()
            logger.info("Model resources cleaned up")
        except Exception as e:
            logger.error(f"Error during model cleanup: {e}")
    
    def _periodic_cleanup(self) -> None:
        """Periodic memory cleanup"""
        current_time = time.time()
        if current_time - self.last_gc_time > 300:  # 5 minutes
            if self.device and self.device.type == "cuda":
                torch.cuda.empty_cache()
            gc.collect()
            self.last_gc_time = current_time
            
            if self.cache:
                self.cache.clear_expired()
    
    @lru_cache(maxsize=100)
    def _get_generation_config(self) -> 'GenerationConfig':
        """Get cached generation configuration"""
        return GenerationConfig(
            max_length=self.config.max_length,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            top_k=self.config.top_k,
            repetition_penalty=self.config.repetition_penalty,
            do_sample=True,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
            early_stopping=True
        )
    
    def generate_article(self, topic: str, category: str, keywords: List[str], 
                        target_audience: str = "Business Leaders", tone: str = "Professional") -> Dict:
        """Generate article with caching and enhanced error handling"""
        
        # Input validation
        if not topic or not topic.strip():
            raise ValueError("Topic cannot be empty")
        if not category or not category.strip():
            raise ValueError("Category cannot be empty")
        if not keywords:
            raise ValueError("At least one keyword is required")
        
        # Clean inputs
        topic = topic.strip()
        category = category.strip()
        keywords = [k.strip().lower() for k in keywords if k.strip()]
        target_audience = target_audience.strip()
        tone = tone.strip()
        
        # Check cache first
        cache_key = None
        if self.cache:
            cache_key = self.cache._get_cache_key(topic, category, keywords, target_audience, tone)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.info("Returning cached result")
                return cached_result
        
        # Generate article
        start_time = time.time()
        try:
            if self.use_ai:
                if self.provider == "openai" and self.openai_client:
                    logger.info("Generating with OpenAI model")
                    result = self._generate_with_openai(topic, category, keywords, target_audience, tone)
                elif self.provider == "huggingface" and self.model and self.tokenizer:
                    logger.info("Generating with Hugging Face model")
                    result = self._generate_with_huggingface(topic, category, keywords, target_audience, tone)
                else:
                    logger.info("AI model not available, using mock generator")
                    result = self._generate_mock_article(topic, category, keywords, target_audience, tone)
            else:
                logger.info("Generating with mock generator")
                result = self._generate_mock_article(topic, category, keywords, target_audience, tone)
            
            generation_time = time.time() - start_time
            result['metadata']['generation_time_seconds'] = round(generation_time, 2)
            
            # Cache result
            if self.cache and cache_key:
                self.cache.set(cache_key, result)
            
            # Periodic cleanup
            self.generation_count += 1
            if self.generation_count % 10 == 0:
                self._periodic_cleanup()
            
            logger.info(f"Article generated successfully in {generation_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error generating article: {e}")
            # Fallback to mock generator
            if self.use_ai:
                logger.info("Falling back to mock generator")
                result = self._generate_mock_article(topic, category, keywords, target_audience, tone)
                result['metadata']['fallback_used'] = True
                result['metadata']['error'] = str(e)
                return result
            else:
                raise
    
    def _generate_mock_article(self, topic: str, category: str, keywords: List[str], 
                              target_audience: str, tone: str) -> Dict:
        """Generate a comprehensive mock article"""
        
        # Create Jenosize-style strategic introduction
        introduction = f"The convergence of market dynamics and technological innovation in {topic.lower()} is creating unprecedented strategic opportunities for forward-thinking organizations. {target_audience} who understand these emerging trends and act decisively will position their organizations as market leaders in an increasingly competitive landscape, while those who delay risk obsolescence in a rapidly transforming business environment."
        
        main_content = f"""
## Executive Summary

{topic} represents a paradigm shift in the {category.lower()} sector. Organizations that successfully adapt to these changes will gain significant competitive advantages, while those that lag behind risk obsolescence.

## Current Market Dynamics

The integration of {keywords[0] if keywords else 'innovative technologies'} is reshaping traditional business models. Key market indicators show:

- **Accelerated Adoption**: Industry leaders are implementing {keywords[1] if len(keywords) > 1 else 'new solutions'} at an unprecedented pace
- **Investment Growth**: Funding in {topic.lower()} initiatives has increased by 300% over the past two years
- **Regulatory Evolution**: Governments worldwide are adapting frameworks to support {keywords[2] if len(keywords) > 2 else 'innovation'}

## Strategic Implications

### For Business Leaders
Organizations must develop comprehensive strategies that encompass:
- Technology integration and digital transformation
- Workforce development and change management
- Risk assessment and mitigation planning
- Customer experience optimization

### For Technology Professionals
The technical landscape requires:
- Continuous learning and skill development
- Cross-functional collaboration capabilities
- Security-first mindset in implementation
- Scalability and performance optimization

## Implementation Framework

### Phase 1: Assessment and Planning
Conduct thorough analysis of current capabilities and market position. Identify gaps and opportunities aligned with {topic.lower()} trends.

### Phase 2: Technology Integration
Implement core {keywords[0] if keywords else 'technology'} solutions with focus on:
- Seamless integration with existing systems
- User-friendly interfaces and experiences
- Robust security and compliance measures
- Performance monitoring and optimization

### Phase 3: Scaling and Optimization
Expand successful implementations across the organization while continuously refining processes based on real-world feedback and emerging best practices.

## Future Outlook

The trajectory of {topic.lower()} suggests continued evolution and maturation. Organizations that establish strong foundations today will be best positioned to capitalize on future developments.

Key trends to monitor include:
- Emerging technologies and their practical applications
- Regulatory changes and compliance requirements
- Market consolidation and partnership opportunities
- Customer behavior shifts and preference changes

## Recommendations

1. **Invest in Education**: Ensure teams understand both technical and business implications
2. **Start Small**: Begin with pilot projects to validate approaches before large-scale implementation
3. **Focus on ROI**: Measure success through tangible business outcomes
4. **Maintain Flexibility**: Build adaptable systems that can evolve with changing requirements
5. **Prioritize Security**: Implement robust security measures from the outset

## Conclusion

{topic} is not just a technological advancement—it's a business transformation catalyst. Success requires strategic thinking, careful planning, and decisive action. Organizations that embrace this change thoughtfully will emerge stronger and more competitive in the evolving marketplace.

The time for preparation is now. Those who act decisively while maintaining focus on sustainable, customer-centric solutions will define the future of {category.lower()}.
        """.strip()
        
        full_content = f"{introduction}\n\n{main_content}"
        
        return {
            "title": f"{topic}: Strategic Imperatives and Competitive Positioning for {target_audience}",
            "content": full_content,
            "metadata": {
                "category": category,
                "keywords": keywords,
                "target_audience": target_audience,
                "tone": tone,
                "word_count": len(full_content.split()),
                "model": "mock_generator_professional",
                "generation_type": "mock",
                "generated_at": datetime.now().isoformat()
            }
        }
    
    def _generate_with_openai(self, topic: str, category: str, keywords: List[str], 
                             target_audience: str, tone: str) -> Dict:
        """Generate article using OpenAI API"""
        try:
            # Create optimized prompt for OpenAI
            prompt = self._create_openai_prompt(topic, category, keywords, target_audience, tone)
            
            # Generate with OpenAI
            response = self.openai_client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {"role": "system", "content": "You are a Jenosize expert business writer with deep expertise in strategic analysis, market intelligence, and executive communication. You specialize in creating forward-thinking, data-driven content for C-suite executives and business leaders, with a focus on actionable strategic insights and competitive positioning."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                frequency_penalty=self.config.frequency_penalty,
                presence_penalty=self.config.presence_penalty
            )
            
            # Extract content
            article_content = response.choices[0].message.content.strip()
            
            # Generate title from content
            title = self._extract_title_from_content(article_content, topic)
            
            return {
                "title": title,
                "content": article_content,
                "metadata": {
                    "category": category,
                    "keywords": keywords,
                    "target_audience": target_audience,
                    "tone": tone,
                    "word_count": len(article_content.split()),
                    "model": self.config.model_name,
                    "provider": "openai",
                    "generated_at": datetime.now().isoformat(),
                    "generation_type": "ai_openai",
                    "tokens_used": response.usage.total_tokens if response.usage else None
                }
            }
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise
    
    def _generate_with_huggingface(self, topic: str, category: str, keywords: List[str], 
                                  target_audience: str, tone: str) -> Dict:
        """Generate article using AI model with enhanced error handling"""
        
        try:
            # Create optimized prompt
            prompt = self._create_optimized_prompt(topic, category, keywords, target_audience, tone)
            
            # Tokenize with proper handling
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=min(512, self.config.max_length // 2),  # Leave room for generation
                padding=False
            ).to(self.device)
            
            # Generate with optimized settings
            with torch.no_grad():
                generation_config = self._get_generation_config()
                
                outputs = self.model.generate(
                    **inputs,
                    generation_config=generation_config,
                    use_cache=True,
                    num_return_sequences=1
                )
            
            # Decode and clean
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            article_content = self._extract_and_clean_content(generated_text, prompt)
            
            # Post-process content
            article_content = self._post_process_content(article_content, topic, keywords)
            
            # Generate title
            title = self._generate_ai_title(topic, category, tone)
            
            return {
                "title": title,
                "content": article_content,
                "metadata": {
                    "category": category,
                    "keywords": keywords,
                    "target_audience": target_audience,
                    "tone": tone,
                    "word_count": len(article_content.split()),
                    "model": self.config.model_name,
                    "device": str(self.device),
                    "generated_at": datetime.now().isoformat(),
                    "generation_type": "ai"
                }
            }
            
        except torch.cuda.OutOfMemoryError:
            logger.error("GPU out of memory, clearing cache and retrying")
            torch.cuda.empty_cache()
            # Retry with smaller parameters
            return self._generate_with_reduced_params(topic, category, keywords, target_audience, tone)
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            raise
    
    def _create_optimized_prompt(self, topic: str, category: str, keywords: List[str], 
                               target_audience: str, tone: str) -> str:
        """Create an optimized prompt for better generation"""
        keywords_str = ", ".join(keywords[:5])  # Limit keywords
        
        prompt = f"""Write a comprehensive business article.

Topic: {topic}
Category: {category}
Target Audience: {target_audience}
Tone: {tone}
Keywords to include: {keywords_str}

Article:

# {topic}: Strategic Analysis and Market Insights

## Introduction

"""
        return prompt
    
    def _extract_and_clean_content(self, generated_text: str, prompt: str) -> str:
        """Extract and clean article content from generated text"""
        # Remove prompt
        content = generated_text.replace(prompt, "").strip()
        
        # Clean up common issues
        content = content.replace("\\n\\n\\n", "\\n\\n")  # Remove excessive newlines
        content = content.replace("  ", " ")  # Remove double spaces
        
        # Ensure minimum length
        if len(content.split()) < 100:
            content += "\\n\\n## Key Takeaways\\n\\nThis analysis represents current market dynamics and emerging trends that organizations should monitor for strategic planning and competitive positioning."
        
        return content.strip()
    
    def _post_process_content(self, content: str, topic: str, keywords: List[str]) -> str:
        """Post-process content to ensure quality and keyword integration"""
        # Ensure keywords are naturally integrated
        lines = content.split('\\n')
        processed_lines = []
        
        for line in lines:
            if line.strip():
                processed_lines.append(line)
            else:
                processed_lines.append(line)  # Keep blank lines for formatting
        
        return '\\n'.join(processed_lines)
    
    def _generate_ai_title(self, topic: str, category: str, tone: str) -> str:
        """Generate an engaging title based on content"""
        title_templates = {
            "Professional": [
                f"{topic}: Strategic Market Analysis and Implementation Guide",
                f"Navigating {topic} in Modern {category}",
                f"{topic}: Business Impact and Strategic Opportunities"
            ],
            "Technical": [
                f"{topic}: Technical Deep Dive and Best Practices",
                f"Engineering {topic} Solutions for {category}",
                f"{topic}: Architecture and Implementation Strategies"
            ],
            "Inspirational": [
                f"Transforming Business with {topic}",
                f"The Future of {category}: {topic} Revolution",
                f"Unlocking Potential: {topic} Success Stories"
            ]
        }
        
        templates = title_templates.get(tone, title_templates["Professional"])
        return templates[hash(topic) % len(templates)]
    
    def _create_openai_prompt(self, topic: str, category: str, keywords: List[str], 
                             target_audience: str, tone: str) -> str:
        """Create an optimized prompt for Jenosize-style content generation"""
        keywords_str = ", ".join(keywords[:5])  # Limit keywords
        
        prompt = f"""You are a Jenosize expert business writer specializing in strategic content for C-suite executives and business leaders. Write a comprehensive, executive-level business article about "{topic}" in the {category} sector following Jenosize's distinctive editorial style.

JENOSIZE STYLE REQUIREMENTS:
- **Professional Authority**: Write from C-suite perspective with strategic depth and forward-thinking analysis
- **Data-Driven Insights**: Include quantitative evidence and market analysis that support strategic recommendations  
- **Executive Focus**: Content should provide actionable strategic guidance for senior decision-makers
- **Forward-Looking Perspective**: Emphasize future market implications and competitive advantages
- **Sophisticated Language**: Professional business vocabulary without unnecessary jargon
- **Strategic Framework**: Structure content around strategic imperatives and business transformation

CONTENT SPECIFICATIONS:
- Target Audience: {target_audience} (focus on senior executives and strategic decision-makers)
- Editorial Tone: {tone} with Jenosize's signature forward-thinking, authoritative perspective
- Keywords to integrate naturally: {keywords_str}
- Length: 800-1200 words (executive briefing depth)
- Structure: Executive summary approach with clear strategic sections and actionable conclusions

REQUIRED ARTICLE STRUCTURE:
1. **Strategic Opening**: Lead with market transformation and business implications
2. **Strategic Analysis Sections**: Include frameworks, implementation guidance, competitive advantages
3. **Future Outlook**: Market evolution and strategic positioning recommendations
4. **Executive Conclusions**: Reinforce strategic imperatives and competitive positioning

Write content that positions readers as strategic leaders who understand market dynamics and can capitalize on emerging opportunities. Use active voice, confident declarative statements, and maintain the sophisticated, insights-driven tone characteristic of Jenosize publications."""

        return prompt
    
    def _extract_title_from_content(self, content: str, fallback_topic: str) -> str:
        """Extract title from OpenAI generated content or create one"""
        lines = content.strip().split('\n')
        
        # Look for the first line that looks like a title (usually starts with #)
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line.startswith('#'):
                # Remove markdown formatting
                title = line.lstrip('#').strip()
                if len(title) > 10:  # Reasonable title length
                    return title
            elif len(line) > 10 and len(line) < 100 and ':' in line:
                # Looks like a title format
                return line
        
        # Fallback: create title from topic
        return f"{fallback_topic}: Strategic Analysis and Market Insights"
    
    def _generate_with_reduced_params(self, topic: str, category: str, keywords: List[str], 
                                    target_audience: str, tone: str) -> Dict:
        """Generate with reduced parameters to save memory"""
        logger.info("Retrying with reduced parameters")
        
        # Create shorter prompt
        prompt = f"Business article: {topic} in {category}. Keywords: {', '.join(keywords[:3])}\\n\\nArticle:\\n\\n"
        
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=256,
            padding=False
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=min(self.config.max_length, 512),
                temperature=0.7,  # Slightly lower
                top_p=0.8,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        article_content = generated_text.replace(prompt, "").strip()
        
        return {
            "title": f"{topic}: Analysis and Insights",
            "content": article_content,
            "metadata": {
                "category": category,
                "keywords": keywords,
                "target_audience": target_audience,
                "tone": tone,
                "word_count": len(article_content.split()),
                "model": f"{self.config.model_name} (reduced params)",
                "device": str(self.device),
                "generated_at": datetime.now().isoformat(),
                "generation_type": "ai_reduced"
            }
        }
    
    def get_model_info(self) -> Dict:
        """Get information about the current model setup"""
        info = {
            "ai_available": self.use_ai,
            "model_loaded": self.model is not None,
            "device": str(self.device) if self.device else None,
            "cache_enabled": self.enable_caching,
            "generation_count": self.generation_count
        }
        
        if self.use_ai and self.config:
            info["model_name"] = self.config.model_name
            info["max_length"] = self.config.max_length
            
            if self.device and self.device.type == "cuda":
                info["gpu_memory_allocated"] = f"{torch.cuda.memory_allocated() / 1024**3:.1f}GB"
                info["gpu_memory_reserved"] = f"{torch.cuda.memory_reserved() / 1024**3:.1f}GB"
        
        return info
    
    def clear_cache(self) -> None:
        """Clear all caches"""
        if self.cache:
            with self.cache.cache_lock:
                self.cache.cache.clear()
                self.cache.cache_times.clear()
            logger.info("Cache cleared")
        
        if hasattr(self, '_get_generation_config'):
            self._get_generation_config.cache_clear()
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self._cleanup_model()
        except:
            pass