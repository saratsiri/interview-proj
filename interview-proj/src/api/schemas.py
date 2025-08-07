"""API request/response schemas"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime

class ArticleRequest(BaseModel):
    """Request schema for article generation"""
    topic: str = Field(..., min_length=3, max_length=200, description="Article topic")
    category: str = Field(..., description="Business category")
    keywords: List[str] = Field(..., min_items=1, max_items=10, description="SEO keywords")
    target_audience: str = Field(default="Business Leaders and Tech Professionals")
    tone: Optional[str] = Field(default="Professional and Insightful")
    
    @validator('category')
    def validate_category(cls, v):
        allowed = ["Technology", "Business Strategy", "Digital Transformation", 
                  "Innovation", "Sustainability", "Marketing", "Finance"]
        if v not in allowed:
            raise ValueError(f"Category must be one of: {', '.join(allowed)}")
        return v
    
    @validator('keywords', each_item=True)
    def clean_keywords(cls, v):
        return v.strip().lower()

class ArticleMetadata(BaseModel):
    """Metadata for generated article"""
    category: str
    keywords: List[str]
    target_audience: str
    tone: str
    word_count: int
    model: str
    generated_at: str
    generation_time_seconds: Optional[float] = None

class ArticleResponse(BaseModel):
    """Response schema for article generation"""
    success: bool = True
    title: str
    content: str
    metadata: ArticleMetadata
    message: str = "Article generated successfully"