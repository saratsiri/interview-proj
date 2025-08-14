#!/usr/bin/env python3
"""
Integrated Style-Aware Content Generator
Combines style matching with our existing Claude/OpenAI generation system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Dict, List, Optional
import logging
from datetime import datetime
from .article_processor import JenosizeArticleStyleMatcher
from .style_prompt_generator import JenosizeStylePromptGenerator
from model.generator import JenosizeTrendGenerator
from model.config import ModelConfig

logger = logging.getLogger(__name__)

class StyleAwareContentGenerator:
    def __init__(self, config: ModelConfig = None):
        """
        Initialize the integrated style-aware content generator.
        
        Args:
            config: Model configuration for the content generator
        """
        logger.info("🚀 Initializing Style-Aware Content Generator")
        
        # Initialize style matching system
        self.style_matcher = JenosizeArticleStyleMatcher()
        self.style_generator = None
        
        # Initialize content generator with existing system
        self.config = config or ModelConfig()
        self.content_generator = JenosizeTrendGenerator(self.config)
        
        # Track if style system is ready
        self.style_ready = False
        
    def initialize_style_system(self, force_recompute: bool = False) -> None:
        """Initialize the style matching system with our article database."""
        try:
            logger.info("📚 Loading Jenosize article database...")
            self.style_matcher.load_jenosize_articles()
            
            logger.info("🧠 Computing article embeddings...")
            self.style_matcher.fit(force_recompute=force_recompute)
            
            # Initialize style prompt generator
            self.style_generator = JenosizeStylePromptGenerator(self.style_matcher)
            self.style_ready = True
            
            logger.info("✅ Style matching system ready!")
            
            # Display database statistics
            stats = self.style_matcher.get_category_statistics()
            logger.info("📊 Article database statistics:")
            for category, data in stats.items():
                logger.info(f"  {category}: {data['count']} articles, {data['avg_words']:.0f} avg words")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize style system: {e}")
            self.style_ready = False
            raise
    
    def generate_with_style_matching(self,
                                   topic: str,
                                   category: str = None,
                                   keywords: List[str] = None,
                                   target_audience: str = "business professionals",
                                   tone: str = "professional",
                                   target_word_count: int = 800,
                                   use_similar_examples: bool = True,
                                   num_style_examples: int = 3) -> Dict:
        """
        Generate content using style matching for enhanced authenticity.
        
        Args:
            topic: Main topic for the content
            category: Target category (optional, will be inferred if not provided)
            keywords: SEO keywords to include
            target_audience: Target audience description
            tone: Desired tone for the content
            target_word_count: Target word count for the article
            use_similar_examples: Whether to use style matching
            num_style_examples: Number of style examples to include
            
        Returns:
            Generated content with metadata
        """
        if not self.style_ready and use_similar_examples:
            logger.warning("⚠️ Style system not ready, falling back to standard generation")
            use_similar_examples = False
        
        # Generate content brief for style matching
        content_brief = f"Write about {topic}"
        if keywords:
            content_brief += f" including keywords: {', '.join(keywords)}"
        if target_audience:
            content_brief += f" for {target_audience}"
        
        if use_similar_examples:
            logger.info(f"🎨 Generating content with style matching for: {topic}")
            
            # Generate style-aware prompt
            style_prompt = self.style_generator.generate_style_prompt(
                content_brief=content_brief,
                num_examples=num_style_examples,
                category_filter=category,
                target_word_count=target_word_count
            )
            
            # Find similar articles for reference
            similar_articles = self.style_matcher.find_similar_articles(
                content_brief,
                top_k=num_style_examples,
                category_filter=category
            )
            
            # Generate content using style-enhanced prompt
            result = self._generate_with_style_prompt(
                style_prompt=style_prompt,
                topic=topic,
                category=category or self._infer_category(topic),
                keywords=keywords or [],
                target_audience=target_audience,
                tone=tone,
                similar_articles=similar_articles
            )
            
        else:
            logger.info(f"📝 Generating content with standard method for: {topic}")
            # Fall back to standard generation
            result = self.content_generator.generate_article(
                topic=topic,
                category=category or "Business",
                keywords=keywords or [],
                target_audience=target_audience,
                tone=tone
            )
        
        # Add style matching metadata
        if use_similar_examples and self.style_ready:
            result['style_matching'] = {
                'used_style_examples': True,
                'num_examples': num_style_examples,
                'similar_articles': [
                    {
                        'title': article['article']['title'],
                        'category': article['article']['category'],
                        'similarity': article['similarity']
                    }
                    for article in similar_articles
                ]
            }
        else:
            result['style_matching'] = {'used_style_examples': False}
        
        return result
    
    def generate_with_enhanced_parameters(self,
                                        topic: str,
                                        category: str = None,
                                        keywords: List[str] = None,
                                        target_audience: str = "business professionals",
                                        tone: str = "professional",
                                        industry: str = None,
                                        data_source: str = None,
                                        company_context: str = None,
                                        content_length: str = "Medium",
                                        include_statistics: bool = True,
                                        include_case_studies: bool = True,
                                        call_to_action_type: str = "consultation",
                                        use_similar_examples: bool = True,
                                        num_style_examples: int = 3) -> Dict:
        """
        Generate content using enhanced parameters for comprehensive content creation.
        
        Args:
            topic: Main topic for the content
            category: Target category (optional, will be inferred if not provided)
            keywords: SEO keywords to include
            target_audience: Target audience description
            tone: Desired tone for the content
            industry: Specific industry focus
            data_source: Source of website data or document reference
            company_context: Company or brand context information
            content_length: Target content length (Short, Medium, Long, Comprehensive)
            include_statistics: Whether to include statistical data
            include_case_studies: Whether to include case studies and examples
            call_to_action_type: Type of call-to-action to include
            use_similar_examples: Whether to use style matching
            num_style_examples: Number of style examples to include
            
        Returns:
            Generated content with metadata
        """
        if not self.style_ready and use_similar_examples:
            logger.warning("⚠️ Style system not ready, falling back to standard generation")
            use_similar_examples = False
        
        # Calculate target word count based on content length
        word_count_map = {
            "Short": 400,
            "Medium": 800,
            "Long": 1200,
            "Comprehensive": 1600
        }
        target_word_count = word_count_map.get(content_length, 800)
        
        # Enhanced content brief generation
        content_brief = f"Write a {content_length.lower()} article about {topic}"
        if industry:
            content_brief += f" specifically for the {industry} industry"
        if keywords:
            content_brief += f" including keywords: {', '.join(keywords)}"
        if target_audience:
            content_brief += f" for {target_audience}"
        if company_context:
            content_brief += f". Company context: {company_context}"
        if data_source:
            content_brief += f". Reference data from: {data_source}"
        
        # Additional content requirements
        content_requirements = []
        if include_statistics:
            content_requirements.append("Include relevant statistics and data points")
        if include_case_studies:
            content_requirements.append("Include real-world examples and case studies")
        
        if content_requirements:
            content_brief += f". Requirements: {'; '.join(content_requirements)}"
        
        logger.info(f"Enhanced content brief: {content_brief[:100]}...")
        
        if use_similar_examples:
            logger.info(f"🎨 Generating content with enhanced style matching for: {topic}")
            
            # Generate enhanced style-aware prompt
            style_prompt = self.style_generator.generate_enhanced_style_prompt(
                content_brief=content_brief,
                num_examples=num_style_examples,
                category_filter=category,
                target_word_count=target_word_count,
                industry=industry,
                include_statistics=include_statistics,
                include_case_studies=include_case_studies,
                call_to_action_type=call_to_action_type
            )
            
            # Find similar articles for reference
            similar_articles = self.style_matcher.find_similar_articles(
                content_brief,
                top_k=num_style_examples,
                category_filter=category
            )
            
            # Generate content using enhanced style prompt
            result = self._generate_with_style_prompt(
                style_prompt=style_prompt,
                topic=topic,
                category=category or self._infer_category(topic),
                keywords=keywords or [],
                target_audience=target_audience,
                tone=tone,
                similar_articles=similar_articles
            )
            
        else:
            logger.info(f"📝 Generating content with standard method for: {topic}")
            # Fall back to standard generation
            result = self.content_generator.generate_article(
                topic=topic,
                category=category or "Technology",
                keywords=keywords or [],
                target_audience=target_audience,
                tone=tone
            )
        
        # Add enhanced style matching metadata
        if use_similar_examples and self.style_ready:
            result['style_matching'] = {
                'used_style_examples': True,
                'num_examples': num_style_examples,
                'enhanced_parameters_used': True,
                'industry_focus': industry,
                'content_length': content_length,
                'include_statistics': include_statistics,
                'include_case_studies': include_case_studies,
                'call_to_action_type': call_to_action_type,
                'similar_articles': [
                    {
                        'title': article['article']['title'],
                        'category': article['article']['category'],
                        'similarity': article['similarity']
                    }
                    for article in similar_articles
                ]
            }
        else:
            result['style_matching'] = {
                'used_style_examples': False,
                'enhanced_parameters_used': True,
                'industry_focus': industry,
                'content_length': content_length
            }
        
        return result
    
    def _generate_with_style_prompt(self,
                                  style_prompt: str,
                                  topic: str,
                                  category: str,
                                  keywords: List[str],
                                  target_audience: str,
                                  tone: str,
                                  similar_articles: List[Dict]) -> Dict:
        """Generate content using the style-enhanced prompt."""
        
        # Use Claude if available, otherwise OpenAI
        if self.content_generator.claude_handler:
            logger.info("🤖 Generating with Claude API using style prompt")
            return self._generate_with_claude_style(
                style_prompt, topic, category, keywords, target_audience, tone
            )
        elif self.content_generator.openai_handler:
            logger.info("🤖 Generating with OpenAI API using style prompt")
            return self._generate_with_openai_style(
                style_prompt, topic, category, keywords, target_audience, tone
            )
        else:
            logger.info("🤖 Generating with fallback method")
            return self.content_generator.generate_article(
                topic, category, keywords, target_audience, tone
            )
    
    def _generate_with_claude_style(self,
                                  style_prompt: str,
                                  topic: str,
                                  category: str,
                                  keywords: List[str],
                                  target_audience: str,
                                  tone: str) -> Dict:
        """Generate content using Claude with style prompt."""
        try:
            messages = [
                {
                    "role": "user",
                    "content": style_prompt
                }
            ]
            
            response = self.content_generator.claude_handler.generate_completion(
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            if response and hasattr(response, 'content') and response.content:
                content = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content[0])
                
                # Process and structure the response
                return self._process_generated_content(
                    content, topic, category, keywords, target_audience, tone, "claude"
                )
            else:
                raise ValueError("No content received from Claude")
                
        except Exception as e:
            logger.error(f"❌ Claude generation failed: {e}")
            # Fallback to standard generation
            return self.content_generator.generate_article(
                topic, category, keywords, target_audience, tone
            )
    
    def _generate_with_openai_style(self,
                                  style_prompt: str,
                                  topic: str,
                                  category: str,
                                  keywords: List[str],
                                  target_audience: str,
                                  tone: str) -> Dict:
        """Generate content using OpenAI with style prompt."""
        try:
            messages = [
                {"role": "system", "content": "You are an expert content writer for Jenosize."},
                {"role": "user", "content": style_prompt}
            ]
            
            response = self.content_generator.openai_handler.generate_completion(
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            if response and response.choices:
                content = response.choices[0].message.content
                
                return self._process_generated_content(
                    content, topic, category, keywords, target_audience, tone, "openai"
                )
            else:
                raise ValueError("No content received from OpenAI")
                
        except Exception as e:
            logger.error(f"❌ OpenAI generation failed: {e}")
            # Fallback to standard generation
            return self.content_generator.generate_article(
                topic, category, keywords, target_audience, tone
            )
    
    def _process_generated_content(self,
                                 content: str,
                                 topic: str,
                                 category: str,
                                 keywords: List[str],
                                 target_audience: str,
                                 tone: str,
                                 model_used: str) -> Dict:
        """Process and structure the generated content."""
        
        # Extract title (first line or H1)
        lines = content.split('\n')
        potential_title = lines[0].strip('#').strip() if lines else topic
        
        # If the extracted title is too long (likely the first paragraph), create a proper title
        if len(potential_title) > 100:
            title = f"{topic} - {category}"
        else:
            title = potential_title
        
        # Clean content - if we used the first line as title, remove it from content
        if len(potential_title) <= 100 and len(lines) > 1:
            content_body = '\n'.join(lines[1:]).strip()
        else:
            content_body = content.strip()
        
        # Calculate metrics
        word_count = len(content_body.split())
        
        # Quality scoring (simplified)
        quality_score = self._calculate_quality_score(content_body, keywords)
        
        return {
            'title': title,
            'content': content_body,
            'topic': topic,
            'metadata': {
                'category': category,
                'keywords': keywords,
                'target_audience': target_audience,
                'tone': tone,
                'word_count': word_count,
                'model': model_used,
                'quality_score': quality_score,
                'generated_at': datetime.now().isoformat()
            }
        }
    
    def _calculate_quality_score(self, content: str, keywords: List[str]) -> float:
        """Calculate a simple quality score for the content."""
        score = 0.8  # Base score
        
        # Keyword inclusion
        if keywords:
            keyword_mentions = sum(1 for keyword in keywords if keyword.lower() in content.lower())
            keyword_score = min(keyword_mentions / len(keywords), 1.0) * 0.2
            score += keyword_score
        
        # Length appropriateness
        word_count = len(content.split())
        if 600 <= word_count <= 1200:
            score += 0.1
        
        # Jenosize patterns
        if "In today's digital era" in content or "digital transformation" in content:
            score += 0.05
        
        if "Jenosize" in content:
            score += 0.05
        
        return min(score, 1.0)
    
    def _infer_category(self, topic: str) -> str:
        """Infer the most appropriate category based on topic."""
        if not self.style_ready:
            return "Business"
        
        # Use style matching to find the best category
        similar_articles = self.style_matcher.find_similar_articles(topic, top_k=3)
        
        if similar_articles:
            # Return the most common category among similar articles
            categories = [article['article']['category'] for article in similar_articles]
            return max(set(categories), key=categories.count)
        
        return "Business"
    
    def get_style_recommendations(self, topic: str, num_recommendations: int = 5) -> List[Dict]:
        """Get style recommendations for a given topic."""
        if not self.style_ready:
            logger.warning("⚠️ Style system not ready")
            return []
        
        similar_articles = self.style_matcher.find_similar_articles(
            topic, 
            top_k=num_recommendations
        )
        
        recommendations = []
        for article_data in similar_articles:
            article = article_data['article']
            recommendations.append({
                'title': article['title'],
                'category': article['category'],
                'word_count': article['word_count'],
                'similarity': article_data['similarity'],
                'url': article.get('url', ''),
                'preview': article['content'][:200] + "..." if len(article['content']) > 200 else article['content']
            })
        
        return recommendations
    
    def get_available_categories(self) -> List[str]:
        """Get list of available categories in the database."""
        if not self.style_ready:
            return []
        
        stats = self.style_matcher.get_category_statistics()
        return list(stats.keys())