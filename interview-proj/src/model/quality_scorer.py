"""Content quality scoring and validation system"""
import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    """Content quality score with breakdown"""
    overall_score: float
    executive_language: float
    data_driven: float
    forward_thinking: float
    authority_tone: float
    business_focus: float
    structure_score: float
    readability_score: float
    jenosize_style: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'overall_score': round(self.overall_score, 1),
            'breakdown': {
                'executive_language': round(self.executive_language, 1),
                'data_driven': round(self.data_driven, 1),
                'forward_thinking': round(self.forward_thinking, 1),
                'authority_tone': round(self.authority_tone, 1),
                'business_focus': round(self.business_focus, 1),
                'structure_score': round(self.structure_score, 1),
                'readability_score': round(self.readability_score, 1),
                'jenosize_style': round(self.jenosize_style, 1)
            },
            'grade': self.get_grade(),
            'recommendations': self.get_recommendations()
        }
    
    def get_grade(self) -> str:
        """Get letter grade for content"""
        if self.overall_score >= 90:
            return 'A+'
        elif self.overall_score >= 85:
            return 'A'
        elif self.overall_score >= 80:
            return 'B+'
        elif self.overall_score >= 75:
            return 'B'
        elif self.overall_score >= 70:
            return 'C+'
        elif self.overall_score >= 65:
            return 'C'
        else:
            return 'D'
    
    def get_recommendations(self) -> List[str]:
        """Get improvement recommendations"""
        recommendations = []
        
        if self.executive_language < 70:
            recommendations.append("Enhance executive vocabulary and C-suite perspective")
        if self.data_driven < 70:
            recommendations.append("Include more quantitative metrics and data points")
        if self.forward_thinking < 70:
            recommendations.append("Add future outlook and emerging trend analysis")
        if self.authority_tone < 70:
            recommendations.append("Use more confident, declarative statements")
        if self.business_focus < 70:
            recommendations.append("Strengthen business value proposition and ROI focus")
        if self.structure_score < 70:
            recommendations.append("Improve article structure with clear sections and headers")
        if self.readability_score < 70:
            recommendations.append("Enhance readability with shorter sentences and clearer language")
        if self.jenosize_style < 70:
            recommendations.append("Better align with Jenosize editorial style and tone")
            
        if not recommendations:
            recommendations.append("Excellent content quality - maintain current standards")
            
        return recommendations


