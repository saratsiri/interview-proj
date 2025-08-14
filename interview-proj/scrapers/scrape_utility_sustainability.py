#!/usr/bin/env python3
"""
Scraper for Utility Consumer Insights Sustainability articles (utility-for-our-world)
Based on the working Futurist scraper
"""

import json
import time
import re
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import requests
from bs4 import BeautifulSoup
import os

class JenosizeConsumerInsightsScraper:
    def __init__(self):
        self.base_url = "https://www.jenosize.com"
        self.category_url = "https://www.jenosize.com/en/ideas/utility-for-our-world"
        self.category_name = "Utility Consumer Insights Sustainability"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Setup Chrome options
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument(f'--user-agent={self.headers["User-Agent"]}')
        self.chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        
    def setup_driver(self):
        """Setup Chrome WebDriver"""
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self.chrome_options)
            return driver
        except Exception as e:
            print(f"❌ Error setting up Chrome driver: {e}")
            return None
    
    def get_all_article_links_selenium(self) -> List[str]:
        """Extract all article links using Selenium"""
        print(f"🔍 Fetching article links with Selenium from: {self.category_url}")
        
        driver = self.setup_driver()
        if not driver:
            return []
        
        try:
            # Load the page
            driver.get(self.category_url)
            
            # Wait for content to load
            print("⏳ Waiting for dynamic content to load...")
            time.sleep(5)
            
            # Try to wait for article links to appear
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "a"))
                )
            except:
                print("⚠️  Timeout waiting for links, proceeding with current content...")
            
            # Get page source after JS execution
            page_source = driver.page_source
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Look for article links
            article_links = set()
            
            # Strategy 1: Look for links containing '/utility-for-our-world/'
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    href = self.base_url + href
                
                # Check if this is a consumer insights article link
                if '/ideas/utility-for-our-world/' in href and href != self.category_url:
                    # Clean URL
                    clean_url = href.split('?')[0].split('#')[0]
                    article_links.add(clean_url)
            
            # Strategy 2: Look in JSON-LD or script tags
            scripts = soup.find_all('script', type='application/json')
            for script in scripts:
                if script.string:
                    script_content = script.string
                    # Look for URLs in the JSON
                    consumer_matches = re.findall(r'/ideas/utility-for-our-world/([^"\']+)', script_content)
                    for match in consumer_matches:
                        clean_match = match.split('?')[0].split('#')[0].strip()
                        if clean_match and clean_match != '':
                            full_url = f"{self.base_url}/en/ideas/utility-for-our-world/{clean_match}"
                            article_links.add(full_url)
            
            # Strategy 3: Look in all script tags for potential article slugs
            all_scripts = soup.find_all('script')
            for script in all_scripts:
                if script.string:
                    script_content = script.string
                    # Look for potential article URLs or slugs
                    patterns = [
                        r'"/ideas/utility-for-our-world/([^"]+)"',
                        r"'/ideas/utility-for-our-world/([^']+)'",
                        r'ideas/utility-for-our-world/([a-zA-Z0-9\-]+)',
                        r'"utility-for-our-world/([^"]+)"'
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, script_content)
                        for match in matches:
                            clean_match = match.split('?')[0].split('#')[0].strip()
                            if clean_match and len(clean_match) > 3 and clean_match != 'utility-for-our-world':
                                # Clean up the slug
                                if clean_match.startswith('/'):
                                    clean_match = clean_match[1:]
                                if clean_match.endswith('/'):
                                    clean_match = clean_match[:-1]
                                
                                full_url = f"{self.base_url}/en/ideas/utility-for-our-world/{clean_match}"
                                article_links.add(full_url)
            
            article_links = list(article_links)
            
            print(f"✅ Found {len(article_links)} potential article links")
            
            # Display found links
            for i, link in enumerate(sorted(article_links), 1):
                print(f"  {i}. {link}")
            
            return article_links
            
        except Exception as e:
            print(f"❌ Error with Selenium scraping: {e}")
            return []
            
        finally:
            if driver:
                driver.quit()
    
    def verify_article_links(self, links: List[str]) -> List[str]:
        """Verify that the discovered links are valid articles"""
        print(f"\n🔍 Verifying {len(links)} discovered links...")
        
        valid_links = []
        
        for i, url in enumerate(links, 1):
            try:
                print(f"[{i}/{len(links)}] Checking: {url}")
                response = self.session.head(url, timeout=10)
                
                if response.status_code == 200:
                    valid_links.append(url)
                    print(f"  ✅ Valid")
                else:
                    print(f"  ❌ Status {response.status_code}")
                
                time.sleep(1)  # Be respectful to the server
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        print(f"\n✅ Verified {len(valid_links)} valid article links")
        return valid_links
    
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
                'title',
                '[class*="title"]'
            ]
            
            for selector in title_selectors:
                title_elem = soup.select_one(selector)
                if title_elem and title_elem.get_text(strip=True):
                    title = title_elem.get_text(strip=True)
                    # Clean up title
                    title = title.replace('| Jenosize', '').replace('- Jenosize', '').strip()
                    if len(title) > 5:  # Reasonable title length
                        break
            
            if not title or len(title) < 5:
                # Try meta og:title as fallback
                og_title = soup.find('meta', property='og:title')
                if og_title:
                    title = og_title.get('content', '').strip()
            
            if not title:
                title = "Untitled Article"
            
            # Extract main content
            content_text = ""
            
            # Try multiple strategies for content extraction
            content_selectors = [
                'article',
                '.article-content',
                '.post-content',
                '.content',
                'main',
                '[role="main"]'
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # Remove unwanted elements
                    for element in content_elem(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                        element.decompose()
                    
                    content_text = content_elem.get_text(separator='\n', strip=True)
                    if len(content_text) > 200:  # Substantial content
                        break
            
            # Fallback: get all paragraphs
            if len(content_text) < 200:
                paragraphs = soup.find_all('p')
                content_parts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:
                        content_parts.append(text)
                content_text = '\n\n'.join(content_parts)
            
            # Clean content
            content_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', content_text)
            content_text = content_text.strip()
            
            # Validate content
            if len(content_text) < 100:
                print(f"  ⚠️  Content too short ({len(content_text)} chars)")
                return None
            
            # Extract topic slug from URL
            topic_slug = url.split('/')[-1] if url.split('/')[-1] else "unknown"
            
            word_count = len(content_text.split())
            
            article_data = {
                "title": title,
                "url": url,
                "category": self.category_name,
                "topic_slug": topic_slug,
                "content": content_text,
                "word_count": word_count,
                "author": "Jenosize.com",
                "source": "jenosize_website"
            }
            
            print(f"  ✅ Scraped: {title[:50]}... ({word_count} words)")
            return article_data
            
        except Exception as e:
            print(f"  ❌ Error scraping {url}: {e}")
            return None
    
    def scrape_all_articles(self, output_file: str = None) -> List[Dict]:
        """Main method to scrape all consumer insights articles"""
        print("🚀 Starting Utility Consumer Insights Sustainability articles scraping...")
        
        # Get all article links using Selenium
        all_links = self.get_all_article_links_selenium()
        
        if not all_links:
            print("❌ No article links found")
            return []
        
        # Verify links are valid
        valid_links = self.verify_article_links(all_links)
        
        if not valid_links:
            print("❌ No valid article links found")
            return []
        
        print(f"\n📋 Scraping {len(valid_links)} valid articles...")
        
        # Scrape each article
        scraped_articles = []
        
        for i, url in enumerate(valid_links, 1):
            print(f"\n[{i}/{len(valid_links)}] Processing article...")
            
            article_data = self.extract_article_content(url)
            if article_data:
                scraped_articles.append(article_data)
            
            # Be respectful to the server
            time.sleep(2)
        
        print(f"\n✅ Successfully scraped {len(scraped_articles)} articles")
        
        # Save to file
        if output_file:
            os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(scraped_articles, f, indent=2, ensure_ascii=False)
            print(f"💾 Articles saved to: {output_file}")
        
        return scraped_articles

def main():
    """Main function"""
    scraper = JenosizeConsumerInsightsScraper()
    
    # Scrape all articles
    articles = scraper.scrape_all_articles(
        output_file="data/utility_sustainability_articles.json"
    )
    
    # Display summary
    if articles:
        total_words = sum(article['word_count'] for article in articles)
        avg_words = total_words / len(articles)
        
        print(f"\n📊 SCRAPING SUMMARY:")
        print(f"Total articles scraped: {len(articles)}")
        print(f"Total words: {total_words:,}")
        print(f"Average words per article: {avg_words:.1f}")
        print(f"Category: Utility Consumer Insights Sustainability")
        
        print(f"\n📝 SCRAPED ARTICLES:")
        for i, article in enumerate(articles, 1):
            print(f"  {i}. {article['title']} ({article['word_count']} words)")
            print(f"     {article['url']}")
    
    return len(articles)

if __name__ == "__main__":
    main()