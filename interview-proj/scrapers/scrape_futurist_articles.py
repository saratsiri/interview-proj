#!/usr/bin/env python3
"""
Scraper for Jenosize Futurist articles
Extracts all article links from the futurist section and scrapes their content
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict, Optional
import re
from urllib.parse import urljoin, urlparse
import os

class JenosizeFuturistScraper:
    def __init__(self):
        self.base_url = "https://www.jenosize.com"
        self.futurist_url = "https://www.jenosize.com/en/ideas/futurist"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def get_article_links(self) -> List[str]:
        """Extract all article links from the futurist section"""
        print(f"🔍 Fetching article links from: {self.futurist_url}")
        
        try:
            response = self.session.get(self.futurist_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all article links - they should contain '/ideas/futurist/' in the URL
            article_links = []
            
            # Look for links that match the pattern
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    href = urljoin(self.base_url, href)
                
                # Check if this is a futurist article link
                if '/ideas/futurist/' in href and href != self.futurist_url:
                    # Remove any query parameters or fragments
                    clean_url = href.split('?')[0].split('#')[0]
                    if clean_url not in article_links:
                        article_links.append(clean_url)
            
            print(f"✅ Found {len(article_links)} article links")
            
            # Print the links for verification
            for i, link in enumerate(article_links, 1):
                print(f"  {i}. {link}")
            
            return article_links
            
        except Exception as e:
            print(f"❌ Error fetching article links: {e}")
            return []
    
    def extract_article_content(self, url: str) -> Optional[Dict]:
        """Extract content from a single article"""
        print(f"📄 Scraping: {url}")
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = None
            title_selectors = [
                'h1',
                '.article-title',
                '.post-title',
                '[class*="title"]',
                'title'
            ]
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem and title_elem.get_text(strip=True):
                    title = title_elem.get_text(strip=True)
                    break
            
            if not title:
                title = "Untitled Article"
            
            # Extract main content
            content_text = ""
            
            # Try different content selectors
            content_selectors = [
                '.article-content',
                '.post-content',
                '.content',
                'article',
                '.main-content',
                '[class*="content"]'
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # Remove script and style elements
                    for script in content_elem(["script", "style", "nav", "header", "footer"]):
                        script.decompose()
                    
                    content_text = content_elem.get_text(separator='\n', strip=True)
                    if len(content_text) > 200:  # Only accept if substantial content
                        break
            
            # Fallback: get all paragraph text
            if len(content_text) < 200:
                paragraphs = soup.find_all('p')
                content_text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            
            # Clean up the content
            content_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', content_text)
            content_text = content_text.strip()
            
            # Extract category (always 'Futurist' for this scraper)
            category = "Futurist"
            
            # Calculate word count
            word_count = len(content_text.split())
            
            article_data = {
                "title": title,
                "content": content_text,
                "url": url,
                "category": category,
                "word_count": word_count,
                "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            print(f"  ✅ Scraped: {title[:50]}... ({word_count} words)")
            return article_data
            
        except Exception as e:
            print(f"  ❌ Error scraping {url}: {e}")
            return None
    
    def scrape_all_futurist_articles(self, output_file: str = None) -> List[Dict]:
        """Scrape all articles from the futurist section"""
        print("🚀 Starting Futurist articles scraping...")
        
        # Get all article links
        article_links = self.get_article_links()
        
        if not article_links:
            print("❌ No article links found")
            return []
        
        # Scrape each article
        scraped_articles = []
        
        for i, link in enumerate(article_links, 1):
            print(f"\n[{i}/{len(article_links)}] Processing article...")
            
            article_data = self.extract_article_content(link)
            if article_data:
                scraped_articles.append(article_data)
            
            # Be respectful to the server
            time.sleep(2)
        
        print(f"\n✅ Successfully scraped {len(scraped_articles)} articles")
        
        # Save to file if specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(scraped_articles, f, indent=2, ensure_ascii=False)
            print(f"💾 Articles saved to: {output_file}")
        
        return scraped_articles

def main():
    """Main function to run the scraper"""
    scraper = JenosizeFuturistScraper()
    
    # Scrape all futurist articles
    articles = scraper.scrape_all_futurist_articles(
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