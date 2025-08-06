"""Article generation with fallback to mock generation"""
import logging
from typing import Dict, List
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("Transformers not available, using mock generator")
    TRANSFORMERS_AVAILABLE = False

class JenosizeTrendGenerator:
    """Generate trend articles with fallback to mock generation"""
    
    def __init__(self, config=None):
        self.use_ai = TRANSFORMERS_AVAILABLE
        
        if self.use_ai and config:
            try:
                self.config = config
                self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                logger.info(f"Loading model: {self.config.model_name}")
                self.model = AutoModelForCausalLM.from_pretrained(self.config.model_name).to(self.device)
                self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                logger.info("AI model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load AI model: {e}")
                self.use_ai = False
        else:
            self.use_ai = False
            logger.info("Using mock generator")
    
    def generate_article(self, topic: str, category: str, keywords: List[str], 
                        target_audience: str = "Business Leaders", tone: str = "Professional") -> Dict:
        """Generate article using AI or mock generation"""
        
        if self.use_ai:
            return self._generate_with_ai(topic, category, keywords, target_audience, tone)
        else:
            return self._generate_mock_article(topic, category, keywords, target_audience, tone)
    
    def _generate_mock_article(self, topic: str, category: str, keywords: List[str], 
                              target_audience: str, tone: str) -> Dict:
        """Generate a comprehensive mock article"""
        
        # Create rich, detailed content
        introduction = f"The landscape of {topic.lower()} is rapidly evolving, presenting both unprecedented opportunities and unique challenges for {target_audience.lower()}. As we navigate through this transformative period, understanding the key trends and strategic implications becomes crucial for sustained success."
        
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
            "title": f"{topic}: Strategic Insights and Implementation Guide for {target_audience}",
            "content": full_content,
            "metadata": {
                "category": category,
                "keywords": keywords,
                "target_audience": target_audience,
                "tone": tone,
                "word_count": len(full_content.split()),
                "model": "mock_generator_professional",
                "generated_at": datetime.now().isoformat()
            }
        }
    
    def _generate_with_ai(self, topic: str, category: str, keywords: List[str], 
                         target_audience: str, tone: str) -> Dict:
        """Generate article using AI model"""
        prompt = f"Write a professional business article about {topic} in {category}. Keywords: {', '.join(keywords)}. Target: {target_audience}. Tone: {tone}\\n\\nArticle:\\n\\n"
        
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True).to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_length=self.config.max_length,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                top_k=self.config.top_k,
                repetition_penalty=self.config.repetition_penalty,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        article_content = generated_text.replace(prompt, "").strip()
        
        return {
            "title": f"{topic}: AI-Generated Insights and Analysis",
            "content": article_content,
            "metadata": {
                "category": category,
                "keywords": keywords,
                "target_audience": target_audience,
                "tone": tone,
                "word_count": len(article_content.split()),
                "model": self.config.model_name,
                "generated_at": datetime.now().isoformat()
            }
        }