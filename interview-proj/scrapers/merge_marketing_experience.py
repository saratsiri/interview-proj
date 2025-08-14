#!/usr/bin/env python3
"""
Merge the newly scraped Marketing and Experience articles into the comprehensive database
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

def merge_marketing_experience_articles():
    """Merge Marketing and Experience articles with existing training database"""
    print("🔄 Merging Marketing and Experience articles with training database...")
    
    # Load existing training data
    existing_articles = load_json_file("data/jenosize_training_articles.json")
    print(f"📚 Loaded {len(existing_articles)} existing articles")
    
    # Load newly scraped articles
    marketing_articles = load_json_file("data/marketing_articles.json")
    experience_articles = load_json_file("data/experience_articles.json")
    
    print(f"🆕 Found {len(marketing_articles)} new Marketing articles")
    print(f"🆕 Found {len(experience_articles)} new Experience articles")
    
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
    
    # Process Marketing articles
    print(f"\n📂 Processing Marketing articles...")
    for article in marketing_articles:
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
                print(f"  🔄 Updated: {article['title'][:50]}... ({old_word_count} → {new_word_count} words)")
                existing_articles[existing_index] = article
                total_updated += 1
            else:
                print(f"  ⚠️  Duplicate: {article['title'][:50]}...")
                total_duplicates += 1
        else:
            # Add new article
            existing_articles.append(article)
            existing_urls.add(normalized_url)
            print(f"  ✅ Added: {article['title'][:50]}... ({article['word_count']} words)")
            total_added += 1
    
    # Process Experience articles
    print(f"\n📂 Processing Experience articles...")
    for article in experience_articles:
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
                print(f"  🔄 Updated: {article['title'][:50]}... ({old_word_count} → {new_word_count} words)")
                existing_articles[existing_index] = article
                total_updated += 1
            else:
                print(f"  ⚠️  Duplicate: {article['title'][:50]}...")
                total_duplicates += 1
        else:
            # Add new article
            existing_articles.append(article)
            existing_urls.add(normalized_url)
            print(f"  ✅ Added: {article['title'][:50]}... ({article['word_count']} words)")
            total_added += 1
    
    # Sort articles by category then by title
    existing_articles.sort(key=lambda x: (x.get('category', ''), x.get('title', '')))
    
    # Save merged data
    if save_json_file(existing_articles, "data/jenosize_training_articles.json"):
        print(f"\n✅ Successfully merged Marketing and Experience articles!")
        
        # Generate comprehensive summary
        print(f"\n📊 MERGE SUMMARY:")
        print(f"Articles added: {total_added}")
        print(f"Articles updated: {total_updated}")
        print(f"Duplicates skipped: {total_duplicates}")
        print(f"Total articles in database: {len(existing_articles)}")
        
        # Show category breakdown
        categories = {}
        for article in existing_articles:
            cat = article.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        print(f"\n📂 UPDATED DATABASE BY CATEGORY:")
        for category, count in sorted(categories.items()):
            print(f"  {category}: {count}")
        
        # Word count statistics
        total_words = sum(article.get('word_count', 0) for article in existing_articles)
        avg_words = total_words / len(existing_articles) if existing_articles else 0
        
        print(f"\n📝 UPDATED WORD STATISTICS:")
        print(f"Total words: {total_words:,}")
        print(f"Average words per article: {avg_words:.1f}")
        
        # Show Marketing and Experience stats specifically
        marketing_articles_final = [a for a in existing_articles if a.get('category') == 'Marketing']
        experience_articles_final = [a for a in existing_articles if a.get('category') == 'Experience']
        
        print(f"\n🎯 CATEGORY HIGHLIGHTS:")
        print(f"Marketing articles: {len(marketing_articles_final)} ({sum(a.get('word_count', 0) for a in marketing_articles_final):,} words)")
        print(f"Experience articles: {len(experience_articles_final)} ({sum(a.get('word_count', 0) for a in experience_articles_final):,} words)")
        
        return True
    
    return False

def main():
    """Main function"""
    success = merge_marketing_experience_articles()
    
    if success:
        print("\n🎉 MARKETING AND EXPERIENCE ARTICLES SUCCESSFULLY MERGED!")
        print("The training database now has comprehensive coverage of all categories!")
    else:
        print("\n❌ Merge failed!")
    
    return success

if __name__ == "__main__":
    main()