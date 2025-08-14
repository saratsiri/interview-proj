#!/usr/bin/env python3
"""
Article Style Matcher for Jenosize Content Generation
Adapted for our existing codebase with 68 high-quality Jenosize articles
"""

import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple, Optional
import pickle
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JenosizeArticleStyleMatcher:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the Jenosize Article Style Matcher.
        
        Args:
            model_name: Sentence transformer model for embeddings
        """
        logger.info(f"Initializing with model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.articles = []
        self.embeddings = None
        self.is_fitted = False
        self.embeddings_cache_path = "data/jenosize_embeddings.pkl"
        
    def load_jenosize_articles(self, json_file: str = "data/jenosize_training_articles.json") -> None:
        """
        Load articles from our Jenosize training database.
        
        Args:
            json_file: Path to the Jenosize articles JSON file
        """
        logger.info(f"Loading Jenosize articles from: {json_file}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.articles = []
            for i, article in enumerate(data):
                processed_article = {
                    'id': i,
                    'title': article.get('title', f'Article {i+1}'),
                    'content': article.get('content', ''),
                    'category': article.get('category', 'Unknown'),
                    'word_count': article.get('word_count', len(article.get('content', '').split())),
                    'url': article.get('url', ''),
                    'topic_slug': article.get('topic_slug', ''),
                    'author': article.get('author', 'Jenosize.com'),
                    'source': article.get('source', 'jenosize_website')
                }
                self.articles.append(processed_article)
            
            logger.info(f"✅ Loaded {len(self.articles)} Jenosize articles")
            
            # Display category breakdown
            categories = {}
            total_words = 0
            for article in self.articles:
                cat = article['category']
                categories[cat] = categories.get(cat, 0) + 1
                total_words += article['word_count']
            
            logger.info(f"📊 Total words: {total_words:,}")
            logger.info("📂 Category breakdown:")
            for category, count in sorted(categories.items()):
                category_words = sum(a['word_count'] for a in self.articles if a['category'] == category)
                logger.info(f"  {category}: {count} articles ({category_words:,} words)")
                
        except FileNotFoundError:
            logger.error(f"❌ Jenosize articles file not found: {json_file}")
            raise
        except Exception as e:
            logger.error(f"❌ Error loading articles: {e}")
            raise
    
    def fit(self, force_recompute: bool = False) -> None:
        """
        Create embeddings for all Jenosize articles.
        
        Args:
            force_recompute: Force recomputation even if cached embeddings exist
        """
        if not self.articles:
            raise ValueError("No articles loaded. Call load_jenosize_articles() first.")
        
        # Check for cached embeddings
        if not force_recompute and os.path.exists(self.embeddings_cache_path):
            logger.info("📁 Loading cached embeddings...")
            try:
                self.load_embeddings(self.embeddings_cache_path)
                return
            except Exception as e:
                logger.warning(f"⚠️ Failed to load cached embeddings: {e}")
                logger.info("🔄 Computing fresh embeddings...")
        
        logger.info("🧠 Creating embeddings for Jenosize articles...")
        article_texts = [article['content'] for article in self.articles]
        
        # Create embeddings with progress bar
        self.embeddings = self.model.encode(
            article_texts,
            show_progress_bar=True,
            batch_size=8,
            convert_to_numpy=True
        )
        
        self.is_fitted = True
        logger.info(f"✅ Created embeddings: {self.embeddings.shape}")
        
        # Cache embeddings for future use
        self.save_embeddings(self.embeddings_cache_path)
    
    def find_similar_articles(self, 
                            query_text: str, 
                            top_k: int = 3,
                            min_similarity: float = 0.1,
                            category_filter: Optional[str] = None,
                            word_count_range: Optional[Tuple[int, int]] = None) -> List[Dict]:
        """
        Find the most stylistically similar Jenosize articles to the query.
        
        Args:
            query_text: Content description or sample text to match against
            top_k: Number of similar articles to return
            min_similarity: Minimum cosine similarity threshold
            category_filter: Filter by specific category (e.g., 'Futurist', 'Marketing')
            word_count_range: Tuple of (min_words, max_words) for filtering
            
        Returns:
            List of dictionaries containing article data and similarity scores
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")
        
        logger.info(f"🔍 Finding articles similar to: '{query_text[:50]}...'")
        
        # Create embedding for query
        query_embedding = self.model.encode([query_text], convert_to_numpy=True)
        
        # Calculate similarities
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        
        # Apply filters
        valid_indices = []
        for i, similarity in enumerate(similarities):
            article = self.articles[i]
            
            # Similarity threshold
            if similarity < min_similarity:
                continue
            
            # Category filter
            if category_filter and article['category'] != category_filter:
                continue
            
            # Word count filter
            if word_count_range:
                min_words, max_words = word_count_range
                if not (min_words <= article['word_count'] <= max_words):
                    continue
            
            valid_indices.append(i)
        
        # Sort by similarity (descending)
        valid_indices = sorted(valid_indices, key=lambda x: similarities[x], reverse=True)
        
        # Return top k results
        results = []
        for rank, idx in enumerate(valid_indices[:top_k], 1):
            results.append({
                'article': self.articles[idx].copy(),
                'similarity': float(similarities[idx]),
                'rank': rank
            })
        
        logger.info(f"✅ Found {len(results)} matching articles")
        for result in results:
            logger.info(f"  {result['rank']}. {result['article']['title'][:50]}... "
                       f"(similarity: {result['similarity']:.3f}, "
                       f"category: {result['article']['category']})")
        
        return results
    
    def find_articles_by_category(self, category: str, limit: int = None) -> List[Dict]:
        """
        Get all articles from a specific category.
        
        Args:
            category: Category name (e.g., 'Futurist', 'Marketing')
            limit: Maximum number of articles to return
            
        Returns:
            List of articles from the specified category
        """
        category_articles = [
            article for article in self.articles 
            if article['category'] == category
        ]
        
        if limit:
            category_articles = category_articles[:limit]
        
        logger.info(f"📂 Found {len(category_articles)} articles in category: {category}")
        return category_articles
    
    def get_category_statistics(self) -> Dict[str, Dict]:
        """Get detailed statistics for each category."""
        stats = {}
        
        for article in self.articles:
            category = article['category']
            if category not in stats:
                stats[category] = {
                    'count': 0,
                    'total_words': 0,
                    'articles': []
                }
            
            stats[category]['count'] += 1
            stats[category]['total_words'] += article['word_count']
            stats[category]['articles'].append({
                'title': article['title'],
                'word_count': article['word_count'],
                'topic_slug': article['topic_slug']
            })
        
        # Calculate averages
        for category in stats:
            stats[category]['avg_words'] = stats[category]['total_words'] / stats[category]['count']
        
        return stats
    
    def save_embeddings(self, filepath: str) -> None:
        """Save embeddings and articles to disk for faster loading."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            data = {
                'articles': self.articles,
                'embeddings': self.embeddings,
                'model_name': self.model.get_sentence_embedding_dimension(),
                'version': '1.0'
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
            
            logger.info(f"💾 Saved embeddings to: {filepath}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save embeddings: {e}")
    
    def load_embeddings(self, filepath: str) -> None:
        """Load pre-computed embeddings from disk."""
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
            
            self.articles = data['articles']
            self.embeddings = data['embeddings']
            self.is_fitted = True
            
            logger.info(f"📁 Loaded embeddings from: {filepath}")
            logger.info(f"✅ Articles: {len(self.articles)}, Embeddings: {self.embeddings.shape}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load embeddings: {e}")
            raise
    
    def search_by_keywords(self, keywords: List[str], top_k: int = 5) -> List[Dict]:
        """
        Search articles by keywords in title and content.
        
        Args:
            keywords: List of keywords to search for
            top_k: Number of results to return
            
        Returns:
            List of matching articles with relevance scores
        """
        keyword_query = " ".join(keywords)
        logger.info(f"🔍 Searching for keywords: {keywords}")
        
        # Use semantic similarity for keyword search
        return self.find_similar_articles(keyword_query, top_k=top_k)
    
    def get_diverse_examples(self, 
                           query_text: str, 
                           num_examples: int = 3,
                           ensure_category_diversity: bool = True) -> List[Dict]:
        """
        Get diverse examples across different categories for better style coverage.
        
        Args:
            query_text: Query to match against
            num_examples: Number of examples to return
            ensure_category_diversity: Try to get examples from different categories
            
        Returns:
            List of diverse article examples
        """
        # Get more candidates than needed
        candidates = self.find_similar_articles(query_text, top_k=num_examples * 3)
        
        if not ensure_category_diversity:
            return candidates[:num_examples]
        
        # Select diverse examples
        selected = []
        used_categories = set()
        
        # First pass: one from each category
        for candidate in candidates:
            category = candidate['article']['category']
            if category not in used_categories:
                selected.append(candidate)
                used_categories.add(category)
                
                if len(selected) >= num_examples:
                    break
        
        # Second pass: fill remaining slots with best matches
        if len(selected) < num_examples:
            for candidate in candidates:
                if candidate not in selected:
                    selected.append(candidate)
                    if len(selected) >= num_examples:
                        break
        
        # Update ranks
        for i, result in enumerate(selected, 1):
            result['rank'] = i
        
        logger.info(f"✅ Selected {len(selected)} diverse examples from categories: "
                   f"{[r['article']['category'] for r in selected]}")
        
        return selected