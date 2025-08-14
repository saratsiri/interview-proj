"""Main API application"""
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables from .env file (development only)
if os.getenv("ENVIRONMENT") != "production":
    load_dotenv()

from src.api.schemas import ArticleRequest, ArticleResponse, ArticleMetadata
from src.api.security import (
    rate_limiter, input_sanitizer, security_headers, request_validator,
    audit_logger, get_client_ip, APIKeyAuth
)
from src.model.generator import JenosizeTrendGenerator
from src.model.config import ModelConfig
from src.style_matcher.integrated_generator import StyleAwareContentGenerator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Jenosize Trend Articles Generator API",
    description="Generate high-quality business trend articles using AI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize security
api_keys = os.getenv("API_KEYS", "").split(",") if os.getenv("API_KEYS") else []
api_key_auth = APIKeyAuth(api_keys) if api_keys else APIKeyAuth()

# Initialize model with style matching
try:
    logger.info("Initializing style-aware content generator...")
    config = ModelConfig()
    style_generator = StyleAwareContentGenerator(config)
    
    # Initialize the style system
    logger.info("Loading Jenosize article database and style matching...")
    style_generator.initialize_style_system()
    
    # Keep legacy generator for fallback
    generator = JenosizeTrendGenerator(config)
    logger.info("Style-aware generator initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize style-aware generator: {e}")
    style_generator = None
    generator = JenosizeTrendGenerator()  # Fallback to mock

