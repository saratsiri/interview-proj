"""API request/response schemas"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict
from datetime import datetime

class ArticleRequest(BaseModel):
    """Enhanced request schema for comprehensive article generation"""
    # Core content parameters
    topic: str = Field(..., min_length=3, max_length=200, description="Main article topic")
    category: str = Field(..., description="Jenosize content category")
    keywords: List[str] = Field(..., min_items=1, max_items=15, description="SEO keywords for optimization")
    
    # Industry and audience targeting
    industry: Optional[str] = Field(None, max_length=100, description="Specific industry focus (e.g., Healthcare, Fintech, E-commerce)")
    target_audience: str = Field(default="Business Leaders and Tech Professionals", max_length=200)
    
    # Content customization
    tone: Optional[str] = Field(default="Professional and Insightful", description="Writing tone and style")
    content_length: Optional[str] = Field(default="Medium", description="Target content length")
    
    # Data source and context
    data_source: Optional[str] = Field(None, description="Source of website data or document reference")
    company_context: Optional[str] = Field(None, max_length=500, description="Company or brand context information")
    
    # Advanced generation parameters
    include_statistics: Optional[bool] = Field(default=True, description="Include statistical data and metrics")
    include_case_studies: Optional[bool] = Field(default=True, description="Include real-world examples and case studies")
    call_to_action_type: Optional[str] = Field(default="consultation", description="Type of CTA to include")
    
    # Style matching preferences
    use_style_matching: Optional[bool] = Field(default=True, description="Use Jenosize style matching system")
    num_style_examples: Optional[int] = Field(default=3, ge=1, le=5, description="Number of style examples to use")
    
    @validator('category')
    def validate_category(cls, v):
        # Use exact Jenosize categories
        allowed = ["Consumer Insights", "Experience", "Futurist", "Marketing", "Technology", 
                  "Utility Consumer Insights Sustainability"]
        if v not in allowed:
            raise ValueError(f"Category must be one of: {', '.join(allowed)}")
        return v
    
    @validator('content_length')
    def validate_content_length(cls, v):
        if v is not None:
            allowed = ["Short", "Medium", "Long", "Comprehensive"]
            if v not in allowed:
                raise ValueError(f"Content length must be one of: {', '.join(allowed)}")
        return v
    
    @validator('call_to_action_type')
    def validate_cta_type(cls, v):
        if v is not None:
            allowed = ["consultation", "contact", "demo", "whitepaper", "newsletter", "none"]
            if v not in allowed:
                raise ValueError(f"CTA type must be one of: {', '.join(allowed)}")
        return v
    
    @validator('keywords', each_item=True)
    def clean_keywords(cls, v):
        return v.strip().lower()

class ArticleMetadata(BaseModel):
    """Enhanced metadata for generated article"""
    # Core content metadata
    category: str
    keywords: List[str]
    target_audience: str
    tone: str
    word_count: int
    
    # Industry and context
    industry: Optional[str] = None
    data_source: Optional[str] = None
    company_context: Optional[str] = None
    
    # Generation details
    content_length: str
    include_statistics: bool
    include_case_studies: bool
    call_to_action_type: str
    
    # Technical metadata
    model: str
    generated_at: str
    generation_time_seconds: Optional[float] = None
    
    # Style matching metadata
    style_matching_used: bool = False
    style_examples_count: Optional[int] = None
    similar_articles_referenced: Optional[int] = None

class ArticleResponse(BaseModel):
    """Response schema for article generation"""
    success: bool = True
    title: str
    content: str
    metadata: ArticleMetadata
    message: str = "Article generated successfully"