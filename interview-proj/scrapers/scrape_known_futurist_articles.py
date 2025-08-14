#!/usr/bin/env python3
"""
Scraper for specific known Futurist articles
Since the main page uses dynamic loading, we'll work with known article URLs
and expand from there
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict, Optional
import re
import os

class JenosizeFuturistScraper:
    def __init__(self):
        self.base_url = "https://www.jenosize.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Known futurist article URLs provided by user
        self.known_futurist_urls = [
            "https://www.jenosize.com/en/ideas/futurist/digital-twin-business-model",
            "https://www.jenosize.com/en/ideas/futurist/experiential-marketing-2030-trends"
        ]
        
        # We can also try to discover more by pattern matching
        self.potential_futurist_topics = [
            "ai-revolution",
            "future-of-work", 
            "metaverse-business",
            "blockchain-future",
            "sustainable-innovation",
            "digital-transformation",
            "automation-trends",
            "virtual-reality-business",
            "iot-future",
            "5g-impact",
            "quantum-computing",
            "robotics-future"
        ]
    
    def extract_article_content(self, url: str) -> Optional[Dict]:
        """Extract content from a single article"""
        print(f"📄 Scraping: {url}")
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            if response.status_code != 200:
                print(f"  ❌ Status code: {response.status_code}")
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title - try multiple strategies
            title = None
            
            # Strategy 1: Look for h1 tags
            h1_tags = soup.find_all('h1')
            for h1 in h1_tags:
                text = h1.get_text(strip=True)
                if text and len(text) > 5:  # Reasonable title length
                    title = text
                    break
            
            # Strategy 2: Look in page title
            if not title:
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    # Clean up title (remove site name, etc.)
                    title = title.replace('| Jenosize', '').replace('- Jenosize', '').strip()
            
            # Strategy 3: Look for meta og:title
            if not title:
                og_title = soup.find('meta', property='og:title')
                if og_title:
                    title = og_title.get('content', '').strip()
            
            if not title:
                title = "Untitled Article"
            
            # Extract main content - try multiple strategies
            content_text = ""
            
            # Strategy 1: Look for article tag
            article_tag = soup.find('article')
            if article_tag:
                # Remove unwanted elements
                for element in article_tag(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    element.decompose()
                content_text = article_tag.get_text(separator='\n', strip=True)
            
            # Strategy 2: Look for main content areas
            if len(content_text) < 200:
                content_selectors = [
                    '.article-content',
                    '.post-content', 
                    '.content',
                    'main',
                    '[role="main"]',
                    '.main-content'
                ]
                
                for selector in content_selectors:
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        for element in content_elem(['script', 'style', 'nav', 'header', 'footer']):
                            element.decompose()
                        content_text = content_elem.get_text(separator='\n', strip=True)
                        if len(content_text) > 200:
                            break
            
            # Strategy 3: Get all paragraphs as fallback
            if len(content_text) < 200:
                paragraphs = soup.find_all('p')
                content_parts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:  # Ignore very short paragraphs
                        content_parts.append(text)
                content_text = '\n\n'.join(content_parts)
            
            # Clean up the content
            content_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', content_text)
            content_text = content_text.strip()
            
            # Validate content quality
            if len(content_text) < 100:
                print(f"  ⚠️  Content too short ({len(content_text)} chars), skipping")
                return None
            
            # Extract any metadata
            category = "Futurist"
            word_count = len(content_text.split())
            
            article_data = {
                "title": title,
                "content": content_text,
                "url": url,
                "category": category,
                "word_count": word_count,
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            print(f"  ✅ Scraped: {title[:60]}... ({word_count} words)")
            return article_data
            
        except requests.RequestException as e:
            print(f"  ❌ Request error for {url}: {e}")
            return None
        except Exception as e:
            print(f"  ❌ Error scraping {url}: {e}")
            return None
    
    def try_discover_more_articles(self) -> List[str]:
        """Try to discover more futurist articles by testing common URL patterns"""
        print("🔍 Attempting to discover more futurist articles...")
        
        discovered_urls = []
        
        for topic in self.potential_futurist_topics:
            test_url = f"https://www.jenosize.com/en/ideas/futurist/{topic}"
            
            try:
                response = self.session.head(test_url, timeout=10)
                if response.status_code == 200:
                    discovered_urls.append(test_url)
                    print(f"  ✅ Found: {test_url}")
                elif response.status_code == 404:
                    print(f"  ❌ Not found: {topic}")
                else:
                    print(f"  ⚠️  Status {response.status_code}: {topic}")
                
                time.sleep(0.5)  # Be respectful to the server
                
            except Exception as e:
                print(f"  ❌ Error testing {topic}: {e}")
        
        print(f"🎯 Discovered {len(discovered_urls)} additional articles")
        return discovered_urls
    
    def scrape_futurist_articles(self, output_file: str = None) -> List[Dict]:
        """Scrape known and discovered futurist articles"""
        print("🚀 Starting Futurist articles scraping...")
        
        # Start with known URLs
        all_urls = self.known_futurist_urls.copy()
        
        # Try to discover more
        discovered_urls = self.try_discover_more_articles()
        all_urls.extend(discovered_urls)
        
        # Remove duplicates
        all_urls = list(set(all_urls))
        
        print(f"📋 Total articles to scrape: {len(all_urls)}")
        
        # Scrape each article
        scraped_articles = []
        
        for i, url in enumerate(all_urls, 1):
            print(f"\n[{i}/{len(all_urls)}] Processing article...")
            
            article_data = self.extract_article_content(url)
            if article_data:
                scraped_articles.append(article_data)
            
            # Be respectful to the server
            time.sleep(2)
        
        print(f"\n✅ Successfully scraped {len(scraped_articles)} futurist articles")
        
        # Save to file if specified
        if output_file:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(scraped_articles, f, indent=2, ensure_ascii=False)
            print(f"💾 Articles saved to: {output_file}")
        
        return scraped_articles

def main():
    """Main function to run the scraper"""
    scraper = JenosizeFuturistScraper()
    
    # Scrape all futurist articles
    articles = scraper.scrape_futurist_articles(
        output_file="data/futurist_articles.json"
    )
    
    # Display summary
    if articles:
        total_words = sum(article['word_count'] for article in articles)
        avg_words = total_words / len(articles)
        
        print(f"\n📊 SCRAPING SUMMARY:")
        print(f"Total articles: {len(articles)}")
        print(f"Total words: {total_words:,}")
        print(f"Average words per article: {avg_words:.1f}")
        print(f"Category: Futurist")
        
        # Show titles
        print(f"\n📝 SCRAPED ARTICLES:")
        for i, article in enumerate(articles, 1):
            print(f"  {i}. {article['title']} ({article['word_count']} words)")
    
    return len(articles)

if __name__ == "__main__":
    main()