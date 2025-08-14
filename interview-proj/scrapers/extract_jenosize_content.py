#!/usr/bin/env python3
"""Extract Jenosize article content"""

import requests
from bs4 import BeautifulSoup
import json
import re
import os

def extract_jenosize_article():
    url = 'https://www.jenosize.com/en/ideas/real-time-marketing/event-marketing-strategy'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract the full article
    article_data = {
        'title': 'What Is Event Marketing? Connecting Brands with Customers',
        'url': url,
        'category': 'real-time-marketing',
        'tags': ['Art', 'Marketing', 'Business'],
        'author': 'Jenosize.com'
    }

    # Get full text and clean it
    full_text = soup.get_text()

    # Find the main article content by looking for the pattern
    content_start = full_text.find('What Is Event Marketing? Building Brands Through Experience')
    content_end = full_text.find('Contact Us', content_start)

    if content_start != -1:
        if content_end != -1:
            main_content = full_text[content_start:content_end]
        else:
            main_content = full_text[content_start:content_start+3000]
        
        # Clean up the content
        main_content = re.sub(r'[^\w\s.,!?;:()\-]', ' ', main_content)
        main_content = re.sub(r'\s+', ' ', main_content)
        main_content = main_content.strip()
        
        article_data['content'] = main_content
        article_data['word_count'] = len(main_content.split())
        
        print('Successfully extracted Jenosize article:')
        print(f'Title: {article_data["title"]}')
        print(f'Word count: {article_data["word_count"]}')
        print(f'Category: {article_data["category"]}')
        print(f'Tags: {article_data["tags"]}')
        
        print('\n--- Article Content ---')
        print(main_content)
        
        # Save the article
        os.makedirs('data', exist_ok=True)
        with open('data/jenosize_sample_article.json', 'w') as f:
            json.dump(article_data, f, indent=2)
        print('\n✅ Saved to data/jenosize_sample_article.json')
        
        return article_data
    else:
        print('Could not find article content')
        return None

if __name__ == "__main__":
    extract_jenosize_article()