#!/usr/bin/env python3
"""
Style Prompt Generator for Jenosize Content Generation
Creates prompts with stylistically similar examples for AI models
"""

import re
from typing import List, Dict, Optional
from .article_processor import JenosizeArticleStyleMatcher
import logging

logger = logging.getLogger(__name__)

class JenosizeStylePromptGenerator:
    def __init__(self, matcher: JenosizeArticleStyleMatcher):
        """
        Initialize the style prompt generator.
        
        Args:
            matcher: Fitted JenosizeArticleStyleMatcher instance
        """
        self.matcher = matcher
        
    def generate_style_prompt(self, 
                            content_brief: str,
                            num_examples: int = 3,
                            max_example_words: int = 200,
                            category_filter: Optional[str] = None,
                            target_word_count: Optional[int] = None,
                            include_jenosize_patterns: bool = True) -> str:
        """
        Generate a comprehensive style prompt with Jenosize examples.
        
        Args:
            content_brief: Description of content to generate
            num_examples: Number of style examples to include
            max_example_words: Maximum words per example (for prompt length control)
            category_filter: Filter examples by category
            target_word_count: Target word count for the output
            include_jenosize_patterns: Include specific Jenosize style patterns
            
        Returns:
            Complete prompt string ready for AI model
        """
        logger.info(f"🎨 Generating style prompt for: '{content_brief[:50]}...'")
        
        # Find similar articles
        similar_articles = self.matcher.get_diverse_examples(
            content_brief, 
            num_examples=num_examples
        )
        
        if category_filter:
            # Re-search with category filter if specified
            similar_articles = self.matcher.find_similar_articles(
                content_brief,
                top_k=num_examples,
                category_filter=category_filter
            )
        
        if not similar_articles:
            logger.warning("⚠️ No similar articles found, using default examples")
            # Fallback to random articles from database
            similar_articles = [
                {
                    'article': article,
                    'similarity': 0.5,
                    'rank': i + 1
                }
                for i, article in enumerate(self.matcher.articles[:num_examples])
            ]
        
        # Build the comprehensive prompt
        prompt_parts = [
            "You are an expert content writer for Jenosize, a leading digital transformation and marketing consultancy in Thailand.",
            "",
            "JENOSIZE WRITING STYLE GUIDELINES:",
            "• Start articles with 'In today's digital era...' or similar forward-looking phrases",
            "• Use clear, business-focused language that's accessible yet professional",
            "• Include practical examples and case studies",
            "• Structure content with numbered lists and clear sections",
            "• End with calls-to-action mentioning Jenosize's services",
            "• Focus on business value and practical implementation",
            "",
            "Please write content that matches the style demonstrated in these examples from our article database:"
        ]
        
        # Add style examples
        for i, result in enumerate(similar_articles, 1):
            article = result['article']
            content = article['content']
            
            # Extract key patterns from Jenosize content
            content_preview = self._extract_content_preview(content, max_example_words)
            
            prompt_parts.extend([
                "",
                f"EXAMPLE {i} - {article['category']} Category (Similarity: {result['similarity']:.3f}):",
                f"Title: {article['title']}",
                f"Content Preview: {content_preview}",
                f"Word Count: {article['word_count']} words",
                f"Key Patterns: {self._identify_style_patterns(content)}"
            ])
        
        # Add specific writing instructions
        prompt_parts.extend([
            "",
            "CONTENT BRIEF:",
            f"{content_brief}",
            "",
            "WRITING INSTRUCTIONS:",
            "Based on the examples above, write content that demonstrates:",
            "",
            "1. TONE & VOICE:",
            "   • Professional yet approachable business tone",
            "   • Forward-thinking and optimistic perspective",
            "   • Authoritative but not overly technical",
            "",
            "2. STRUCTURE:",
            "   • Clear, engaging introduction with industry context",
            "   • Well-organized sections with descriptive headings", 
            "   • Numbered lists for key points or strategies",
            "   • Practical examples and real-world applications",
            "",
            "3. CONTENT ELEMENTS:",
            "   • Start with phrases like 'In today's digital era...' or 'In the rapidly evolving...'",
            "   • Include specific business benefits and value propositions",
            "   • Reference current trends and future implications",
            "   • Provide actionable insights and recommendations",
            "",
            "4. JENOSIZE BRANDING:",
            "   • Conclude with Jenosize service offerings",
            "   • Mention specific expertise areas relevant to the topic",
            "   • Include a call-to-action for consultation or contact",
            ""
        ])
        
        # Add word count guidance if specified
        if target_word_count:
            prompt_parts.extend([
                f"5. LENGTH REQUIREMENT:",
                f"   • Target approximately {target_word_count} words",
                f"   • Ensure comprehensive coverage without being verbose",
                ""
            ])
        
        # Add category-specific instructions
        if category_filter:
            category_instructions = self._get_category_specific_instructions(category_filter)
            if category_instructions:
                prompt_parts.extend([
                    f"6. {category_filter.upper()} CATEGORY FOCUS:",
                    category_instructions,
                    ""
                ])
        
        # Final instruction
        prompt_parts.extend([
            "Generate the article following these style guidelines and incorporating the demonstrated patterns.",
            "Ensure the content is valuable, engaging, and clearly positions Jenosize as the expert solution provider."
        ])
        
        return "\n".join(prompt_parts)
    
    def generate_enhanced_style_prompt(self,
                                     content_brief: str,
                                     num_examples: int = 3,
                                     category_filter: Optional[str] = None,
                                     target_word_count: Optional[int] = None,
                                     industry: Optional[str] = None,
                                     include_statistics: bool = True,
                                     include_case_studies: bool = True,
                                     call_to_action_type: str = "consultation") -> str:
        """
        Generate an enhanced style prompt with additional parameters for comprehensive content generation.
        
        Args:
            content_brief: Description of content to generate
            num_examples: Number of style examples to include
            category_filter: Filter examples by category
            target_word_count: Target word count for the output
            industry: Specific industry focus
            include_statistics: Whether to include statistical data
            include_case_studies: Whether to include case studies
            call_to_action_type: Type of call-to-action to include
            
        Returns:
            Enhanced prompt string ready for AI model
        """
        logger.info(f"🎨 Generating enhanced style prompt for: '{content_brief[:50]}...'")
        
        # For now, use the standard style prompt generation with enhanced content brief
        # This can be expanded with more sophisticated logic later
        return self.generate_style_prompt(
            content_brief=content_brief,
            num_examples=num_examples,
            category_filter=category_filter,
            target_word_count=target_word_count,
            include_jenosize_patterns=True
        )
    
    def generate_few_shot_examples(self, 
                                 content_brief: str,
                                 num_examples: int = 2,
                                 category_filter: Optional[str] = None) -> List[Dict]:
        """
        Generate clean examples for few-shot prompting format.
        
        Args:
            content_brief: Content description to match
            num_examples: Number of examples to return
            category_filter: Filter by specific category
            
        Returns:
            List of clean example dictionaries
        """
        similar_articles = self.matcher.find_similar_articles(
            content_brief, 
            top_k=num_examples,
            category_filter=category_filter
        )
        
        examples = []
        for result in similar_articles:
            article = result['article']
            examples.append({
                'title': article['title'],
                'category': article['category'],
                'content': article['content'],
                'word_count': article['word_count'],
                'similarity': result['similarity'],
                'key_patterns': self._identify_style_patterns(article['content'])
            })
        
        return examples
    
    def generate_category_style_prompt(self, 
                                     category: str, 
                                     content_brief: str,
                                     num_examples: int = 3) -> str:
        """
        Generate a style prompt focused on a specific Jenosize category.
        
        Args:
            category: Jenosize category (Futurist, Marketing, Technology, etc.)
            content_brief: Content description
            num_examples: Number of examples from the category
            
        Returns:
            Category-focused style prompt
        """
        return self.generate_style_prompt(
            content_brief=content_brief,
            num_examples=num_examples,
            category_filter=category,
            include_jenosize_patterns=True
        )
    
    def _extract_content_preview(self, content: str, max_words: int) -> str:
        """Extract a meaningful preview of article content."""
        # Clean up content
        cleaned_content = re.sub(r'\s+', ' ', content).strip()
        
        # Try to get first paragraph or introduction
        paragraphs = cleaned_content.split('\n\n')
        if len(paragraphs) > 1 and len(paragraphs[0].split()) < max_words:
            preview = paragraphs[0]
            # Add second paragraph if there's room
            remaining_words = max_words - len(preview.split())
            if remaining_words > 20 and len(paragraphs) > 1:
                second_para_words = paragraphs[1].split()[:remaining_words]
                preview += "\n\n" + " ".join(second_para_words)
        else:
            # Just take first max_words
            words = cleaned_content.split()[:max_words]
            preview = " ".join(words)
        
        if len(cleaned_content.split()) > max_words:
            preview += "..."
        
        return preview
    
    def _identify_style_patterns(self, content: str) -> str:
        """Identify key Jenosize style patterns in content."""
        patterns = []
        
        # Check for common Jenosize opening phrases
        if "In today's digital era" in content:
            patterns.append("Digital era opening")
        if "digital transformation" in content.lower():
            patterns.append("Digital transformation focus")
        if any(phrase in content for phrase in ["In recent years", "The rapidly evolving", "Modern businesses"]):
            patterns.append("Industry context setting")
        
        # Check for structural elements
        if re.search(r'\d+\.', content):
            patterns.append("Numbered lists")
        if "Jenosize" in content:
            patterns.append("Brand integration")
        if any(word in content.lower() for word in ["strategy", "solution", "implementation"]):
            patterns.append("Business-focused language")
        
        # Check for call-to-action patterns
        if any(phrase in content for phrase in ["contact us", "Contact Us", "ready to help"]):
            patterns.append("Call-to-action")
        
        return ", ".join(patterns) if patterns else "Standard business writing"
    
    def _get_category_specific_instructions(self, category: str) -> str:
        """Get writing instructions specific to each Jenosize category."""
        instructions = {
            "Futurist": "   • Focus on emerging trends and future implications\n   • Include technology adoption and innovation themes\n   • Emphasize forward-thinking business strategies",
            
            "Marketing": "   • Emphasize practical marketing strategies and tactics\n   • Include case studies and campaign examples\n   • Focus on measurable business results and ROI",
            
            "Technology": "   • Explain technical concepts in business-friendly terms\n   • Include implementation considerations and best practices\n   • Focus on digital transformation and efficiency gains",
            
            "Consumer Insights": "   • Include customer behavior analysis and psychology\n   • Focus on actionable insights for business decisions\n   • Emphasize customer experience and satisfaction",
            
            "Experience": "   • Focus on user experience and customer journey\n   • Include experiential marketing and engagement strategies\n   • Emphasize emotional connection and brand loyalty",
            
            "Utility & Sustainability": "   • Include sustainability and environmental considerations\n   • Focus on long-term business value and responsibility\n   • Emphasize efficiency and resource optimization"
        }
        
        return instructions.get(category, "")
    
    def generate_comparative_prompt(self, 
                                  content_brief: str,
                                  compare_categories: List[str]) -> str:
        """
        Generate a prompt comparing styles across multiple categories.
        
        Args:
            content_brief: Content to generate
            compare_categories: List of categories to compare
            
        Returns:
            Comparative style prompt
        """
        prompt_parts = [
            f"Generate content about: {content_brief}",
            "",
            "Compare and blend the writing styles from these Jenosize categories:",
            ""
        ]
        
        for category in compare_categories:
            examples = self.matcher.find_articles_by_category(category, limit=2)
            if examples:
                prompt_parts.extend([
                    f"{category.upper()} STYLE:",
                    f"Example: {examples[0]['title']}",
                    f"Content preview: {self._extract_content_preview(examples[0]['content'], 100)}",
                    ""
                ])
        
        prompt_parts.extend([
            "Blend these styles to create content that:",
            "• Captures the best elements from each category",
            "• Maintains Jenosize's professional, forward-thinking tone",
            "• Provides practical value to business readers"
        ])
        
        return "\n".join(prompt_parts)