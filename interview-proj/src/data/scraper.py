"""Data scraper for collecting training articles"""
import json
from typing import List, Dict
from datetime import datetime

class JenosizeContentScraper:
    """Scraper for collecting business trend articles"""
    
    def __init__(self):
        self.data_sources = ["Sample Business Articles"]
    
    def get_sample_data(self) -> List[Dict]:
        """Return sample training data for demo"""
        sample_articles = [
            {
                "title": "AI Revolutionizing Healthcare in 2025",
                "content": "Artificial intelligence is transforming healthcare through predictive analytics, personalized medicine, and automated diagnostics. Healthcare providers are leveraging AI to improve patient outcomes while reducing costs. The integration of machine learning algorithms has enabled early disease detection and more accurate treatment recommendations.",
                "category": "Technology",
                "keywords": ["AI", "healthcare", "digital transformation", "innovation"],
                "date": datetime.now().isoformat()
            },
            {
                "title": "Sustainable Business Practices for the Future",
                "content": "Companies worldwide are adopting sustainable practices to meet environmental goals and consumer demands. From renewable energy adoption to circular economy models, businesses are reimagining their operations. This shift not only benefits the planet but also drives long-term profitability and brand loyalty.",
                "category": "Sustainability",
                "keywords": ["sustainability", "ESG", "green business", "corporate responsibility"],
                "date": datetime.now().isoformat()
            },
            {
                "title": "The Rise of Remote Work Technologies",
                "content": "Remote work has become a permanent fixture in the modern workplace. Organizations are investing in collaboration tools, cybersecurity, and digital infrastructure. This transformation is reshaping office culture and creating new opportunities for global talent acquisition.",
                "category": "Business Strategy",
                "keywords": ["remote work", "digital workplace", "collaboration", "technology"],
                "date": datetime.now().isoformat()
            }
        ]
        return sample_articles
    
    def save_data(self, articles: List[Dict], filepath: str = "data/raw/articles.json"):
        """Save articles to file"""
        with open(filepath, 'w') as f:
            json.dump(articles, f, indent=2)
        print(f"Saved {len(articles)} articles to {filepath}")