"""Main API application"""
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
import logging
from datetime import datetime
import os

from src.api.schemas import ArticleRequest, ArticleResponse, ArticleMetadata
from src.api.security import (
    rate_limiter, input_sanitizer, security_headers, request_validator,
    audit_logger, get_client_ip, APIKeyAuth
)
from src.model.generator import JenosizeTrendGenerator
from src.model.config import ModelConfig

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

# Initialize model
try:
    logger.info("Initializing model...")
    config = ModelConfig()
    generator = JenosizeTrendGenerator(config)
    logger.info("Model initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize model: {e}")
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
            "/docs": "Interactive API documentation",
            "/redoc": "Alternative API documentation"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "generator_type": "ai" if hasattr(generator, 'use_ai') and generator.use_ai else "mock"
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
            
            # Sanitize inputs
            topic = input_sanitizer.sanitize_string(request.topic, request_validator.MAX_TOPIC_LENGTH)
            
            # Validate category
            allowed_categories = ["Technology", "Business", "Healthcare", "Finance", "Marketing", "Science", "Education"]
            category = input_sanitizer.validate_category(request.category, allowed_categories)
            
            # Sanitize keywords
            keywords = input_sanitizer.sanitize_keywords(
                request.keywords, 
                request_validator.MAX_KEYWORDS, 
                request_validator.MAX_KEYWORD_LENGTH
            )
            
            # Sanitize optional fields
            target_audience = input_sanitizer.sanitize_string(
                request.target_audience or "Business Leaders and Tech Professionals",
                request_validator.MAX_AUDIENCE_LENGTH
            )
            tone = input_sanitizer.sanitize_string(
                request.tone or "Professional and Insightful",
                request_validator.MAX_TONE_LENGTH
            )
            
        except HTTPException:
            raise
        except Exception as e:
            audit_logger.log_security_violation(client_ip, "input_validation", str(e))
            raise HTTPException(status_code=400, detail="Invalid input format")
        
        logger.info(f"Generating article for topic: {topic}")
        
        # Generate article
        result = generator.generate_article(
            topic=topic,
            category=category,
            keywords=keywords,
            target_audience=target_audience,
            tone=tone
        )
        
        # Create metadata
        metadata = ArticleMetadata(
            category=result["metadata"]["category"],
            keywords=result["metadata"]["keywords"],
            target_audience=result["metadata"]["target_audience"],
            tone=result["metadata"]["tone"],
            word_count=result["metadata"]["word_count"],
            model=result["metadata"]["model"],
            generated_at=result["metadata"]["generated_at"],
            generation_time_seconds=result["metadata"].get("generation_time_seconds")
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