#!/usr/bin/env python3
"""
Jenosize Specific Article Scraper
Scrapes specific Jenosize article for training data analysis
"""

import requests
from bs4 import BeautifulSoup
import json
import logging
from typing import Dict, Optional
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def scrape_jenosize_article(url: str) -> Optional[Dict]:
    """Scrape specific Jenosize article"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        logger.info(f"Fetching: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        article_data = {
            'url': url,
            'title': '',
            'content': '',
            'sections': [],
            'category': '',
            'tags': [],
            'author': '',
            'publication_date': '',
            'word_count': 0,
            'writing_style_notes': []
        }
        
        # Extract title - try multiple selectors
        title_selectors = [
            'h1',
            '.article-title', 
            '.post-title',
            '.title',
            '.headline',
            'title',
            '[class*="title"]',
            '[class*="heading"]'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.text.strip():
                title_text = title_elem.text.strip()
                if len(title_text) > 10 and not title_text.startswith('Jenosize'):
                    article_data['title'] = title_text
                    logger.info(f"Found title: {title_text}")
                    break
        
        # Extract main content - try multiple approaches
        content_selectors = [
            'main',
            '.article-content',
            '.post-content',
            '.content',
            'article',
            '.main-content',
            '.entry-content',
            '[class*="content"]',
            '[class*="article"]',
            '[class*="post"]'
        ]
        
        content_parts = []
        
        for selector in content_selectors:
            content_elems = soup.select(selector)
            for elem in content_elems:
                if elem:
                    # Remove unwanted elements
                    for unwanted in elem.find_all(['script', 'style', 'nav', 'header', 'footer', '.navigation']):
                        unwanted.decompose()
                    
                    # Get text content
                    text_content = elem.get_text(separator=' ', strip=True)
                    if len(text_content) > 100:  # Only meaningful content
                        content_parts.append(text_content)
        
        # Remove duplicates and join content
        unique_content = []
        for content in content_parts:
            if content not in unique_content:
                unique_content.append(content)
        
        article_data['content'] = ' '.join(unique_content)
        
        # Extract sections/headings
        heading_selectors = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        for selector in heading_selectors:
            headings = soup.select(selector)
            for heading in headings:
                heading_text = heading.text.strip()
                if heading_text and len(heading_text) > 3:
                    article_data['sections'].append({
                        'level': selector,
                        'text': heading_text
                    })
        
        # Extract tags/categories
        tag_selectors = [
            '.tag', '.category', '.topic', '.keyword', 
            '[class*="tag"]', '[class*="category"]', '[class*="topic"]'
        ]
        
        for selector in tag_selectors:
            tags = soup.select(selector)
            for tag in tags:
                tag_text = tag.text.strip()
                if tag_text and tag_text not in article_data['tags']:
                    article_data['tags'].append(tag_text)
        
        # Extract author
        author_selectors = [
            '.author', '.by-author', '.writer', 
            '[class*="author"]', '[class*="writer"]'
        ]
        
        for selector in author_selectors:
            author_elem = soup.select_one(selector)
            if author_elem:
                article_data['author'] = author_elem.text.strip()
                break
        
        # Extract publication date
        date_selectors = [
            '.date', '.published', '.post-date', 'time', 
            '[class*="date"]', '[datetime]'
        ]
        
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                date_text = date_elem.text.strip()
                if date_text:
                    article_data['publication_date'] = date_text
                    break
                # Try datetime attribute
                datetime_attr = date_elem.get('datetime')
                if datetime_attr:
                    article_data['publication_date'] = datetime_attr
                    break
        
        # Calculate word count
        if article_data['content']:
            article_data['word_count'] = len(article_data['content'].split())
        
        # Extract URL path for category
        url_parts = url.split('/')
        if 'ideas' in url_parts:
            ideas_index = url_parts.index('ideas')
            if ideas_index + 1 < len(url_parts):
                article_data['category'] = url_parts[ideas_index + 1]
        
        # Analyze writing style
        if article_data['content']:
            content_lower = article_data['content'].lower()
            
            # Check for business/marketing language
            business_terms = ['strategy', 'marketing', 'brand', 'customer', 'business', 'digital', 'engagement']
            found_terms = [term for term in business_terms if term in content_lower]
            if found_terms:
                article_data['writing_style_notes'].append(f"Business-focused with terms: {', '.join(found_terms)}")
            
            # Check for educational tone
            educational_indicators = ['what is', 'how to', 'understanding', 'learn', 'guide']
            found_educational = [ind for ind in educational_indicators if ind in content_lower]
            if found_educational:
                article_data['writing_style_notes'].append("Educational/explanatory tone")
            
            # Check sentence structure
            sentences = article_data['content'].split('.')
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
            article_data['writing_style_notes'].append(f"Average sentence length: {avg_sentence_length:.1f} words")
        
        return article_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing {url}: {e}")
        return None

def main():
    """Main function to scrape the specific article"""
    url = "https://www.jenosize.com/en/ideas/real-time-marketing/event-marketing-strategy"
    
    logger.info("Starting specific Jenosize article scrape...")
    
    article_data = scrape_jenosize_article(url)
    
    if article_data and article_data['content']:
        # Save the scraped article
        os.makedirs('data', exist_ok=True)
        
        with open('data/jenosize_sample_article.json', 'w', encoding='utf-8') as f:
            json.dump(article_data, f, indent=2, ensure_ascii=False)
        
        # Print analysis
        print(f"\n📄 Jenosize Article Analysis:")
        print(f"Title: {article_data['title']}")
        print(f"URL: {article_data['url']}")
        print(f"Category: {article_data['category']}")
        print(f"Word Count: {article_data['word_count']}")
        print(f"Sections Found: {len(article_data['sections'])}")
        print(f"Tags: {', '.join(article_data['tags'])}")
        print(f"Author: {article_data['author']}")
        print(f"Publication Date: {article_data['publication_date']}")
        
        print(f"\n📝 Content Preview (first 300 chars):")
        print(f"{article_data['content'][:300]}...")
        
        print(f"\n🎯 Writing Style Notes:")
        for note in article_data['writing_style_notes']:
            print(f"- {note}")
        
        print(f"\n📋 Article Sections:")
        for section in article_data['sections'][:5]:  # First 5 sections
            print(f"- {section['level'].upper()}: {section['text']}")
        
        print(f"\n✅ Article saved to data/jenosize_sample_article.json")
        return article_data
    else:
        print("❌ Failed to extract meaningful content from the article")
        return None

if __name__ == "__main__":
    main()