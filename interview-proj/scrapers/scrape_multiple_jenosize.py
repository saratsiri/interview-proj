#!/usr/bin/env python3
"""
Scrape Multiple Jenosize Articles
Build comprehensive training dataset from real Jenosize content
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import os
import time
from typing import List, Dict, Optional

def extract_jenosize_article(url: str) -> Optional[Dict]:
    """Extract content from a single Jenosize article"""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"📄 Scraping: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title from URL path and page
        url_parts = url.split('/')
        topic_slug = url_parts[-1] if url_parts else "unknown"
        category_slug = url_parts[-2] if len(url_parts) > 1 else "unknown"
        
        # Try to get actual title from page
        title = soup.title.text.strip() if soup.title else topic_slug.replace('-', ' ').title()
        
        # Get full page text
        full_text = soup.get_text()
        
        # Look for content patterns - try multiple approaches
        content_patterns = [
            r'(.*?)\s+In today.*?Contact Us',
            r'(.*?)\s+In the.*?Contact Us', 
            r'(.*?)\s+As we.*?Contact Us',
            r'(.*?)\s+The world.*?Contact Us',
            r'(.*?)\s+With.*?Contact Us'
        ]
        
        main_content = ""
        
        # Try to find the main article content
        for pattern in content_patterns:
            match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
            if match and len(match.group(0)) > 500:
                main_content = match.group(0)
                break
        
        # If patterns don't work, extract by finding content between title and footer
        if not main_content or len(main_content) < 300:
            # Find content start
            title_variations = [
                title,
                topic_slug.replace('-', ' '),
                topic_slug.replace('-', ' ').title()
            ]
            
            content_start = -1
            for title_var in title_variations:
                content_start = full_text.find(title_var)
                if content_start != -1:
                    # Look for actual article content after title
                    potential_starts = [
                        "In today",
                        "In the",
                        "As we", 
                        "The world",
                        "With the",
                        "Over the",
                        "Throughout"
                    ]
                    
                    for start_phrase in potential_starts:
                        phrase_pos = full_text.find(start_phrase, content_start)
                        if phrase_pos != -1 and phrase_pos - content_start < 200:
                            content_start = phrase_pos
                            break
                    break
            
            content_end = full_text.find('Contact Us')
            if content_end == -1:
                content_end = full_text.find('Loading...')
            if content_end == -1:
                content_end = content_start + 2000  # Take first 2000 chars if no end marker
            
            if content_start != -1:
                main_content = full_text[content_start:content_end]
        
        # Clean up the content
        if main_content:
            # Remove extra whitespace and clean text
            main_content = re.sub(r'[^\w\s.,!?;:()\-\'\"&]', ' ', main_content)
            main_content = re.sub(r'\s+', ' ', main_content)
            main_content = main_content.strip()
            
            # Remove common footer/navigation text
            cleanup_patterns = [
                r'Loading\.\.\.',
                r'Unbox Future Opportunities Together.*',
                r'Brief Us.*',
                r'Chat with Sales.*',
                r'Available Monday to Friday.*',
                r'JENOSIZE Co\.,Ltd\..*'
            ]
            
            for pattern in cleanup_patterns:
                main_content = re.sub(pattern, '', main_content, flags=re.DOTALL)
            
            main_content = main_content.strip()
        
        # Extract category from URL
        category_mapping = {
            'futurist': 'Futurist',
            'experience-the-new-world': 'Experience',
            'understand-people-and-consumer': 'Consumer Insights', 
            'transformation-and-technology': 'Technology',
            'utility-for-our-world': 'Utility & Sustainability',
            'real-time-marketing': 'Marketing'
        }
        
        category = category_mapping.get(category_slug, category_slug.replace('-', ' ').title())
        
        article_data = {
            'title': title,
            'url': url,
            'category': category,
            'topic_slug': topic_slug,
            'content': main_content,
            'word_count': len(main_content.split()) if main_content else 0,
            'author': 'Jenosize.com',
            'source': 'jenosize_website'
        }
        
        return article_data
        
    except Exception as e:
        print(f"❌ Error processing {url}: {e}")
        return None

def scrape_all_articles(urls: List[str]) -> List[Dict]:
    """Scrape all provided Jenosize articles"""
    
    articles = []
    
    for i, url in enumerate(urls, 1):
        print(f"\n📑 Processing article {i}/{len(urls)}")
        
        article_data = extract_jenosize_article(url)
        
        if article_data and article_data['content'] and article_data['word_count'] > 200:
            articles.append(article_data)
            print(f"✅ Successfully extracted: {article_data['title']}")
            print(f"   Word count: {article_data['word_count']}")
            print(f"   Category: {article_data['category']}")
        else:
            print(f"❌ Failed to extract meaningful content from {url}")
        
        # Be respectful with requests
        time.sleep(2)
    
    return articles

def analyze_jenosize_style(articles: List[Dict]) -> Dict:
    """Analyze writing style patterns from scraped articles"""
    
    analysis = {
        'total_articles': len(articles),
        'categories': {},
        'avg_word_count': 0,
        'common_phrases': [],
        'writing_patterns': [],
        'structural_elements': []
    }
    
    if not articles:
        return analysis
    
    # Calculate statistics
    word_counts = [article['word_count'] for article in articles]
    analysis['avg_word_count'] = sum(word_counts) // len(word_counts)
    analysis['word_count_range'] = f"{min(word_counts)}-{max(word_counts)}"
    
    # Analyze categories
    for article in articles:
        category = article['category']
        if category not in analysis['categories']:
            analysis['categories'][category] = 0
        analysis['categories'][category] += 1
    
    # Analyze common phrases and patterns
    all_content = ' '.join([article['content'].lower() for article in articles])
    
    # Common business/tech phrases
    common_business_phrases = [
        'in today', 'digital era', 'consumer', 'brand', 'strategy', 
        'technology', 'experience', 'future', 'innovation', 'market',
        'business', 'customer', 'digital transformation', 'ai', 'data'
    ]
    
    found_phrases = []
    for phrase in common_business_phrases:
        if phrase in all_content:
            count = all_content.count(phrase)
            if count > 1:  # Appears in multiple articles
                found_phrases.append(f"{phrase} ({count}x)")
    
    analysis['common_phrases'] = found_phrases
    
    # Analyze writing patterns
    patterns = []
    if 'in today' in all_content:
        patterns.append("Opens with current context ('In today's...')")
    if 'future' in all_content and 'trend' in all_content:
        patterns.append("Forward-looking perspective with trend analysis")
    if 'business' in all_content and 'strategy' in all_content:
        patterns.append("Business strategy focus")
    if 'customer' in all_content or 'consumer' in all_content:
        patterns.append("Customer/consumer-centric approach")
    
    analysis['writing_patterns'] = patterns
    
    return analysis

def main():
    """Main function to scrape multiple Jenosize articles"""
    
    # Article URLs provided
    urls = [
        "https://www.jenosize.com/en/ideas/real-time-marketing/event-marketing-strategy",  # Already have this one
        "https://www.jenosize.com/en/ideas/futurist/experiential-marketing-2030-trends",
        "https://www.jenosize.com/en/ideas/futurist/japan-ai-earthquake-disaster-response", 
        "https://www.jenosize.com/en/ideas/experience-the-new-world/sensory-experience-event-strategy",
        "https://www.jenosize.com/en/ideas/understand-people-and-consumer/single-customer-view",
        "https://www.jenosize.com/en/ideas/transformation-and-technology/smart-city-transformation",
        "https://www.jenosize.com/en/ideas/utility-for-our-world/esg-green-technology",
        "https://www.jenosize.com/en/ideas/utility-for-our-world/global-risks-business-preparedness",
        "https://www.jenosize.com/en/ideas/futurist/ai-search-marketing-strategies"
    ]
    
    print(f"🚀 Starting to scrape {len(urls)} Jenosize articles...")
    print("=" * 60)
    
    # Scrape all articles
    articles = scrape_all_articles(urls)
    
    if articles:
        # Save articles to JSON
        os.makedirs('data', exist_ok=True)
        
        with open('data/jenosize_training_articles.json', 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        
        # Analyze the content
        analysis = analyze_jenosize_style(articles)
        
        with open('data/jenosize_style_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print(f"\n📊 Scraping Results Summary:")
        print("=" * 60)
        print(f"✅ Successfully scraped: {len(articles)} articles")
        print(f"📈 Total words collected: {sum(a['word_count'] for a in articles):,}")
        print(f"📊 Average word count: {analysis['avg_word_count']}")
        print(f"📏 Word count range: {analysis['word_count_range']}")
        
        print(f"\n📋 Categories covered:")
        for category, count in analysis['categories'].items():
            print(f"  • {category}: {count} articles")
        
        print(f"\n🎯 Common phrases found:")
        for phrase in analysis['common_phrases'][:10]:
            print(f"  • {phrase}")
        
        print(f"\n✍️ Writing patterns identified:")
        for pattern in analysis['writing_patterns']:
            print(f"  • {pattern}")
        
        print(f"\n💾 Files saved:")
        print(f"  • data/jenosize_training_articles.json - Raw articles")
        print(f"  • data/jenosize_style_analysis.json - Style analysis")
        
        print(f"\n🎉 Training dataset ready for content generation system!")
        
        return articles
    else:
        print("❌ No articles were successfully scraped")
        return []

if __name__ == "__main__":
    main()