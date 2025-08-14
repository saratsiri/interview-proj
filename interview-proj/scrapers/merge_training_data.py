#!/usr/bin/env python3
"""
Merge newly scraped Futurist articles with existing training database
Avoid duplicates and update the consolidated training data
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

def normalize_article_for_comparison(article):
    """Normalize article data for duplicate detection"""
    # Use URL as primary key for comparison
    if 'url' in article:
        return article['url'].strip().lower()
    
    # Fallback to title if no URL
    if 'title' in article:
        return article['title'].strip().lower()
    
    return None

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
        "category": article.get('category', 'Futurist'),
        "topic_slug": topic_slug,
        "content": article.get('content', ''),
        "word_count": article.get('word_count', len(article.get('content', '').split())),
        "author": "Jenosize.com",
        "source": "jenosize_website"
    }
    
    return standardized

def merge_training_data():
    """Merge futurist articles with existing training database"""
    print("🔄 Merging training data...")
    
    # Load existing training data
    existing_articles = load_json_file("data/jenosize_training_articles.json")
    print(f"📚 Loaded {len(existing_articles)} existing articles")
    
    # Load newly scraped futurist articles
    new_articles = load_json_file("data/futurist_articles.json")
    print(f"🆕 Loaded {len(new_articles)} new futurist articles")
    
    if not existing_articles and not new_articles:
        print("❌ No data to merge")
        return
    
    # Create a set of existing article identifiers for duplicate detection
    existing_identifiers = set()
    for article in existing_articles:
        identifier = normalize_article_for_comparison(article)
        if identifier:
            existing_identifiers.add(identifier)
    
    # Track statistics
    added_count = 0
    duplicate_count = 0
    
    # Process new articles
    for new_article in new_articles:
        identifier = normalize_article_for_comparison(new_article)
        
        if identifier and identifier in existing_identifiers:
            print(f"  ⚠️  Duplicate found: {new_article.get('title', 'Unknown')[:50]}...")
            duplicate_count += 1
            continue
        
        # Standardize format and add to existing articles
        standardized_article = standardize_article_format(new_article)
        existing_articles.append(standardized_article)
        
        if identifier:
            existing_identifiers.add(identifier)
        
        print(f"  ✅ Added: {standardized_article['title'][:50]}...")
        added_count += 1
    
    # Sort articles by category then by title
    existing_articles.sort(key=lambda x: (x.get('category', ''), x.get('title', '')))
    
    # Save merged data
    if save_json_file(existing_articles, "data/jenosize_training_articles.json"):
        print(f"✅ Successfully merged training data!")
        
        # Generate summary statistics
        print(f"\n📊 MERGE SUMMARY:")
        print(f"Articles added: {added_count}")
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
        
        # Show word count statistics
        total_words = sum(article.get('word_count', 0) for article in existing_articles)
        avg_words = total_words / len(existing_articles) if existing_articles else 0
        
        print(f"\n📝 WORD STATISTICS:")
        print(f"Total words: {total_words:,}")
        print(f"Average words per article: {avg_words:.1f}")
        
        return True
    
    return False

def main():
    """Main function"""
    success = merge_training_data()
    
    if success:
        print("\n🎉 Training data merge completed successfully!")
        print("The updated database is ready for model training.")
    else:
        print("\n❌ Training data merge failed!")
    
    return success

if __name__ == "__main__":
    main()