class ContentQualityScorer:
    """Advanced content quality scoring system for Jenosize articles"""
    
    def __init__(self):
        # Define scoring criteria and patterns
        self.executive_terms = [
            'strategic', 'competitive', 'market leadership', 'organizations',
            'executives', 'c-suite', 'business leaders', 'decision makers',
            'enterprise', 'corporate', 'transformation', 'initiatives'
        ]
        
        self.data_driven_patterns = [
            r'\d+[-–—]\d+%',  # Range percentages like 25-40%
            r'\d+%',          # Single percentages
            r'\$\d+[kmb]?',   # Dollar amounts
            r'\d+x',          # Multipliers like 3x
            r'roi', r'return on investment', r'cost reduction',
            r'efficiency gains', r'productivity improvement'
        ]
        
        self.forward_thinking_terms = [
            'future', 'emerging', 'evolution', 'trajectory', 'next generation',
            'tomorrow', 'ahead', 'anticipated', 'projected', 'forecasted',
            'trends', 'outlook', 'roadmap', 'vision', 'innovative'
        ]
        
        self.authority_terms = [
            'must', 'will', 'requires', 'imperative', 'critical', 'essential',
            'should', 'need to', 'demands', 'necessitates', 'crucial',
            'fundamental', 'vital', 'key', 'primary'
        ]
        
        self.business_terms = [
            'revenue', 'roi', 'investment', 'operational', 'profitability',
            'market share', 'competitive advantage', 'cost', 'efficiency',
            'growth', 'performance', 'value creation', 'stakeholder'
        ]
        
        self.jenosize_patterns = [
            r'convergence of.*?innovation',
            r'unprecedented.*?opportunities',
            r'forward-thinking organizations',
            r'competitive landscape',
            r'market.*?positioning',
            r'strategic.*?imperatives'
        ]
        
        # Required structure elements
        self.required_sections = [
            'executive summary', 'strategic', 'implementation', 'future',
            'recommendations', 'conclusion', 'analysis', 'framework'
        ]
    
    def score_content(self, content: str, title: str = "", metadata: Dict = None) -> QualityScore:
        """Score content quality across multiple dimensions"""
        content_lower = content.lower()
        
        # Calculate individual scores
        executive_score = self._score_executive_language(content_lower)
        data_score = self._score_data_driven(content)
        forward_score = self._score_forward_thinking(content_lower)
        authority_score = self._score_authority_tone(content_lower)
        business_score = self._score_business_focus(content_lower)
        structure_score = self._score_structure(content, title)
        readability_score = self._score_readability(content)
        jenosize_score = self._score_jenosize_style(content_lower)
        
        # Calculate weighted overall score
        weights = {
            'executive': 0.15,
            'data': 0.15,
            'forward': 0.15,
            'authority': 0.10,
            'business': 0.15,
            'structure': 0.10,
            'readability': 0.10,
            'jenosize': 0.10
        }
        
        overall = (
            executive_score * weights['executive'] +
            data_score * weights['data'] +
            forward_score * weights['forward'] +
            authority_score * weights['authority'] +
            business_score * weights['business'] +
            structure_score * weights['structure'] +
            readability_score * weights['readability'] +
            jenosize_score * weights['jenosize']
        )
        
        return QualityScore(
            overall_score=overall,
            executive_language=executive_score,
            data_driven=data_score,
            forward_thinking=forward_score,
            authority_tone=authority_score,
            business_focus=business_score,
            structure_score=structure_score,
            readability_score=readability_score,
            jenosize_style=jenosize_score
        )
    
    def _score_executive_language(self, content: str) -> float:
        """Score executive-level language usage"""
        total_words = len(content.split())
        executive_count = sum(1 for term in self.executive_terms if term in content)
        
        # Normalize by content length (aim for 1-2% executive terms)
        density = (executive_count / total_words) * 100 if total_words > 0 else 0
        
        if density >= 1.5:
            return 100
        elif density >= 1.0:
            return 90
        elif density >= 0.8:
            return 80
        elif density >= 0.5:
            return 70
        elif density >= 0.3:
            return 60
        else:
            return max(0, density * 200)  # Scale up small densities
    
    def _score_data_driven(self, content: str) -> float:
        """Score data-driven content with metrics and statistics"""
        matches = 0
        for pattern in self.data_driven_patterns:
            matches += len(re.findall(pattern, content, re.IGNORECASE))
        
        # Expect 3-8 data points in a good business article
        if matches >= 8:
            return 100
        elif matches >= 6:
            return 90
        elif matches >= 4:
            return 80
        elif matches >= 2:
            return 70
        elif matches >= 1:
            return 60
        else:
            return 30
    
    def _score_forward_thinking(self, content: str) -> float:
        """Score forward-thinking perspective and future focus"""
        found_terms = sum(1 for term in self.forward_thinking_terms if term in content)
        
        if found_terms >= 8:
            return 100
        elif found_terms >= 6:
            return 90
        elif found_terms >= 4:
            return 80
        elif found_terms >= 3:
            return 70
        elif found_terms >= 2:
            return 60
        else:
            return found_terms * 30
    
    def _score_authority_tone(self, content: str) -> float:
        """Score authoritative tone and confident language"""
        found_terms = sum(1 for term in self.authority_terms if term in content)
        
        if found_terms >= 10:
            return 100
        elif found_terms >= 8:
            return 90
        elif found_terms >= 6:
            return 80
        elif found_terms >= 4:
            return 70
        elif found_terms >= 2:
            return 60
        else:
            return found_terms * 30
    
    def _score_business_focus(self, content: str) -> float:
        """Score business and commercial focus"""
        found_terms = sum(1 for term in self.business_terms if term in content)
        
        if found_terms >= 10:
            return 100
        elif found_terms >= 8:
            return 90
        elif found_terms >= 6:
            return 80
        elif found_terms >= 4:
            return 70
        elif found_terms >= 2:
            return 60
        else:
            return found_terms * 30
    
    def _score_structure(self, content: str, title: str) -> float:
        """Score article structure and organization"""
        content_lower = content.lower()
        score = 0
        
        # Check for section headers (##)
        section_count = content.count('##')
        if section_count >= 6:
            score += 30
        elif section_count >= 4:
            score += 25
        elif section_count >= 2:
            score += 20
        else:
            score += section_count * 10
        
        # Check for required sections
        required_found = sum(1 for section in self.required_sections 
                           if section in content_lower)
        score += (required_found / len(self.required_sections)) * 40
        
        # Check for bullet points and lists
        if content.count('-') >= 5 or content.count('•') >= 5:
            score += 15
        elif content.count('-') >= 3:
            score += 10
        
        # Check for professional title structure
        if title and ':' in title and len(title) > 50:
            score += 15
        
        return min(100, score)
    
    def _score_readability(self, content: str) -> float:
        """Score readability and clarity"""
        sentences = content.split('.')
        paragraphs = content.split('\n\n')
        words = content.split()
        
        if not sentences or not words:
            return 0
        
        # Average sentence length (aim for 15-25 words)
        avg_sentence_length = len(words) / len(sentences)
        sentence_score = 100 - abs(20 - avg_sentence_length) * 3
        sentence_score = max(0, min(100, sentence_score))
        
        # Paragraph length distribution
        paragraph_lengths = [len(p.split()) for p in paragraphs if p.strip()]
        if paragraph_lengths:
            avg_paragraph_length = sum(paragraph_lengths) / len(paragraph_lengths)
            # Aim for 80-150 words per paragraph
            paragraph_score = 100 - abs(115 - avg_paragraph_length) * 0.5
            paragraph_score = max(0, min(100, paragraph_score))
        else:
            paragraph_score = 50
        
        # Overall readability
        return (sentence_score * 0.6 + paragraph_score * 0.4)
    
    def _score_jenosize_style(self, content: str) -> float:
        """Score alignment with Jenosize editorial style"""
        pattern_matches = 0
        for pattern in self.jenosize_patterns:
            if re.search(pattern, content):
                pattern_matches += 1
        
        # Base score from pattern matching
        base_score = (pattern_matches / len(self.jenosize_patterns)) * 60
        
        # Bonus for specific Jenosize phrases
        jenosize_phrases = [
            'strategic imperatives',
            'competitive positioning',
            'market leadership',
            'forward-thinking organizations',
            'unprecedented opportunities'
        ]
        
        phrase_bonus = sum(10 for phrase in jenosize_phrases if phrase in content)
        
        return min(100, base_score + phrase_bonus)

    def get_improvement_suggestions(self, score: QualityScore, content: str) -> List[str]:
        """Get specific improvement suggestions based on content analysis"""
        suggestions = []
        
        if score.executive_language < 80:
            suggestions.append(
                "Add more executive-level terminology like 'strategic imperatives', "
                "'competitive positioning', and 'organizational capabilities'"
            )
        
        if score.data_driven < 80:
            suggestions.append(
                "Include specific metrics and data points such as percentage improvements, "
                "ROI figures, or market growth statistics"
            )
        
        if score.structure_score < 80:
            if content.count('##') < 4:
                suggestions.append("Add more section headers (##) to improve article structure")
            if 'executive summary' not in content.lower():
                suggestions.append("Include an 'Executive Summary' section")
        
        if score.jenosize_style < 80:
            suggestions.append(
                "Better incorporate Jenosize signature phrases like 'convergence of market dynamics' "
                "and 'forward-thinking organizations'"
            )
        
        return suggestions


# Global quality scorer instance
quality_scorer = ContentQualityScorer()