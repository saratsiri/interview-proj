#!/usr/bin/env python3
"""
Jenosize Ideas Scraper
Scrapes articles from Jenosize Ideas section for training data
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JenosizeScraper:
    def __init__(self, base_url: str = "https://www.jenosize.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.articles = []

    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page"""
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            logger.info(f"Successfully fetched: {url}")
            return soup
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def find_article_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find all article links on a page"""
        article_links = []
        
        # Look for various link patterns that might indicate articles
        potential_selectors = [
            'a[href*="/ideas/"]',
            'a[href*="/article/"]', 
            'a[href*="/post/"]',
            'a[href*="/insight/"]',
            '.article-link',
            '.post-link', 
            '.idea-link',
            'article a',
            '.content-item a',
            '.blog-post a'
        ]
        
        for selector in potential_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    if full_url not in article_links:
                        article_links.append(full_url)
                        logger.info(f"Found potential article: {full_url}")
        
        return article_links

    def extract_article_content(self, url: str) -> Optional[Dict]:
        """Extract article content from a URL"""
        soup = self.get_page(url)
        if not soup:
            return None

        article_data = {
            'url': url,
            'title': '',
            'content': '',
            'category': '',
            'tags': [],
            'publication_date': '',
            'author': '',
            'word_count': 0
        }

        # Extract title
        title_selectors = ['h1', '.article-title', '.post-title', 'title', '.headline']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.text.strip():
                article_data['title'] = title_elem.text.strip()
                break

        # Extract main content 
        content_selectors = [
            '.article-content',
            '.post-content', 
            '.content',
            'article',
            '.main-content',
            '.entry-content',
            'main'
        ]
        
        content_text = []
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # Remove script and style elements
                for script in content_elem(["script", "style"]):
                    script.decompose()
                content_text.append(content_elem.get_text(strip=True))
                break

        article_data['content'] = ' '.join(content_text)
        article_data['word_count'] = len(article_data['content'].split())

        # Extract category/tags
        tag_selectors = ['.category', '.tag', '.topic', '.keywords']
        for selector in tag_selectors:
            tags = soup.select(selector)
            for tag in tags:
                if tag.text.strip():
                    article_data['tags'].append(tag.text.strip())

        # Extract publication date
        date_selectors = ['.date', '.published', '.post-date', 'time']
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                article_data['publication_date'] = date_elem.text.strip()
                break

        # Only return if we found meaningful content
        if article_data['title'] and len(article_data['content']) > 100:
            return article_data
        
        return None

    def scrape_ideas_section(self) -> List[Dict]:
        """Main scraping method for Jenosize Ideas section"""
        ideas_urls = [
            f"{self.base_url}/en/ideas",
            f"{self.base_url}/ideas",
            f"{self.base_url}/en/insights", 
            f"{self.base_url}/insights",
            f"{self.base_url}/en/blog",
            f"{self.base_url}/blog"
        ]

        all_article_links = []
        
        # Try different URLs to find the ideas section
        for url in ideas_urls:
            soup = self.get_page(url)
            if soup:
                links = self.find_article_links(soup, self.base_url)
                all_article_links.extend(links)
                
                # Look for pagination or "load more" buttons
                pagination_links = soup.select('a[href*="page"]')
                for link in pagination_links:
                    page_url = urljoin(self.base_url, link.get('href'))
                    page_soup = self.get_page(page_url) 
                    if page_soup:
                        page_links = self.find_article_links(page_soup, self.base_url)
                        all_article_links.extend(page_links)

        # Remove duplicates
        unique_links = list(set(all_article_links))
        logger.info(f"Found {len(unique_links)} unique article links")

        # Extract content from each article
        articles = []
        for link in unique_links[:20]:  # Limit to first 20 articles for now
            logger.info(f"Processing article: {link}")
            article_data = self.extract_article_content(link)
            if article_data:
                articles.append(article_data)
                logger.info(f"Successfully extracted: {article_data['title']}")
            
            time.sleep(1)  # Be respectful with requests

        return articles

    def save_articles(self, articles: List[Dict], filename: str = "data/jenosize_scraped_articles.json"):
        """Save scraped articles to JSON file"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(articles)} articles to {filename}")

def main():
    """Main scraping function"""
    logger.info("Starting Jenosize Ideas scraper...")
    
    scraper = JenosizeScraper()
    articles = scraper.scrape_ideas_section()
    
    if articles:
        scraper.save_articles(articles)
        
        # Print summary
        print(f"\n📊 Scraping Results:")
        print(f"Total articles scraped: {len(articles)}")
        print(f"Average word count: {sum(a['word_count'] for a in articles) // len(articles) if articles else 0}")
        print(f"\nSample titles:")
        for article in articles[:5]:
            print(f"- {article['title']}")
        
        return articles
    else:
        logger.warning("No articles found. The website might use dynamic loading or have different structure.")
        return []

if __name__ == "__main__":
    main()