#!/usr/bin/env python3
"""
Merge all 12 scraped Futurist articles with existing training database
This will give us comprehensive Futurist content for training
"""

import json
import time

def load_json_file(filepath):
    """Load JSON data from file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        return []
    except Exception as e:
        print(f"❌ Error loading {filepath}: {e}")
        return []

def save_json_file(data, filepath):
    """Save JSON data to file"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved to: {filepath}")
        return True
    except Exception as e:
        print(f"❌ Error saving to {filepath}: {e}")
        return False

def normalize_url_for_comparison(url):
    """Normalize URL for duplicate detection"""
    return url.strip().lower().rstrip('/')

def standardize_article_format(article, source="futurist_scraper"):
    """Standardize article format to match existing database structure"""
    
    # Extract slug from URL if available
    topic_slug = ""
    if 'url' in article:
        url_parts = article['url'].split('/')
        if len(url_parts) > 0:
            topic_slug = url_parts[-1]
    
    standardized = {
        "title": article.get('title', 'Untitled'),
        "url": article.get('url', ''),
        "category": "Futurist",  # Force all to be Futurist category
        "topic_slug": topic_slug,
        "content": article.get('content', ''),
        "word_count": article.get('word_count', len(article.get('content', '').split())),
        "author": "Jenosize.com",
        "source": "jenosize_website"
    }
    
    return standardized

def merge_all_futurist_articles():
    """Merge all futurist articles with existing training database"""
    print("🔄 Merging ALL futurist articles with training database...")
    
    # Load existing training data
    existing_articles = load_json_file("data/jenosize_training_articles.json")
    print(f"📚 Loaded {len(existing_articles)} existing articles")
    
    # Load newly scraped futurist articles (all 12)
    new_futurist_articles = load_json_file("data/all_futurist_articles.json")
    print(f"🆕 Loaded {len(new_futurist_articles)} new futurist articles")
    
    if not existing_articles and not new_futurist_articles:
        print("❌ No data to merge")
        return False
    
    # Create a set of existing article URLs for duplicate detection
    existing_urls = set()
    for article in existing_articles:
        if 'url' in article and article['url']:
            normalized_url = normalize_url_for_comparison(article['url'])
            existing_urls.add(normalized_url)
    
    # Track statistics
    added_count = 0
    duplicate_count = 0
    updated_count = 0
    
    # Process new articles
    for new_article in new_futurist_articles:
        url = new_article.get('url', '')
        normalized_url = normalize_url_for_comparison(url)
        
        # Check if this article already exists
        existing_index = -1
        for i, existing_article in enumerate(existing_articles):
            if 'url' in existing_article:
                existing_normalized = normalize_url_for_comparison(existing_article['url'])
                if existing_normalized == normalized_url:
                    existing_index = i
                    break
        
        # Standardize format
        standardized_article = standardize_article_format(new_article)
        
        if existing_index >= 0:
            # Update existing article with new content (newer scrape might have better content)
            old_word_count = existing_articles[existing_index].get('word_count', 0)
            new_word_count = standardized_article.get('word_count', 0)
            
            if new_word_count > old_word_count:
                print(f"  🔄 Updated: {standardized_article['title'][:50]}... ({old_word_count} → {new_word_count} words)")
                existing_articles[existing_index] = standardized_article
                updated_count += 1
            else:
                print(f"  ⚠️  Duplicate (keeping existing): {standardized_article['title'][:50]}...")
                duplicate_count += 1
        else:
            # Add new article
            existing_articles.append(standardized_article)
            existing_urls.add(normalized_url)
            print(f"  ✅ Added: {standardized_article['title'][:50]}... ({standardized_article['word_count']} words)")
            added_count += 1
    
    # Sort articles by category then by title
    existing_articles.sort(key=lambda x: (x.get('category', ''), x.get('title', '')))
    
    # Save merged data
    if save_json_file(existing_articles, "data/jenosize_training_articles.json"):
        print(f"✅ Successfully merged all futurist articles!")
        
        # Generate comprehensive summary
        print(f"\n📊 MERGE SUMMARY:")
        print(f"Articles added: {added_count}")
        print(f"Articles updated: {updated_count}")
        print(f"Duplicates skipped: {duplicate_count}")
        print(f"Total articles in database: {len(existing_articles)}")
        
        # Show category breakdown
        categories = {}
        for article in existing_articles:
            cat = article.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"\n📂 ARTICLES BY CATEGORY:")
        for category, count in sorted(categories.items()):
            print(f"  {category}: {count}")
        
        # Special focus on Futurist articles
        futurist_articles = [a for a in existing_articles if a.get('category') == 'Futurist']
        print(f"\n🎯 FUTURIST ARTICLES ({len(futurist_articles)} total):")
        for i, article in enumerate(futurist_articles, 1):
            print(f"  {i:2d}. {article['title']} ({article['word_count']} words)")
        
        # Word count statistics
        total_words = sum(article.get('word_count', 0) for article in existing_articles)
        futurist_words = sum(article.get('word_count', 0) for article in futurist_articles)
        avg_words = total_words / len(existing_articles) if existing_articles else 0
        avg_futurist_words = futurist_words / len(futurist_articles) if futurist_articles else 0
        
        print(f"\n📝 WORD STATISTICS:")
        print(f"Total words: {total_words:,}")
        print(f"Futurist words: {futurist_words:,}")
        print(f"Average words per article: {avg_words:.1f}")
        print(f"Average words per futurist article: {avg_futurist_words:.1f}")
        
        return True
    
    return False

def main():
    """Main function"""
    success = merge_all_futurist_articles()
    
    if success:
        print("\n🎉 All futurist articles successfully merged!")
        print("The training database now contains comprehensive Futurist content.")
        print("Ready for advanced content generation with authentic Jenosize style!")
    else:
        print("\n❌ Merge failed!")
    
    return success

if __name__ == "__main__":
    main()