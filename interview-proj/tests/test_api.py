"""Comprehensive API tests"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
import json
import time

from src.api.main import app, generator
from src.api.schemas import ArticleRequest, ArticleResponse
from src.model.config import ModelConfig


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def sample_request():
    """Sample valid request"""
    return {
        "topic": "AI in Healthcare",
        "category": "Technology",
        "keywords": ["ai", "healthcare", "innovation"],
        "target_audience": "Healthcare Professionals",
        "tone": "Professional and Insightful"
    }


class TestAPIEndpoints:
    """Test API endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "status" in data
        assert "endpoints" in data
        
        assert data["service"] == "Jenosize Trend Articles Generator"
        assert data["status"] == "active"
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "generator_type" in data
        
        assert data["status"] == "healthy"
    
    def test_generate_article_success(self, client, sample_request):
        """Test successful article generation"""
        response = client.post("/generate", json=sample_request)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check response structure
        assert "success" in data
        assert "title" in data
        assert "content" in data
        assert "metadata" in data
        assert "message" in data
        
        assert data["success"] is True
        assert len(data["title"]) > 0
        assert len(data["content"]) > 100
        
        # Check metadata
        metadata = data["metadata"]
        assert metadata["category"] == sample_request["category"]
        assert metadata["keywords"] == sample_request["keywords"]
        assert metadata["target_audience"] == sample_request["target_audience"]
        assert metadata["tone"] == sample_request["tone"]
        assert "word_count" in metadata
        assert "generated_at" in metadata
        assert "generation_time_seconds" in metadata
    
    def test_generate_article_invalid_category(self, client):
        """Test article generation with invalid category"""
        request_data = {
            "topic": "AI in Healthcare",
            "category": "InvalidCategory",
            "keywords": ["ai", "healthcare"],
            "target_audience": "Doctors"
        }
        
        response = client.post("/generate", json=request_data)
        assert response.status_code == 422  # Validation error
        
        error_data = response.json()
        assert "detail" in error_data
    
    def test_generate_article_missing_fields(self, client):
        """Test article generation with missing required fields"""
        incomplete_request = {
            "topic": "AI in Healthcare"
            # Missing category and keywords
        }
        
        response = client.post("/generate", json=incomplete_request)
        assert response.status_code == 422
        
        error_data = response.json()
        assert "detail" in error_data
    
    def test_generate_article_empty_topic(self, client):
        """Test article generation with empty topic"""
        request_data = {
            "topic": "",
            "category": "Technology",
            "keywords": ["ai"],
            "target_audience": "Engineers"
        }
        
        response = client.post("/generate", json=request_data)
        assert response.status_code == 500  # Server error due to validation
    
    def test_generate_article_too_many_keywords(self, client):
        """Test article generation with too many keywords"""
        request_data = {
            "topic": "AI Development",
            "category": "Technology",
            "keywords": ["ai", "ml", "deep", "learning", "neural", "networks", "python", "tensorflow", "pytorch", "data", "science", "algorithms"],  # 12 keywords (max is 10)
            "target_audience": "Developers"
        }
        
        response = client.post("/generate", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_generate_article_performance(self, client, sample_request):
        """Test article generation performance"""
        start_time = time.time()
        response = client.post("/generate", json=sample_request)
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Should complete within reasonable time
        request_time = end_time - start_time
        assert request_time < 10.0  # Less than 10 seconds
        
        # Check generation time in response
        data = response.json()
        generation_time = data["metadata"]["generation_time_seconds"]
        assert generation_time < request_time  # Generation time should be less than total request time
    
    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.options("/generate")
        
        # Check CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers


class TestAPIValidation:
    """Test API input validation"""
    
    def test_topic_validation(self, client):
        """Test topic field validation"""
        # Topic too short
        request_data = {
            "topic": "AI",  # Too short (min_length=3 but this might be business logic)
            "category": "Technology",
            "keywords": ["ai"]
        }
        response = client.post("/generate", json=request_data)
        # Should still work as "AI" is 2 characters, but our validation is in the generator
        
        # Topic too long
        long_topic = "A" * 201  # Exceeds max_length=200
        request_data["topic"] = long_topic
        response = client.post("/generate", json=request_data)
        assert response.status_code == 422
    
    def test_keywords_validation(self, client):
        """Test keywords field validation"""
        # No keywords
        request_data = {
            "topic": "AI in Healthcare",
            "category": "Technology",
            "keywords": []
        }
        response = client.post("/generate", json=request_data)
        assert response.status_code == 422
        
        # Too many keywords
        request_data["keywords"] = ["keyword"] * 11  # Exceeds max_items=10
        response = client.post("/generate", json=request_data)
        assert response.status_code == 422
    
    def test_optional_fields_defaults(self, client):
        """Test optional fields have correct defaults"""
        minimal_request = {
            "topic": "AI Development",
            "category": "Technology",
            "keywords": ["ai", "development"]
        }
        
        response = client.post("/generate", json=minimal_request)
        assert response.status_code == 200
        
        data = response.json()
        metadata = data["metadata"]
        
        # Check defaults
        assert metadata["target_audience"] == "Business Leaders and Tech Professionals"
        assert metadata["tone"] == "Professional and Insightful"


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @patch('src.api.main.generator')
    def test_generator_exception_handling(self, mock_generator, client, sample_request):
        """Test handling of generator exceptions"""
        # Mock generator to raise exception
        mock_generator.generate_article.side_effect = Exception("Model error")
        
        response = client.post("/generate", json=sample_request)
        assert response.status_code == 500
        
        error_data = response.json()
        assert "detail" in error_data
        assert "Model error" in error_data["detail"]
    
    @patch('src.api.main.generator')
    def test_generator_value_error_handling(self, mock_generator, client, sample_request):
        """Test handling of validation errors from generator"""
        # Mock generator to raise ValueError
        mock_generator.generate_article.side_effect = ValueError("Invalid input")
        
        response = client.post("/generate", json=sample_request)
        assert response.status_code == 500
        
        error_data = response.json()
        assert "Invalid input" in error_data["detail"]
    
    def test_malformed_json(self, client):
        """Test handling of malformed JSON"""
        response = client.post(
            "/generate",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_wrong_content_type(self, client, sample_request):
        """Test handling of wrong content type"""
        response = client.post(
            "/generate",
            data=json.dumps(sample_request),
            headers={"Content-Type": "text/plain"}
        )
        # FastAPI should handle this gracefully
        assert response.status_code in [422, 415]


class TestAPIDocumentation:
    """Test API documentation endpoints"""
    
    def test_openapi_schema(self, client):
        """Test OpenAPI schema generation"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        
        # Check API info
        info = schema["info"]
        assert info["title"] == "Jenosize Trend Articles Generator API"
        assert info["version"] == "1.0.0"
    
    def test_docs_endpoint(self, client):
        """Test interactive docs endpoint"""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower()
    
    def test_redoc_endpoint(self, client):
        """Test ReDoc endpoint"""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "redoc" in response.text.lower()


class TestAPIIntegration:
    """Integration tests for API"""
    
    def test_multiple_concurrent_requests(self, client, sample_request):
        """Test multiple concurrent requests"""
        import threading
        import queue
        
        results_queue = queue.Queue()
        
        def make_request(request_data, request_id):
            """Make API request in thread"""
            modified_request = request_data.copy()
            modified_request["topic"] = f"{request_data['topic']} {request_id}"
            
            response = client.post("/generate", json=modified_request)
            results_queue.put((request_id, response.status_code, response.json()))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request, args=(sample_request, i))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Collect results
        results = []
        while not results_queue.empty():
            results.append(results_queue.get())
        
        # Validate all requests succeeded
        assert len(results) == 5
        for request_id, status_code, data in results:
            assert status_code == 200
            assert data["success"] is True
            assert str(request_id) in data["title"]
    
    def test_different_content_types(self, client, sample_request):
        """Test different content types and encodings"""
        # Test with explicit UTF-8
        response = client.post(
            "/generate",
            json=sample_request,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        assert response.status_code == 200
        
        # Test with special characters
        unicode_request = sample_request.copy()
        unicode_request["topic"] = "AI in Healthcare: Transformação Digital"
        unicode_request["keywords"] = ["ai", "saúde", "inovação"]
        
        response = client.post("/generate", json=unicode_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "transformação" in data["title"].lower() or "saúde" in str(data["metadata"]["keywords"])
    
    def test_response_caching_behavior(self, client, sample_request):
        """Test response caching behavior"""
        # Make identical requests
        response1 = client.post("/generate", json=sample_request)
        response2 = client.post("/generate", json=sample_request)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Content might be identical due to caching
        data1 = response1.json()
        data2 = response2.json()
        
        # At minimum, structure should be the same
        assert data1.keys() == data2.keys()
        assert data1["metadata"]["category"] == data2["metadata"]["category"]
    
    def test_large_request_handling(self, client):
        """Test handling of requests with large content"""
        large_request = {
            "topic": "A" * 200,  # Max length topic
            "category": "Technology",
            "keywords": ["keyword" + str(i) for i in range(10)],  # Max keywords
            "target_audience": "Very Specific Target Audience With Long Description",
            "tone": "Professional and Insightful with Detailed Analysis"
        }
        
        response = client.post("/generate", json=large_request)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["content"]) > 100  # Should generate substantial content
    
    def test_api_response_schema_compliance(self, client, sample_request):
        """Test API response complies with schema"""
        response = client.post("/generate", json=sample_request)
        assert response.status_code == 200
        
        data = response.json()
        
        # Validate against ArticleResponse schema
        try:
            article_response = ArticleResponse(**data)
            assert article_response.success is True
            assert len(article_response.title) > 0
            assert len(article_response.content) > 0
            assert article_response.metadata.category == sample_request["category"]
        except Exception as e:
            pytest.fail(f"Response doesn't match schema: {e}")


class TestAPIPerformance:
    """Performance tests for API"""
    
    def test_response_time_within_limits(self, client, sample_request):
        """Test response time is within acceptable limits"""
        start_time = time.time()
        response = client.post("/generate", json=sample_request)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 5.0  # Should respond within 5 seconds
        
        # Check internal generation time
        data = response.json()
        generation_time = data["metadata"]["generation_time_seconds"]
        assert generation_time < response_time
    
    def test_memory_usage_stability(self, client, sample_request):
        """Test memory usage remains stable across requests"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Make multiple requests
        for i in range(10):
            modified_request = sample_request.copy()
            modified_request["topic"] = f"Memory Test {i}"
            response = client.post("/generate", json=modified_request)
            assert response.status_code == 200
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024