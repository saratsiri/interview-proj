"""Comprehensive tests for the article generator"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.model.generator import JenosizeTrendGenerator, ModelCache
from src.model.config import ModelConfig


class TestModelCache:
    """Test the ModelCache class"""
    
    def setup_method(self):
        """Setup for each test"""
        self.cache = ModelCache(cache_dir="tests/cache")
    
    def test_cache_key_generation(self):
        """Test cache key generation"""
        key = self.cache._get_cache_key(
            "AI in Healthcare", 
            "Technology", 
            ["ai", "healthcare"], 
            "Doctors", 
            "Professional"
        )
        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hash length
    
    def test_cache_set_get(self):
        """Test cache set and get operations"""
        key = "test_key"
        value = {"title": "Test", "content": "Content"}
        
        # Set cache
        self.cache.set(key, value)
        
        # Get cache
        result = self.cache.get(key)
        assert result == value
    
    def test_cache_expiration(self):
        """Test cache expiration"""
        key = "test_key"
        value = {"title": "Test"}
        
        # Set cache
        self.cache.set(key, value)
        
        # Manually set old timestamp
        self.cache.cache_times[key] = datetime.now() - timedelta(hours=25)
        
        # Should return None (expired)
        result = self.cache.get(key)
        assert result is None
        
        # Key should be removed
        assert key not in self.cache.cache
    
    def test_clear_expired(self):
        """Test clearing expired entries"""
        # Add fresh entry
        self.cache.set("fresh", {"data": "fresh"})
        
        # Add expired entry
        self.cache.set("expired", {"data": "expired"})
        self.cache.cache_times["expired"] = datetime.now() - timedelta(hours=25)
        
        # Clear expired
        self.cache.clear_expired()
        
        # Fresh should remain, expired should be gone
        assert self.cache.get("fresh") is not None
        assert self.cache.get("expired") is None


class TestJenosizeTrendGenerator:
    """Test the main generator class"""
    
    def setup_method(self):
        """Setup for each test"""
        self.config = ModelConfig()
        self.generator = JenosizeTrendGenerator(config=self.config, enable_caching=False)
    
    def test_initialization_without_ai(self):
        """Test generator initialization when AI is not available"""
        gen = JenosizeTrendGenerator(config=None)
        assert not gen.use_ai
        assert gen.model is None
        assert gen.tokenizer is None
    
    def test_input_validation(self):
        """Test input validation"""
        # Empty topic
        with pytest.raises(ValueError, match="Topic cannot be empty"):
            self.generator.generate_article("", "Technology", ["ai"])
        
        # Empty category
        with pytest.raises(ValueError, match="Category cannot be empty"):
            self.generator.generate_article("AI", "", ["ai"])
        
        # No keywords
        with pytest.raises(ValueError, match="At least one keyword is required"):
            self.generator.generate_article("AI", "Technology", [])
    
    def test_mock_article_generation(self):
        """Test mock article generation"""
        result = self.generator.generate_article(
            topic="AI in Healthcare",
            category="Technology",
            keywords=["ai", "healthcare", "innovation"],
            target_audience="Doctors",
            tone="Professional"
        )
        
        # Check structure
        assert "title" in result
        assert "content" in result
        assert "metadata" in result
        
        # Check metadata
        metadata = result["metadata"]
        assert metadata["category"] == "Technology"
        assert metadata["keywords"] == ["ai", "healthcare", "innovation"]
        assert metadata["target_audience"] == "Doctors"
        assert metadata["tone"] == "Professional"
        assert metadata["generation_type"] == "mock"
        assert "word_count" in metadata
        assert "generated_at" in metadata
        assert "generation_time_seconds" in metadata
        
        # Check content quality
        assert len(result["content"]) > 100
        assert "ai" in result["content"].lower()
        assert "healthcare" in result["content"].lower()
    
    def test_input_cleaning(self):
        """Test input cleaning and normalization"""
        result = self.generator.generate_article(
            topic="  AI in Healthcare  ",
            category="  Technology  ",
            keywords=["  AI  ", "  Healthcare  ", ""],
            target_audience="  Doctors  ",
            tone="  Professional  "
        )
        
        metadata = result["metadata"]
        assert metadata["keywords"] == ["ai", "healthcare"]  # Cleaned and lowercased
    
    def test_caching_enabled(self):
        """Test caching functionality"""
        gen = JenosizeTrendGenerator(config=self.config, enable_caching=True)
        
        # First generation
        start_time = time.time()
        result1 = gen.generate_article("AI", "Technology", ["ai"])
        first_time = time.time() - start_time
        
        # Second generation (should be cached)
        start_time = time.time()
        result2 = gen.generate_article("AI", "Technology", ["ai"])
        second_time = time.time() - start_time
        
        # Results should be identical
        assert result1["title"] == result2["title"]
        assert result1["content"] == result2["content"]
        
        # Second call should be faster (cached)
        assert second_time < first_time
    
    def test_get_model_info(self):
        """Test model info retrieval"""
        info = self.generator.get_model_info()
        
        assert isinstance(info, dict)
        assert "ai_available" in info
        assert "model_loaded" in info
        assert "cache_enabled" in info
        assert "generation_count" in info
    
    def test_clear_cache(self):
        """Test cache clearing"""
        gen = JenosizeTrendGenerator(config=self.config, enable_caching=True)
        
        # Generate to populate cache
        gen.generate_article("AI", "Technology", ["ai"])
        
        # Clear cache
        gen.clear_cache()
        
        # Cache should be empty
        if gen.cache:
            assert len(gen.cache.cache) == 0
    
    @patch('src.model.generator.TRANSFORMERS_AVAILABLE', True)
    @patch('src.model.generator.torch')
    @patch('src.model.generator.AutoTokenizer')
    @patch('src.model.generator.AutoModelForCausalLM')
    def test_ai_initialization_success(self, mock_model, mock_tokenizer, mock_torch):
        """Test successful AI model initialization"""
        # Mock setup
        mock_torch.cuda.is_available.return_value = False
        mock_torch.device.return_value = Mock()
        mock_tokenizer.from_pretrained.return_value = Mock()
        mock_model.from_pretrained.return_value = Mock()
        
        # Create generator
        gen = JenosizeTrendGenerator(config=self.config)
        
        # Should attempt to initialize AI
        mock_tokenizer.from_pretrained.assert_called_once()
        mock_model.from_pretrained.assert_called_once()
    
    @patch('src.model.generator.TRANSFORMERS_AVAILABLE', True)
    @patch('src.model.generator.torch')
    @patch('src.model.generator.AutoTokenizer')
    @patch('src.model.generator.AutoModelForCausalLM')
    def test_ai_initialization_failure(self, mock_model, mock_tokenizer, mock_torch):
        """Test AI model initialization failure and fallback"""
        # Mock failure
        mock_model.from_pretrained.side_effect = Exception("Model load failed")
        
        # Create generator
        gen = JenosizeTrendGenerator(config=self.config)
        
        # Should fall back to mock
        assert not gen.use_ai
        assert gen.model is None
    
    def test_periodic_cleanup_tracking(self):
        """Test periodic cleanup is tracked correctly"""
        initial_count = self.generator.generation_count
        
        # Generate multiple articles
        for i in range(5):
            self.generator.generate_article(f"Topic {i}", "Technology", ["test"])
        
        # Generation count should increase
        assert self.generator.generation_count == initial_count + 5
    
    def test_error_handling_with_fallback(self):
        """Test error handling and fallback to mock"""
        # Create a generator that simulates AI failure
        gen = JenosizeTrendGenerator(config=self.config)
        gen.use_ai = True  # Force AI flag
        gen.model = None   # But no actual model
        
        # Should fall back to mock
        result = gen.generate_article("AI", "Technology", ["ai"])
        
        assert result["metadata"]["generation_type"] == "mock"
        assert result["metadata"].get("fallback_used") is True
    
    def test_multiple_keywords_handling(self):
        """Test handling of multiple keywords"""
        keywords = ["ai", "machine learning", "automation", "innovation", "efficiency"]
        
        result = self.generator.generate_article(
            "AI Implementation",
            "Technology",
            keywords
        )
        
        # All keywords should be preserved in metadata
        assert result["metadata"]["keywords"] == keywords
        
        # Content should include multiple keywords
        content_lower = result["content"].lower()
        keyword_found = sum(1 for kw in keywords if kw in content_lower)
        assert keyword_found >= 3  # At least 3 keywords should appear
    
    def test_different_tones(self):
        """Test different tone handling"""
        tones = ["Professional", "Technical", "Inspirational"]
        
        results = []
        for tone in tones:
            result = self.generator.generate_article(
                "AI Development",
                "Technology", 
                ["ai"],
                tone=tone
            )
            results.append(result)
            assert result["metadata"]["tone"] == tone
        
        # Results should be different based on tone
        titles = [r["title"] for r in results]
        assert len(set(titles)) > 1  # Should have different titles
    
    def test_target_audience_customization(self):
        """Test target audience customization"""
        audiences = ["Developers", "Business Leaders", "Healthcare Professionals"]
        
        for audience in audiences:
            result = self.generator.generate_article(
                "AI Strategy",
                "Technology",
                ["ai"],
                target_audience=audience
            )
            
            assert result["metadata"]["target_audience"] == audience
            assert audience.lower() in result["content"].lower()


class TestIntegration:
    """Integration tests"""
    
    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow"""
        config = ModelConfig()
        generator = JenosizeTrendGenerator(config=config, enable_caching=True)
        
        # Test parameters
        topic = "Blockchain in Supply Chain"
        category = "Technology"
        keywords = ["blockchain", "supply chain", "transparency", "efficiency"]
        audience = "Supply Chain Managers"
        tone = "Professional"
        
        # Generate article
        result = generator.generate_article(
            topic=topic,
            category=category,
            keywords=keywords,
            target_audience=audience,
            tone=tone
        )
        
        # Validate complete result structure
        assert isinstance(result, dict)
        
        # Title validation
        assert isinstance(result["title"], str)
        assert len(result["title"]) > 10
        assert topic.split()[0] in result["title"]  # Should contain main topic word
        
        # Content validation
        assert isinstance(result["content"], str)
        assert len(result["content"]) > 500  # Substantial content
        assert len(result["content"].split()) > 100  # Good word count
        
        # Metadata validation
        metadata = result["metadata"]
        assert metadata["category"] == category
        assert metadata["keywords"] == keywords
        assert metadata["target_audience"] == audience
        assert metadata["tone"] == tone
        assert isinstance(metadata["word_count"], int)
        assert metadata["word_count"] > 100
        assert "generated_at" in metadata
        assert "generation_time_seconds" in metadata
        assert "generation_type" in metadata
        
        # Performance validation
        assert metadata["generation_time_seconds"] < 10  # Should be fast
        
        # Content quality validation
        content_lower = result["content"].lower()
        for keyword in keywords:
            assert keyword in content_lower, f"Keyword '{keyword}' not found in content"
        
        # Get model info
        info = generator.get_model_info()
        assert isinstance(info, dict)
        assert info["generation_count"] >= 1
    
    def test_concurrent_generation(self):
        """Test concurrent article generation"""
        import threading
        
        generator = JenosizeTrendGenerator(
            config=ModelConfig(), 
            enable_caching=True
        )
        
        results = []
        errors = []
        
        def generate_article(index):
            try:
                result = generator.generate_article(
                    f"AI Topic {index}",
                    "Technology",
                    [f"keyword{index}", "ai"],
                    target_audience="Engineers"
                )
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=generate_article, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Validate results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
        
        # Each result should be valid
        for result in results:
            assert "title" in result
            assert "content" in result
            assert "metadata" in result
    
    def test_performance_benchmarks(self):
        """Test performance benchmarks"""
        generator = JenosizeTrendGenerator(
            config=ModelConfig(),
            enable_caching=False  # Test without caching
        )
        
        # Measure generation time
        start_time = time.time()
        result = generator.generate_article(
            "Performance Testing",
            "Technology",
            ["performance", "testing", "benchmarks"]
        )
        generation_time = time.time() - start_time
        
        # Performance assertions
        assert generation_time < 5.0  # Should complete within 5 seconds
        assert result["metadata"]["generation_time_seconds"] < 5.0
        
        # Content quality assertions
        assert len(result["content"]) > 1000  # Substantial content
        assert result["metadata"]["word_count"] > 200  # Good word count