# Security middleware
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Add security headers and rate limiting"""
    
    # Get client info
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Log request
    audit_logger.log_request(request, client_ip, user_agent)
    
    # Rate limiting (skip for health checks)
    if request.url.path not in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
        allowed, message = rate_limiter.is_allowed(client_ip)
        if not allowed:
            audit_logger.log_rate_limit_exceeded(client_ip, "global")
            return JSONResponse(
                status_code=429,
                content={"detail": message}
            )
    
    # Process request
    response = await call_next(request)
    
    # Add security headers
    for key, value in security_headers.get_security_headers().items():
        response.headers[key] = value
    
    return response

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Jenosize Trend Articles Generator",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "/": "Service info",
            "/health": "Health check",
            "/generate": "Generate article (POST)",
            "/style-recommendations": "Get style recommendations for a topic (GET)",
            "/style-categories": "Get available Jenosize categories (GET)",
            "/docs": "Interactive API documentation",
            "/redoc": "Alternative API documentation"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    generator_type = "mock"
    style_matching_enabled = False
    
    if hasattr(generator, 'use_ai') and generator.use_ai:
        generator_type = "ai"
    
    if style_generator and style_generator.style_ready:
        style_matching_enabled = True
        generator_type += "_with_style_matching"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "generator_type": generator_type,
        "style_matching_enabled": style_matching_enabled,
        "article_database_size": len(style_generator.style_matcher.articles) if style_generator and style_generator.style_ready else 0
    }

@app.post("/generate", response_model=ArticleResponse)
async def generate_article(
    request: ArticleRequest, 
    http_request: Request,
    credentials = Depends(api_key_auth)
):
    """Generate a trend article based on provided parameters"""
    
    try:
        # Get client info
        client_ip = get_client_ip(http_request)
        
        # Input validation and sanitization
        try:
            # Validate request body size
            body = await http_request.body()
            request_validator.validate_request_size(body)
            
            # Validate content type
            content_type = http_request.headers.get("content-type", "")
            request_validator.validate_content_type(content_type)
            
            # Sanitize core inputs
            topic = input_sanitizer.sanitize_string(request.topic, request_validator.MAX_TOPIC_LENGTH)
            
            # Validate category - use exact Jenosize scraped categories
            allowed_categories = [
                "Consumer Insights", "Experience", "Futurist", "Marketing", "Technology", 
                "Utility Consumer Insights Sustainability"
            ]
            category = input_sanitizer.validate_category(request.category, allowed_categories)
            
            # Sanitize keywords (increased limit for enhanced functionality)
            keywords = input_sanitizer.sanitize_keywords(
                request.keywords, 
                15,  # Increased from 10 to 15
                request_validator.MAX_KEYWORD_LENGTH
            )
            
            # Sanitize required fields
            target_audience = input_sanitizer.sanitize_string(
                request.target_audience or "Business Leaders and Tech Professionals",
                200  # Increased length limit
            )
            tone = input_sanitizer.sanitize_string(
                request.tone or "Professional and Insightful",
                request_validator.MAX_TONE_LENGTH
            )
            
            # Sanitize optional enhanced fields
            industry = None
            if request.industry:
                industry = input_sanitizer.sanitize_string(request.industry, 100)
            
            data_source = None
            if request.data_source:
                data_source = input_sanitizer.sanitize_string(request.data_source, 200)
                
            company_context = None
            if request.company_context:
                company_context = input_sanitizer.sanitize_string(request.company_context, 500)
            
            # Content parameters
            content_length = request.content_length or "Medium"
            include_statistics = request.include_statistics if request.include_statistics is not None else True
            include_case_studies = request.include_case_studies if request.include_case_studies is not None else True
            call_to_action_type = request.call_to_action_type or "consultation"
            
            # Style matching parameters
            use_style_matching = request.use_style_matching if request.use_style_matching is not None else True
            num_style_examples = request.num_style_examples or 3
            
        except HTTPException:
            raise
        except Exception as e:
            audit_logger.log_security_violation(client_ip, "input_validation", str(e))
            raise HTTPException(status_code=400, detail="Invalid input format")
        
        logger.info(f"Generating enhanced article for topic: {topic}")
        if industry:
            logger.info(f"Industry focus: {industry}")
        if data_source:
            logger.info(f"Data source: {data_source}")
            
        # Generate article with enhanced parameters
        if style_generator and style_generator.style_ready:
            logger.info("Using style-aware generation with enhanced Jenosize parameters")
            result = style_generator.generate_with_enhanced_parameters(
                topic=topic,
                category=category,
                keywords=keywords,
                target_audience=target_audience,
                tone=tone,
                industry=industry,
                data_source=data_source,
                company_context=company_context,
                content_length=content_length,
                include_statistics=include_statistics,
                include_case_studies=include_case_studies,
                call_to_action_type=call_to_action_type,
                use_similar_examples=use_style_matching,
                num_style_examples=num_style_examples
            )
        else:
            logger.info("Using standard generation (style matching not available)")
            result = generator.generate_article(
                topic=topic,
                category=category,
                keywords=keywords,
                target_audience=target_audience,
                tone=tone
            )
        
        # Create enhanced metadata
        metadata = ArticleMetadata(
            # Core content metadata
            category=result["metadata"]["category"],
            keywords=result["metadata"]["keywords"],
            target_audience=result["metadata"]["target_audience"],
            tone=result["metadata"]["tone"],
            word_count=result["metadata"]["word_count"],
            
            # Industry and context
            industry=industry,
            data_source=data_source,
            company_context=company_context,
            
            # Generation details
            content_length=content_length,
            include_statistics=include_statistics,
            include_case_studies=include_case_studies,
            call_to_action_type=call_to_action_type,
            
            # Technical metadata
            model=result["metadata"]["model"],
            generated_at=result["metadata"]["generated_at"],
            generation_time_seconds=result["metadata"].get("generation_time_seconds"),
            
            # Style matching metadata
            style_matching_used=result.get("style_matching", {}).get("used_style_examples", False),
            style_examples_count=num_style_examples if use_style_matching else None,
            similar_articles_referenced=len(result.get("style_matching", {}).get("similar_articles", []))
        )
        
        # Create response
        response = ArticleResponse(
            title=result["title"],
            content=result["content"],
            metadata=metadata
        )
        
        logger.info(f"Article generated successfully: {response.title}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating article: {e}")
        audit_logger.log_security_violation(get_client_ip(http_request), "generation_error", str(e))
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

# Add rate limit status endpoint
@app.get("/rate-limit-status")
async def get_rate_limit_status(request: Request):
    """Get rate limit status for current client"""
    client_ip = get_client_ip(request)
    status = rate_limiter.get_status(client_ip)
    return status

# Style matching endpoints
@app.get("/style-recommendations")
async def get_style_recommendations(topic: str, num_recommendations: int = 5):
    """Get style recommendations for a given topic"""
    if not style_generator or not style_generator.style_ready:
        raise HTTPException(status_code=503, detail="Style matching system not available")
    
    try:
        recommendations = style_generator.get_style_recommendations(topic, num_recommendations)
        return {
            "topic": topic,
            "recommendations": recommendations,
            "total_found": len(recommendations)
        }
    except Exception as e:
        logger.error(f"Error getting style recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {str(e)}")

@app.get("/style-categories")
async def get_available_categories():
    """Get available Jenosize categories for style matching"""
    if not style_generator or not style_generator.style_ready:
        raise HTTPException(status_code=503, detail="Style matching system not available")
    
    try:
        categories = style_generator.get_available_categories()
        stats = style_generator.style_matcher.get_category_statistics()
        
        category_info = []
        for category in categories:
            stat = stats.get(category, {})
            category_info.append({
                "name": category,
                "article_count": stat.get("count", 0),
                "total_words": stat.get("total_words", 0),
                "avg_words": round(stat.get("avg_words", 0))
            })
        
        return {
            "categories": category_info,
            "total_articles": sum(info["article_count"] for info in category_info),
            "total_words": sum(info["total_words"] for info in category_info)
        }
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler with security logging"""
    client_ip = get_client_ip(request)
    audit_logger.log_security_violation(client_ip, "unhandled_exception", str(exc))
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": str(type(exc).__name__)}
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)