"""Main API application"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from datetime import datetime
import os

from src.api.schemas import ArticleRequest, ArticleResponse, ArticleMetadata
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

# Initialize model
try:
    logger.info("Initializing model...")
    config = ModelConfig()
    generator = JenosizeTrendGenerator(config)
    logger.info("Model initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize model: {e}")
    generator = JenosizeTrendGenerator()  # Fallback to mock

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
async def generate_article(request: ArticleRequest):
    """Generate a trend article based on provided parameters"""
    
    try:
        logger.info(f"Generating article for topic: {request.topic}")
        
        # Generate article
        result = generator.generate_article(
            topic=request.topic,
            category=request.category,
            keywords=request.keywords,
            target_audience=request.target_audience,
            tone=request.tone
        )
        
        # Create metadata
        metadata = ArticleMetadata(
            category=result["metadata"]["category"],
            keywords=result["metadata"]["keywords"],
            target_audience=result["metadata"]["target_audience"],
            tone=result["metadata"]["tone"],
            word_count=result["metadata"]["word_count"],
            model=result["metadata"]["model"],
            generated_at=result["metadata"]["generated_at"]
        )
        
        # Create response
        response = ArticleResponse(
            title=result["title"],
            content=result["content"],
            metadata=metadata
        )
        
        logger.info(f"Article generated successfully: {response.title}")
        return response
        
    except Exception as e:
        logger.error(f"Error generating article: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": str(type(exc).__name__)}
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)