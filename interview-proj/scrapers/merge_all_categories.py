#!/usr/bin/env python3
"""
Merge all scraped category articles into the comprehensive training database
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

def merge_all_category_articles():
    """Merge all category articles with existing training database"""
    print("🔄 Merging ALL category articles with training database...")
    
    # Load existing training data
    existing_articles = load_json_file("data/jenosize_training_articles.json")
    print(f"📚 Loaded {len(existing_articles)} existing articles")
    
    # List of all scraped category files
    category_files = [
        ("data/consumer_insights_articles.json", "Consumer Insights"),
        ("data/technology_articles.json", "Technology"), 
        ("data/utility_sustainability_articles.json", "Utility & Sustainability")
    ]
    
    # Track statistics
    total_added = 0
    total_updated = 0
    total_duplicates = 0
    
    # Create a set of existing article URLs for duplicate detection
    existing_urls = set()
    for article in existing_articles:
        if 'url' in article and article['url']:
            normalized_url = normalize_url_for_comparison(article['url'])
            existing_urls.add(normalized_url)
    
    # Process each category file
    for category_file, category_name in category_files:
        print(f"\n📂 Processing {category_name} articles...")
        category_articles = load_json_file(category_file)
        
        if not category_articles:
            print(f"  ⚠️  No articles found in {category_file}")
            continue
            
        print(f"  📄 Found {len(category_articles)} articles to process")
        
        category_added = 0
        category_updated = 0
        category_duplicates = 0
        
        for article in category_articles:
            url = article.get('url', '')
            normalized_url = normalize_url_for_comparison(url)
            
            # Check if this article already exists
            existing_index = -1
            for i, existing_article in enumerate(existing_articles):
                if 'url' in existing_article:
                    existing_normalized = normalize_url_for_comparison(existing_article['url'])
                    if existing_normalized == normalized_url:
                        existing_index = i
                        break
            
            if existing_index >= 0:
                # Update existing article if new content is better
                old_word_count = existing_articles[existing_index].get('word_count', 0)
                new_word_count = article.get('word_count', 0)
                
                if new_word_count > old_word_count:
                    print(f"    🔄 Updated: {article['title'][:40]}... ({old_word_count} → {new_word_count} words)")
                    existing_articles[existing_index] = article
                    category_updated += 1
                else:
                    print(f"    ⚠️  Duplicate: {article['title'][:40]}...")
                    category_duplicates += 1
            else:
                # Add new article
                existing_articles.append(article)
                existing_urls.add(normalized_url)
                print(f"    ✅ Added: {article['title'][:40]}... ({article['word_count']} words)")
                category_added += 1
        
        print(f"  📊 {category_name}: +{category_added} added, {category_updated} updated, {category_duplicates} duplicates")
        total_added += category_added
        total_updated += category_updated
        total_duplicates += category_duplicates
    
    # Sort articles by category then by title
    existing_articles.sort(key=lambda x: (x.get('category', ''), x.get('title', '')))
    
    # Save merged data
    if save_json_file(existing_articles, "data/jenosize_training_articles.json"):
        print(f"\n✅ Successfully merged all category articles!")
        
        # Generate comprehensive summary
        print(f"\n📊 COMPREHENSIVE MERGE SUMMARY:")
        print(f"Articles added: {total_added}")
        print(f"Articles updated: {total_updated}")
        print(f"Duplicates skipped: {total_duplicates}")
        print(f"Total articles in database: {len(existing_articles)}")
        
        # Show category breakdown
        categories = {}
        for article in existing_articles:
            cat = article.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"\n📂 FINAL DATABASE BY CATEGORY:")
        for category, count in sorted(categories.items()):
            print(f"  {category}: {count}")
        
        # Word count statistics
        total_words = sum(article.get('word_count', 0) for article in existing_articles)
        avg_words = total_words / len(existing_articles) if existing_articles else 0
        
        print(f"\n📝 COMPREHENSIVE WORD STATISTICS:")
        print(f"Total words: {total_words:,}")
        print(f"Average words per article: {avg_words:.1f}")
        
        # Category word breakdown
        print(f"\n📊 WORDS BY CATEGORY:")
        for category, count in sorted(categories.items()):
            category_articles = [a for a in existing_articles if a.get('category') == category]
            category_words = sum(article.get('word_count', 0) for article in category_articles)
            avg_category_words = category_words / count if count else 0
            print(f"  {category}: {category_words:,} words ({avg_category_words:.1f} avg)")
        
        return True
    
    return False

def main():
    """Main function"""
    success = merge_all_category_articles()
    
    if success:
        print("\n🎉 ALL CATEGORY ARTICLES SUCCESSFULLY MERGED!")
        print("The training database now contains comprehensive content from all Jenosize categories.")
        print("Ready for advanced content generation with complete authentic Jenosize knowledge!")
    else:
        print("\n❌ Merge failed!")
    
    return success

if __name__ == "__main__":
    main()