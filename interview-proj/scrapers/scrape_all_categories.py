#!/usr/bin/env python3
"""
Comprehensive scraper for all Jenosize article categories
Scrapes articles from all 5 remaining categories using Selenium
"""

import json
import time
import re
from typing import List, Dict, Optional, Tuple
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

class JenosizeAllCategoriesScraper:
    def __init__(self):
        self.base_url = "https://www.jenosize.com"
        
        # Category mappings
        self.categories = {
            "understand-people-and-consumer": "Consumer Insights",
            "transformation-and-technology": "Technology",
            "utility-for-our-world": "Utility & Sustainability",
            "real-time-marketing": "Marketing", 
            "experience-the-new-world": "Experience"
        }
        
        self.category_urls = [
            "https://www.jenosize.com/en/ideas/understand-people-and-consumer",
            "https://www.jenosize.com/en/ideas/transformation-and-technology",
            "https://www.jenosize.com/en/ideas/utility-for-our-world",
            "https://www.jenosize.com/en/ideas/real-time-marketing",
            "https://www.jenosize.com/en/ideas/experience-the-new-world"
        ]
        
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
    
    def extract_category_from_url(self, url: str) -> str:
        """Extract category name from URL"""
        for slug, category_name in self.categories.items():
            if slug in url:
                return category_name
        return "Unknown"
    
    def get_category_article_links(self, category_url: str) -> Tuple[List[str], str]:
        """Extract all article links from a category page using Selenium"""
        category_name = self.extract_category_from_url(category_url)
        print(f"🔍 Fetching articles from {category_name}: {category_url}")
        
        driver = self.setup_driver()
        if not driver:
            return [], category_name
        
        try:
            # Load the page
            driver.get(category_url)
            
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
            
            # Extract category slug from URL
            category_slug = category_url.split('/')[-1]
            
            # Strategy 1: Look for links containing the category slug
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    href = self.base_url + href
                
                # Check if this is an article link for this category
                if f'/ideas/{category_slug}/' in href and href != category_url:
                    # Clean URL
                    clean_url = href.split('?')[0].split('#')[0]
                    article_links.add(clean_url)
            
            # Strategy 2: Look in JSON-LD or script tags
            scripts = soup.find_all('script', type='application/json')
            for script in scripts:
                if script.string:
                    script_content = script.string
                    # Look for URLs in the JSON
                    pattern = f'/ideas/{category_slug}/([^"\']+)'
                    matches = re.findall(pattern, script_content)
                    for match in matches:
                        clean_match = match.split('?')[0].split('#')[0].strip()
                        if clean_match and clean_match != '':
                            full_url = f"{self.base_url}/en/ideas/{category_slug}/{clean_match}"
                            article_links.add(full_url)
            
            # Strategy 3: Look in all script tags for potential article slugs
            all_scripts = soup.find_all('script')
            for script in all_scripts:
                if script.string:
                    script_content = script.string
                    # Look for potential article URLs or slugs
                    patterns = [
                        f'"/ideas/{category_slug}/([^"]+)"',
                        f"'/ideas/{category_slug}/([^']+)'",
                        f'ideas/{category_slug}/([a-zA-Z0-9\\-]+)',
                        f'"{category_slug}/([^"]+)"'
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, script_content)
                        for match in matches:
                            clean_match = match.split('?')[0].split('#')[0].strip()
                            if clean_match and len(clean_match) > 3 and clean_match != category_slug:
                                # Clean up the slug
                                if clean_match.startswith('/'):
                                    clean_match = clean_match[1:]
                                if clean_match.endswith('/'):
                                    clean_match = clean_match[:-1]
                                
                                full_url = f"{self.base_url}/en/ideas/{category_slug}/{clean_match}"
                                article_links.add(full_url)
            
            article_links = list(article_links)
            
            print(f"✅ Found {len(article_links)} potential article links for {category_name}")
            
            # Display found links
            for i, link in enumerate(sorted(article_links), 1):
                print(f"  {i}. {link}")
            
            return article_links, category_name
            
        except Exception as e:
            print(f"❌ Error scraping {category_name}: {e}")
            return [], category_name
            
        finally:
            if driver:
                driver.quit()
    
    def verify_article_links(self, links: List[str], category_name: str) -> List[str]:
        """Verify that the discovered links are valid articles"""
        print(f"\n🔍 Verifying {len(links)} links for {category_name}...")
        
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
                
                time.sleep(0.5)  # Be respectful to the server
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
        
        print(f"✅ Verified {len(valid_links)} valid article links for {category_name}")
        return valid_links
    
    def extract_article_content(self, url: str, category_name: str) -> Optional[Dict]:
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
                "category": category_name,
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
    
    def scrape_all_categories(self, output_file: str = None) -> Dict[str, List[Dict]]:
        """Main method to scrape all category articles"""
        print("🚀 Starting comprehensive scraping of all article categories...")
        
        all_scraped_articles = {}
        total_articles = 0
        
        for category_url in self.category_urls:
            category_name = self.extract_category_from_url(category_url)
            print(f"\n{'='*60}")
            print(f"📚 PROCESSING CATEGORY: {category_name.upper()}")
            print(f"{'='*60}")
            
            # Get all article links for this category
            article_links, category_name = self.get_category_article_links(category_url)
            
            if not article_links:
                print(f"❌ No article links found for {category_name}")
                all_scraped_articles[category_name] = []
                continue
            
            # Verify links are valid
            valid_links = self.verify_article_links(article_links, category_name)
            
            if not valid_links:
                print(f"❌ No valid article links found for {category_name}")
                all_scraped_articles[category_name] = []
                continue
            
            print(f"\n📋 Scraping {len(valid_links)} articles from {category_name}...")
            
            # Scrape each article
            scraped_articles = []
            
            for i, url in enumerate(valid_links, 1):
                print(f"\n[{i}/{len(valid_links)}] Processing {category_name} article...")
                
                article_data = self.extract_article_content(url, category_name)
                if article_data:
                    scraped_articles.append(article_data)
                
                # Be respectful to the server
                time.sleep(2)
            
            all_scraped_articles[category_name] = scraped_articles
            total_articles += len(scraped_articles)
            
            print(f"\n✅ {category_name}: {len(scraped_articles)} articles scraped")
        
        print(f"\n{'='*60}")
        print(f"🎉 SCRAPING COMPLETE!")
        print(f"{'='*60}")
        
        # Save to file
        if output_file:
            os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
            
            # Flatten articles for saving
            all_articles_flat = []
            for category, articles in all_scraped_articles.items():
                all_articles_flat.extend(articles)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_articles_flat, f, indent=2, ensure_ascii=False)
            print(f"💾 All articles saved to: {output_file}")
        
        # Display comprehensive summary
        print(f"\n📊 COMPREHENSIVE SCRAPING SUMMARY:")
        print(f"Total categories processed: {len(self.category_urls)}")
        print(f"Total articles scraped: {total_articles}")
        
        total_words = 0
        for category, articles in all_scraped_articles.items():
            category_words = sum(article['word_count'] for article in articles)
            total_words += category_words
            print(f"  {category}: {len(articles)} articles ({category_words:,} words)")
        
        avg_words = total_words / total_articles if total_articles else 0
        print(f"\nTotal words: {total_words:,}")
        print(f"Average words per article: {avg_words:.1f}")
        
        return all_scraped_articles

def main():
    """Main function"""
    scraper = JenosizeAllCategoriesScraper()
    
    # Scrape all categories
    all_articles = scraper.scrape_all_categories(
        output_file="data/all_categories_articles.json"
    )
    
    return len([article for articles in all_articles.values() for article in articles])

if __name__ == "__main__":
    main()