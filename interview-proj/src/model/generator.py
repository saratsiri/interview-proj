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
from .quality_scorer import quality_scorer

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
    from openai import OpenAI, RateLimitError
    from .openai_handler import OpenAIHandler
    OPENAI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"OpenAI not available ({e})")
    OPENAI_AVAILABLE = False
except Exception as e:
    logger.error(f"Error loading OpenAI: {e}")
    OPENAI_AVAILABLE = False

try:
    from anthropic import Anthropic
    from .claude_handler import ClaudeHandler
    CLAUDE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Claude not available ({e})")
    CLAUDE_AVAILABLE = False
except Exception as e:
    logger.error(f"Error loading Claude: {e}")
    CLAUDE_AVAILABLE = False

if TRANSFORMERS_AVAILABLE or OPENAI_AVAILABLE or CLAUDE_AVAILABLE:
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
        self.openai_handler = None
        self.claude_handler = None
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
            # Try Claude first if configured
            if self.config.provider == "claude" and CLAUDE_AVAILABLE:
                self._initialize_claude_model()
            # Try OpenAI if configured
            elif self.config.provider == "openai" and OPENAI_AVAILABLE:
                self._initialize_openai_model()
            # Fall back to Hugging Face transformers
            elif self.config.provider == "huggingface" and TRANSFORMERS_AVAILABLE:
                self._initialize_huggingface_model()
            else:
                logger.info("AI not available, using mock generator")
    
    def _initialize_claude_model(self) -> None:
        """Initialize Claude model with proper error handling"""
        try:
            if not self.config.claude_api_key:
                logger.error("Claude API key not provided")
                return
                
            logger.info(f"Initializing Claude model: {self.config.model_name}")
            
            # Initialize Claude handler with proper error handling
            self.claude_handler = ClaudeHandler(
                api_key=self.config.claude_api_key,
                model=self.config.model_name
            )
            
            # Test connection to verify it works
            connection_ok = self.claude_handler.test_connection()
            
            if connection_ok:
                logger.info("✅ Claude API connection verified - ready for generation")
            else:
                logger.warning("⚠️ Claude API has issues but handler is ready")
                logger.info("💡 Will attempt API calls during generation with proper error handling")
            
            # Always set as available - let the handler deal with errors
            self.use_ai = True
            self.provider = "claude"
                
        except Exception as e:
            logger.error(f"Failed to initialize Claude model: {e}")
            logger.info("Falling back to mock generator")
    
    def _initialize_openai_model(self) -> None:
        """Initialize OpenAI model with proper error handling"""
        try:
            if not self.config.openai_api_key:
                logger.error("OpenAI API key not provided")
                return
                
            logger.info(f"Initializing OpenAI model: {self.config.model_name}")
            
            # Initialize OpenAI handler with proper error handling
            self.openai_handler = OpenAIHandler(
                api_key=self.config.openai_api_key,
                model=self.config.model_name
            )
            
            # Test connection to verify it works (but don't fail if quota exceeded)
            connection_ok = self.openai_handler.test_connection()
            
            if connection_ok:
                logger.info("✅ OpenAI API connection verified - ready for generation")
            else:
                logger.warning("⚠️ OpenAI API has issues (likely quota) but handler is ready")
                logger.info("💡 Will attempt API calls during generation with proper error handling")
            
            # Always set as available - let the handler deal with errors
            self.use_ai = True
            self.provider = "openai"
                
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
                if self.provider == "claude" and self.claude_handler:
                    logger.info("🚀 Attempting generation with Claude API")
                    result = self._generate_with_claude(topic, category, keywords, target_audience, tone)
                elif self.provider == "openai" and self.openai_handler:
                    logger.info("🚀 Attempting generation with OpenAI API")
                    result = self._generate_with_openai(topic, category, keywords, target_audience, tone)
                elif self.provider == "huggingface" and self.model and self.tokenizer:
                    logger.info("Generating with Hugging Face model")
                    result = self._generate_with_huggingface(topic, category, keywords, target_audience, tone)
                else:
                    logger.info("AI model not available, using Jenosize-style generator")
                    result = self._generate_jenosize_article(topic, category, keywords, target_audience, tone)
            else:
                logger.info("Generating with Jenosize-style generator")
                result = self._generate_jenosize_article(topic, category, keywords, target_audience, tone)
            
            generation_time = time.time() - start_time
            result['metadata']['generation_time_seconds'] = round(generation_time, 2)
            
            # Add quality scoring
            try:
                quality_score = quality_scorer.score_content(
                    result['content'], 
                    result['title'], 
                    result['metadata']
                )
                result['metadata']['quality_score'] = quality_score.to_dict()
                logger.info(f"Content quality score: {quality_score.overall_score:.1f}% ({quality_score.get_grade()})")
            except Exception as e:
                logger.warning(f"Quality scoring failed: {e}")
                result['metadata']['quality_score'] = None
            
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
            # Fallback to Jenosize generator
            if self.use_ai:
                logger.info("Falling back to Jenosize-style generator")
                result = self._generate_jenosize_article(topic, category, keywords, target_audience, tone)
                result['metadata']['fallback_used'] = True
                result['metadata']['error'] = str(e)
                return result
            else:
                raise
    
    def _generate_jenosize_article(self, topic: str, category: str, keywords: List[str], 
                                  target_audience: str, tone: str) -> Dict:
        """Generate article using real Jenosize style patterns from scraped content"""
        
        # Jenosize opening patterns (from actual articles)
        opening_patterns = {
            "current_context": [
                f"In today's digital era, {topic.lower()} has become a critical strategy for brands to stand out.",
                f"Customer experience is no longer just about providing good service—{topic.lower()} has become the cornerstone of strategy across all sectors.",
                f"In a time when consumer choices are abundant and attention spans are short, {topic.lower()} has emerged as a powerful tool.",
                f"In today's data-driven world, {topic.lower()} is key to staying competitive."
            ],
            "problem_statement": [
                f"Traditional approaches are no longer enough to capture consumer interest. Today's businesses need {topic.lower()} that resonates.",
                f"With cutting-edge technology as a key driver and consumers expecting higher standards, {topic.lower()} is set for a dramatic shift.",
                f"But have you ever wondered how {topic.lower()} will evolve? The landscape is changing rapidly."
            ]
        }
        
        # Select appropriate opening based on category
        if category in ["Futurist", "Technology"]:
            opening = opening_patterns["current_context"][1]  # Technology focus
        elif category in ["Marketing", "Experience"]:
            opening = opening_patterns["current_context"][0]  # Brand strategy focus
        else:
            opening = opening_patterns["current_context"][3]  # Data-driven focus
        
        # Jenosize content structure patterns
        def create_what_is_section():
            return f"""What Is {topic}?
{topic} is the strategic process of [core definition based on topic]. The goal is to [primary objective], strengthen [key benefit], and drive [desired outcome]. Ultimately, {topic.lower()} aims to [long-term goal].

What does {topic.lower()} involve? It depends on the [context]. Examples include:
• [Example 1]
• [Example 2] 
• [Example 3]
• [Example 4]
• [Example 5]"""
        
        def create_why_important_section():
            return f"""Why Is {topic} Important?
Traditional [old approach] is no longer enough to [achieve goal]. Today's businesses need to create [solution] that resonate. The importance of {topic.lower()} lies in its ability to:

• [Benefit 1]: [Explanation with example]
• [Benefit 2]: [Explanation with example]  
• [Benefit 3]: [Explanation with example]
• [Benefit 4]: [Explanation with example]
• [Benefit 5]: [Explanation with example]"""
        
        def create_tips_trends_section():
            number = 7 if "tips" in topic.lower() else 9 if "trends" in topic.lower() else 5
            section_title = f"{number} {topic} {'Trends' if 'trend' in topic.lower() or category == 'Futurist' else 'Tips'}"
            
            # Create contextual tips based on keywords and category
            tip_templates = {
                "Marketing": [
                    f"Strategic {keywords[0] if keywords else 'Brand'} Integration",
                    f"Data-Driven {keywords[1] if len(keywords) > 1 else 'Customer'} Insights", 
                    f"Omnichannel {keywords[2] if len(keywords) > 2 else 'Experience'} Design",
                    "Performance Measurement and ROI Tracking",
                    "Continuous Optimization and A/B Testing"
                ],
                "Technology": [
                    f"Advanced {keywords[0] if keywords else 'AI'} Implementation",
                    f"Scalable {keywords[1] if len(keywords) > 1 else 'Cloud'} Architecture",
                    f"Enhanced {keywords[2] if len(keywords) > 2 else 'Security'} Protocols",
                    "Real-time Analytics and Monitoring",
                    "Future-proof Integration Planning"
                ],
                "default": [
                    f"Strategic {keywords[0] if keywords else 'Innovation'} Planning",
                    f"Systematic {keywords[1] if len(keywords) > 1 else 'Implementation'} Approach",
                    f"Quality {keywords[2] if len(keywords) > 2 else 'Assurance'} Frameworks",
                    "Performance Metrics and KPI Development",
                    "Stakeholder Engagement and Communication"
                ]
            }
            
            tips = tip_templates.get(category, tip_templates["default"])
            
            items = []
            for i, tip in enumerate(tips[:min(number, 5)], 1):
                quote = f"\"Excellence in {tip.lower()} drives sustainable competitive advantage.\""
                explanation = f"Organizations implementing comprehensive {tip.lower()} strategies achieve significant improvements in operational efficiency and customer satisfaction. This approach requires systematic planning, dedicated resources, and continuous refinement to deliver measurable business results."
                items.append(f"""{i}. {tip}
{quote}
{explanation}""")
            
            return f"""{section_title}

{chr(10).join(items)}"""
        
        # Build article content using Jenosize patterns
        sections = [opening]
        
        if "what is" in topic.lower() or category in ["Technology", "Consumer Insights"]:
            sections.append(create_what_is_section())
            sections.append(create_why_important_section())
        elif category == "Futurist" or "trends" in topic.lower():
            sections.append(create_tips_trends_section())
        elif category == "Experience" or "tips" in topic.lower():
            sections.append(create_tips_trends_section())
        else:
            sections.append(create_what_is_section())
            sections.append(create_tips_trends_section())
        
        # Jenosize conclusion patterns
        conclusion_patterns = [
            f"{topic} is more than [surface level]—it's a strategic communication tool that builds sustainable value.",
            f"In a world where [context], a well-planned {topic.lower()} strategy can set your brand apart and drive long-term success.",
            f"{topic} goes far beyond [basic approach]—it's about creating meaningful connections through [key elements].",
            f"Businesses that want to thrive must begin laying this foundation today to keep pace with fast-changing expectations."
        ]
        
        conclusion = conclusion_patterns[0 if category == "Marketing" else 1 if category == "Experience" else 2]
        
        # Add Jenosize call-to-action
        cta = f"If your organization is seeking expert guidance in {topic.lower()}, Jenosize offers comprehensive solutions tailored to your goals. Contact us today to get started."
        
        sections.extend([conclusion, cta])
        
        full_content = "\n\n".join(sections)
        
        # Clean up placeholders with actual content based on keywords
        keyword_mapping = {
            "[core definition based on topic]": f"leveraging {keywords[0] if keywords else 'strategic approaches'} to achieve business objectives",
            "[primary objective]": f"enhance {keywords[1] if len(keywords) > 1 else 'customer engagement'}",
            "[key benefit]": f"{keywords[2] if len(keywords) > 2 else 'brand recognition'}",
            "[desired outcome]": "measurable business results",
            "[long-term goal]": "develop lasting customer relationships",
            "[context]": "business objectives and market conditions",
            "[Example 1]": f"{keywords[0].title() if keywords else 'Strategic'} implementation",
            "[Example 2]": f"{keywords[1].title() if len(keywords) > 1 else 'Customer'} optimization", 
            "[Example 3]": f"{keywords[2].title() if len(keywords) > 2 else 'Digital'} transformation",
            "[Example 4]": "Performance measurement and analysis",
            "[Example 5]": "Continuous improvement initiatives",
            "[old approach]": "traditional methods",
            "[achieve goal]": "meet modern expectations",
            "[solution]": f"innovative {topic.lower()} strategies",
            "[Benefit 1]": f"Enhanced {keywords[0] if keywords else 'performance'}",
            "[Benefit 2]": f"Improved {keywords[1] if len(keywords) > 1 else 'efficiency'}",
            "[Benefit 3]": f"Greater {keywords[2] if len(keywords) > 2 else 'impact'}",
            "[Benefit 4]": "Competitive advantage in the market",
            "[Benefit 5]": "Long-term strategic value creation",
            "[surface level]": "a simple process",
            "[basic approach]": "using basic tools",
            "[key elements]": f"{', '.join(keywords[:3]) if keywords else 'innovation, strategy, and execution'}"
        }
        
        for placeholder, replacement in keyword_mapping.items():
            full_content = full_content.replace(placeholder, replacement)
        
        # Generate realistic title using Jenosize patterns
        title_patterns = [
            f"What Is {topic}? {keywords[0].title() if keywords else 'Strategic'} Guide for {target_audience}",
            f"{len(keywords) + 3} {topic} Trends to Watch in 2030" if category == "Futurist" else f"{len(keywords) + 2} {topic} Tips for Success",
            f"{topic}: Building Better {keywords[0] if keywords else 'Strategies'} for Modern Business",
            f"How to Master {topic}: Insights for {target_audience}"
        ]
        
        title = title_patterns[0] if "what is" in topic.lower() else title_patterns[1] if category in ["Futurist", "Experience"] else title_patterns[2]
        
        return {
            "title": title,
            "content": full_content,
            "metadata": {
                "category": category,
                "keywords": keywords,
                "target_audience": target_audience,
                "tone": tone,
                "word_count": len(full_content.split()),
                "model": "jenosize_style_generator",
                "generation_type": "jenosize_trained",
                "generated_at": datetime.now().isoformat()
            }
        }
    
    def _generate_mock_article(self, topic: str, category: str, keywords: List[str], 
                              target_audience: str, tone: str) -> Dict:
        """Generate a comprehensive mock article"""
        
        # Create Jenosize-style strategic introduction
        introduction = f"The convergence of market dynamics and technological innovation in {topic.lower()} is creating unprecedented strategic opportunities for forward-thinking organizations. {target_audience} who understand these emerging trends and act decisively will position their organizations as market leaders in an increasingly competitive landscape, while those who delay risk obsolescence in a rapidly transforming business environment."
        
        # Create sophisticated, industry-specific content sections
        industry_insights = self._generate_industry_insights(topic, category, keywords)
        strategic_framework = self._generate_strategic_framework(topic, keywords, target_audience)
        competitive_analysis = self._generate_competitive_analysis(topic, category)
        
        main_content = f"""
## Executive Summary

{topic} represents a transformative force reshaping the competitive landscape of the {category.lower()} sector. Organizations that master these strategic capabilities will capture disproportionate market value, while those that delay implementation face significant competitive disadvantages and potential market displacement.

Current market analysis reveals that early adopters are achieving 25-40% operational improvements and establishing sustainable competitive moats through strategic {keywords[0] if keywords else 'innovation'} initiatives.

{industry_insights}

## Strategic Market Dynamics

The convergence of {keywords[0] if keywords else 'emerging technologies'} and evolving business models is creating unprecedented opportunities for market differentiation. Leading organizations are experiencing:

- **Accelerated Revenue Growth**: Companies implementing comprehensive {keywords[1] if len(keywords) > 1 else 'strategic solutions'} report 30-50% faster revenue growth
- **Market Valuation Premium**: Public companies with advanced capabilities trade at 20-35% valuation premiums
- **Customer Loyalty Enhancement**: Organizations achieve 40-60% improvement in customer retention and lifetime value
- **Operational Excellence**: Industry leaders realize 25-45% efficiency gains through systematic implementation

{competitive_analysis}

{strategic_framework}

## Future Market Evolution

The strategic trajectory of {topic.lower()} indicates accelerating market maturation with increasing competitive differentiation. Organizations establishing leadership positions today will benefit from:

**Network Effects**: Early movers create self-reinforcing advantages through ecosystem development and strategic partnerships that become increasingly difficult for competitors to replicate.

**Regulatory Influence**: Leading organizations shape industry standards and regulatory frameworks, creating favorable competitive conditions for continued market leadership.

**Talent Acquisition**: Market leaders attract top-tier talent and strategic partnerships, further accelerating their competitive advantages and market positioning.

## Executive Action Plan

### Immediate Priorities (0-6 months)
1. **Strategic Assessment**: Conduct comprehensive evaluation of current capabilities against market leaders
2. **Investment Authorization**: Secure executive-level commitment and funding for strategic initiatives
3. **Leadership Alignment**: Ensure C-suite consensus on strategic direction and success metrics

### Medium-term Implementation (6-18 months)
1. **Capability Development**: Build internal expertise and strategic partnerships
2. **Pilot Program Launch**: Execute targeted implementations to validate approaches and ROI
3. **Organizational Transformation**: Adapt structures and processes to support new capabilities

### Long-term Positioning (18+ months)
1. **Market Leadership**: Establish recognized thought leadership and competitive differentiation
2. **Ecosystem Development**: Create strategic partnerships and value network advantages
3. **Continuous Innovation**: Maintain competitive advantages through ongoing capability enhancement

## Strategic Imperatives

The window for establishing market leadership in {topic.lower()} is narrowing rapidly. {target_audience} must act decisively to:

**Secure Competitive Positioning**: Organizations that delay strategic investment risk permanent competitive disadvantage as market leaders establish insurmountable advantages.

**Capture Market Value**: Early movers are capturing disproportionate market value creation, with late adopters facing significantly higher implementation costs and reduced strategic benefits.

**Define Industry Standards**: Leading organizations are shaping the competitive landscape, regulatory environment, and customer expectations in ways that favor their continued market dominance.

The strategic imperative is clear: organizations must commit to comprehensive {topic.lower()} initiatives now or accept subordinate market positions in the transformed competitive landscape."""
        
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
    
    def _generate_industry_insights(self, topic: str, category: str, keywords: List[str]) -> str:
        """Generate industry-specific insights based on category"""
        insights_map = {
            "Technology": f"## Industry Transformation Indicators\n\nThe technology sector is experiencing fundamental structural changes driven by {keywords[0] if keywords else 'innovation'} adoption. Market research indicates that technology leaders implementing comprehensive strategies achieve 35-50% faster time-to-market and capture 25-40% market share premiums.",
            
            "Healthcare": f"## Healthcare Market Evolution\n\nHealthcare organizations leveraging {keywords[0] if keywords else 'digital health'} capabilities are realizing significant improvements in patient outcomes while reducing operational costs by 20-30%. Regulatory frameworks are evolving to support innovation while maintaining safety standards.",
            
            "Finance": f"## Financial Services Disruption\n\nThe financial services landscape is undergoing unprecedented transformation through {keywords[0] if keywords else 'fintech'} integration. Leading institutions report 40-60% improvement in customer acquisition costs and 25-35% enhancement in customer lifetime value.",
            
            "Manufacturing": f"## Manufacturing Renaissance\n\nManufacturing leaders implementing {keywords[0] if keywords else 'Industry 4.0'} initiatives achieve 30-45% improvement in operational efficiency while reducing quality defects by 50-70%. Supply chain resilience has become a critical competitive differentiator.",
            
            "default": f"## Market Transformation Analysis\n\nIndustry analysis reveals that {topic.lower()} is creating new competitive dynamics in the {category.lower()} sector. Organizations with advanced capabilities are establishing market leadership positions through superior customer value delivery."
        }
        
        return insights_map.get(category, insights_map["default"])
    
    def _generate_strategic_framework(self, topic: str, keywords: List[str], target_audience: str) -> str:
        """Generate strategic implementation framework"""
        primary_keyword = keywords[0] if keywords else 'strategic initiatives'
        
        return f"""## Strategic Implementation Framework

### Capability Assessment Matrix
{target_audience} must evaluate organizational readiness across four critical dimensions:

**Technology Infrastructure**: Current systems' ability to support {primary_keyword} integration and scale requirements for future growth and competitive positioning.

**Organizational Capabilities**: Workforce skills, leadership commitment, and change management capacity to execute comprehensive transformation initiatives successfully.

**Market Positioning**: Competitive landscape analysis and strategic positioning requirements to capture market opportunities and defend against competitive threats.

**Financial Resources**: Investment capacity and ROI expectations for {topic.lower()} initiatives, including both direct costs and opportunity costs of delayed implementation.

### Implementation Methodology

**Phase 1 - Strategic Foundation (Months 1-6)**
- Executive alignment on strategic objectives and success metrics
- Comprehensive capability assessment and gap analysis
- Resource allocation and organizational structure optimization
- Initial pilot program design and launch preparation

**Phase 2 - Tactical Execution (Months 6-18)**  
- Core capability development and technology integration
- Workforce development and change management implementation
- Performance measurement and continuous improvement processes
- Strategic partnership development and ecosystem creation

**Phase 3 - Market Leadership (Months 18+)**
- Competitive differentiation and market positioning
- Advanced capability development and innovation leadership
- Ecosystem expansion and strategic alliance management
- Continuous evolution and competitive advantage maintenance"""
    
    def _generate_competitive_analysis(self, topic: str, category: str) -> str:
        """Generate competitive landscape analysis"""
        return f"""## Competitive Landscape Analysis

### Market Leader Characteristics
Organizations achieving market leadership in {topic.lower()} demonstrate consistent patterns across strategic, operational, and cultural dimensions:

**Strategic Vision**: Clear articulation of {topic.lower()} as core competitive advantage with executive-level commitment and sustained investment over 3-5 year horizons.

**Execution Excellence**: Systematic implementation methodologies with rigorous performance measurement and continuous improvement processes that deliver measurable business outcomes.

**Innovation Culture**: Organizational cultures that embrace experimentation, learning, and adaptation while maintaining operational discipline and customer focus.

### Competitive Differentiation Strategies
Market leaders create sustainable advantages through:

- **Ecosystem Development**: Building strategic partnerships and value networks that create barriers to competitive entry
- **Customer Experience Excellence**: Delivering superior customer value through integrated solutions and seamless experiences  
- **Operational Efficiency**: Achieving cost structures and operational capabilities that enable competitive pricing and superior margins
- **Innovation Leadership**: Continuous capability enhancement and market-leading product development that sets industry standards

### Market Dynamics Impact
The competitive implications of {topic.lower()} extend beyond direct operational benefits to fundamental market structure changes that favor prepared organizations over reactive competitors."""
    
    def _generate_with_claude(self, topic: str, category: str, keywords: List[str], 
                             target_audience: str, tone: str) -> Dict:
        """Generate article using Claude API with proper error handling"""
        try:
            # Create optimized prompt for Claude
            prompt = self._create_claude_prompt(topic, category, keywords, target_audience, tone)
            
            # Generate with Claude using the handler
            response = self.claude_handler.generate_completion(
                messages=[
                    {"role": "system", "content": "You are a Jenosize expert business writer with deep expertise in strategic analysis, market intelligence, and executive communication. You specialize in creating forward-thinking, data-driven content for C-suite executives and business leaders, with a focus on actionable strategic insights and competitive positioning."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            # Extract content
            article_content = response.content[0].text.strip()
            
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
                    "provider": "claude",
                    "generated_at": datetime.now().isoformat(),
                    "generation_type": "ai_claude",
                    "input_tokens": response.usage.input_tokens if response.usage else None,
                    "output_tokens": response.usage.output_tokens if response.usage else None
                }
            }
            
        except Exception as e:
            logger.error(f"Claude generation failed: {e}")
            # Log the specific error type for debugging
            if "rate_limit" in str(e).lower():
                logger.warning("⚠️ Claude rate limit - retrying automatically")
            elif "401" in str(e) or "unauthorized" in str(e).lower():
                logger.warning("⚠️ Claude API key invalid")
            else:
                logger.warning(f"⚠️ Claude API error: {type(e).__name__}")
            raise
    
    def _generate_with_openai(self, topic: str, category: str, keywords: List[str], 
                             target_audience: str, tone: str) -> Dict:
        """Generate article using OpenAI API with proper error handling"""
        try:
            # Create optimized prompt for OpenAI
            prompt = self._create_openai_prompt(topic, category, keywords, target_audience, tone)
            
            # Generate with OpenAI using the handler
            response = self.openai_handler.generate_completion(
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
            # Log the specific error type for debugging
            if "429" in str(e) or "quota" in str(e).lower():
                logger.warning("⚠️ OpenAI quota exceeded - this would work with valid quota")
            elif "401" in str(e) or "unauthorized" in str(e).lower():
                logger.warning("⚠️ OpenAI API key invalid")
            else:
                logger.warning(f"⚠️ OpenAI API error: {type(e).__name__}")
            raise
    
    def _generate_with_huggingface(self, topic: str, category: str, keywords: List[str], 
                                  target_audience: str, tone: str) -> Dict:
        """Generate article using AI model with enhanced error handling"""
        
        try:
            # Create optimized prompt for HuggingFace
            prompt = self._create_huggingface_prompt(topic, category, keywords, target_audience, tone)
            
            # Tokenize with optimized parameters
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=min(800, self.config.max_length),  # More room for comprehensive content
                padding=False
            ).to(self.device)
            
            # Use more conservative generation settings for better coherence
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=min(self.config.max_length, 1200),  # Longer output
                    temperature=0.6,  # Lower temperature for more coherent text
                    top_p=0.8,        # More focused sampling
                    top_k=40,         # Reduced for better quality
                    repetition_penalty=1.15,  # Reduce repetition
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    no_repeat_ngram_size=3,  # Prevent repetitive phrases
                    use_cache=True,
                    num_return_sequences=1
                )
            
            # Decode and clean
            generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            article_content = self._extract_and_clean_hf_content(generated_text, prompt)
            
            # Post-process content for quality
            article_content = self._enhance_content_quality(article_content, topic, keywords)
            
            # Generate professional title
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
    
    def _create_huggingface_prompt(self, topic: str, category: str, keywords: List[str], 
                                  target_audience: str, tone: str) -> str:
        """Create an optimized prompt for HuggingFace models with better structure"""
        keywords_str = ", ".join(keywords[:3])  # Fewer keywords for better focus
        
        # Create a more structured prompt that guides the model better
        prompt = f"""Business Article: {topic}

Executive Summary: {topic} represents a significant opportunity for {target_audience} in the {category} sector. Organizations implementing {keywords_str} strategies are seeing substantial competitive advantages.

Current Market Analysis: Leading companies are transforming their operations through strategic {keywords[0] if keywords else 'innovation'} initiatives. Market research indicates that forward-thinking organizations investing in these capabilities are experiencing:

- Enhanced operational efficiency through systematic implementation
- Improved competitive positioning in rapidly evolving markets  
- Strengthened customer relationships and market presence
- Accelerated growth through strategic technology adoption

Strategic Implementation Framework: Successful organizations follow a comprehensive approach that encompasses:

1. Strategic Planning: Develop clear roadmap aligning {topic.lower()} initiatives with business objectives
2. Technology Integration: Implement scalable solutions that enhance operational capabilities
3. Change Management: Ensure workforce adaptation and skill development
4. Performance Measurement: Establish metrics for continuous improvement

Future Market Outlook: The trajectory of {topic.lower()} suggests continued evolution and strategic importance. Organizations establishing strong foundations today will be positioned for long-term success.

Key recommendations include systematic evaluation of current capabilities, strategic investment in core technologies, and development of adaptive organizational structures that support ongoing innovation and market responsiveness."""
        
        return prompt
    
    def _extract_and_clean_hf_content(self, generated_text: str, prompt: str) -> str:
        """Extract and clean HuggingFace generated content with quality enhancements"""
        # Remove the original prompt
        content = generated_text.replace(prompt, "").strip()
        
        # Clean up common issues - fix literal newlines
        content = content.replace("\\\\n\\\\n\\\\n", "\n\n")
        content = content.replace("\\\\n\\\\n", "\n\n")
        content = content.replace("\\\\n", "\n")
        content = content.replace("  ", " ")
        
        # Remove incomplete sentences at the end
        sentences = content.split('.')
        if len(sentences) > 1 and len(sentences[-1].strip()) < 20:
            content = '.'.join(sentences[:-1]) + '.'
        
        # Ensure professional conclusion if content is short
        if len(content.split()) < 200:
            content += "\n\n## Strategic Conclusions\n\nOrganizations that act decisively in implementing these strategic initiatives will establish competitive advantages and market leadership positions. The convergence of market dynamics and technological capabilities creates unprecedented opportunities for forward-thinking leaders who understand the strategic imperatives and competitive positioning requirements of the modern business landscape."
        
        return content.strip()
    
    def _enhance_content_quality(self, content: str, topic: str, keywords: List[str]) -> str:
        """Enhance content quality with professional language and structure"""
        # Split into paragraphs for processing
        paragraphs = [p.strip() for p in content.split('\\n\\n') if p.strip()]
        enhanced_paragraphs = []
        
        for paragraph in paragraphs:
            # Skip very short paragraphs
            if len(paragraph.split()) < 10:
                continue
                
            # Enhance paragraph with professional language
            enhanced = paragraph
            
            # Replace casual language with business language
            replacements = {
                'things': 'initiatives',
                'stuff': 'solutions',
                'really': 'significantly',
                'very': 'highly',
                'good': 'effective',
                'bad': 'suboptimal',
                'big': 'substantial',
                'small': 'targeted'
            }
            
            for casual, professional in replacements.items():
                enhanced = enhanced.replace(f' {casual} ', f' {professional} ')
            
            enhanced_paragraphs.append(enhanced)
        
        # Rejoin paragraphs
        result = '\\n\\n'.join(enhanced_paragraphs)
        
        # Ensure strategic language is present
        if 'strategic' not in result.lower():
            result = result.replace('important', 'strategic')
        
        if 'competitive' not in result.lower() and 'advantage' in result.lower():
            result = result.replace('advantage', 'competitive advantage')
            
        return result
    
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
        """Create an enhanced prompt with examples for higher quality Jenosize-style content"""
        keywords_str = ", ".join(keywords[:5])  # Limit keywords
        
        # Include specific examples from our training data
        example_opening = "The convergence of market dynamics and technological innovation is creating unprecedented strategic opportunities for forward-thinking organizations. Leaders who understand these emerging trends and act decisively will position their organizations as market leaders in an increasingly competitive landscape."
        
        prompt = f"""You are a Jenosize expert business writer with 15+ years of experience writing strategic content for Fortune 500 C-suite executives. Write a comprehensive, executive-level business article about "{topic}" in the {category} sector.

WRITING STYLE - JENOSIZE EDITORIAL STANDARDS:
Follow this exact style from our best-performing content:

OPENING STYLE (use similar structure):
"{example_opening}"

CONTENT REQUIREMENTS:
- **Strategic Depth**: Every paragraph must provide actionable business insights
- **Executive Language**: Use sophisticated business vocabulary (e.g., "strategic imperatives", "competitive positioning", "market dynamics")  
- **Data Integration**: Include specific metrics like "300% growth", "20-30% improvement", "market indicators show"
- **Authority Tone**: Write with confidence using declarative statements, avoid tentative language
- **Future Focus**: Emphasize what forward-thinking organizations are doing NOW

TARGET SPECIFICATIONS:
- Primary Audience: {target_audience} (senior executives making strategic decisions)
- Editorial Tone: {tone} with authoritative, insights-driven perspective
- Core Keywords: {keywords_str} (integrate naturally, don't force)
- Word Count: 800-1200 words (comprehensive executive briefing)
- Readability: Sophisticated but accessible to busy executives

MANDATORY ARTICLE STRUCTURE:
1. **Strategic Opening Paragraph**: Market transformation + business implications (100-150 words)
2. **Executive Summary Section**: Key strategic findings and imperatives (150-200 words)  
3. **Current Market Dynamics**: What's happening now with specific examples (200-250 words)
4. **Strategic Implementation Framework**: Actionable steps for organizations (200-250 words)
5. **Future Outlook & Recommendations**: Forward-looking analysis (150-200 words)
6. **Executive Conclusions**: Strategic imperatives and competitive positioning (100-150 words)

QUALITY STANDARDS:
- Use section headers like "## Strategic Implementation Framework"
- Include bulleted action items and frameworks
- Reference "leading organizations", "industry leaders", "forward-thinking companies"
- Mention quantifiable benefits and ROI implications
- End with urgency and competitive positioning

Write as if this article will be read by CEOs making million-dollar strategic decisions. Every sentence must provide value."""

        return prompt
    
    def _create_claude_prompt(self, topic: str, category: str, keywords: List[str], 
                             target_audience: str, tone: str) -> str:
        """Create an enhanced prompt optimized for Claude with Jenosize style"""
        keywords_str = ", ".join(keywords[:5])  # Limit keywords
        
        # Include specific examples from our training data
        example_opening = "The convergence of market dynamics and technological innovation is creating unprecedented strategic opportunities for forward-thinking organizations. Leaders who understand these emerging trends and act decisively will position their organizations as market leaders in an increasingly competitive landscape."
        
        prompt = f"""Write a comprehensive, executive-level business article about "{topic}" in the {category} sector for {target_audience}.

WRITING STYLE - JENOSIZE EDITORIAL STANDARDS:
Follow this exact style from our best-performing content:

OPENING STYLE (use similar structure):
"{example_opening}"

CONTENT REQUIREMENTS:
- **Strategic Depth**: Every paragraph must provide actionable business insights
- **Executive Language**: Use sophisticated business vocabulary (e.g., "strategic imperatives", "competitive positioning", "market dynamics")  
- **Data Integration**: Include specific metrics like "300% growth", "20-30% improvement", "market indicators show"
- **Authority Tone**: Write with confidence using declarative statements, avoid tentative language
- **Future Focus**: Emphasize what forward-thinking organizations are doing NOW

TARGET SPECIFICATIONS:
- Primary Audience: {target_audience} (senior executives making strategic decisions)
- Editorial Tone: {tone} with authoritative, insights-driven perspective
- Core Keywords: {keywords_str} (integrate naturally, don't force)
- Word Count: 800-1200 words (comprehensive executive briefing)
- Readability: Sophisticated but accessible to busy executives

MANDATORY ARTICLE STRUCTURE:
1. **Strategic Opening Paragraph**: Market transformation + business implications (100-150 words)
2. **Executive Summary Section**: Key strategic findings and imperatives (150-200 words)  
3. **Current Market Dynamics**: What's happening now with specific examples (200-250 words)
4. **Strategic Implementation Framework**: Actionable steps for organizations (200-250 words)
5. **Future Outlook & Recommendations**: Forward-looking analysis (150-200 words)
6. **Executive Conclusions**: Strategic imperatives and competitive positioning (100-150 words)

QUALITY STANDARDS:
- Use section headers like "## Strategic Implementation Framework"
- Include bulleted action items and frameworks
- Reference "leading organizations", "industry leaders", "forward-thinking companies"
- Mention quantifiable benefits and ROI implications
- End with urgency and competitive positioning

Write as if this article will be read by CEOs making million-dollar strategic decisions. Every sentence must provide value."""

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