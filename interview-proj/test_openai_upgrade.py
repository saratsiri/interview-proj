#!/usr/bin/env python3
"""
Test script for OpenAI model upgrade
Usage: OPENAI_API_KEY=your_api_key python test_openai_upgrade.py
"""

import os
import sys
from src.model.config import ModelConfig
from src.model.generator import JenosizeTrendGenerator

def test_openai_upgrade():
    """Test the OpenAI model upgrade"""
    
    print("🚀 Testing OpenAI Model Upgrade...")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OPENAI_API_KEY found in environment variables")
        print("Please run: OPENAI_API_KEY=your_api_key python test_openai_upgrade.py")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Test configuration
    print("\n📋 Testing Configuration...")
    config = ModelConfig(model_name="gpt-3.5-turbo")
    print(f"   Provider: {config.provider}")
    print(f"   Model: {config.model_name}")
    print(f"   Max Tokens: {config.max_tokens}")
    
    # Test generator initialization
    print("\n🤖 Initializing Generator...")
    try:
        generator = JenosizeTrendGenerator(config=config, enable_caching=False)
        print(f"   Provider: {generator.provider}")
        print(f"   Use AI: {generator.use_ai}")
        print(f"   OpenAI Client: {'✅' if generator.openai_client else '❌'}")
        
        if not generator.use_ai:
            print("❌ Generator failed to initialize with AI")
            return False
            
    except Exception as e:
        print(f"❌ Generator initialization failed: {e}")
        return False
    
    # Test article generation
    print("\n📝 Testing Article Generation...")
    try:
        result = generator.generate_article(
            topic="AI in Customer Service",
            category="Technology", 
            keywords=["artificial intelligence", "customer service", "automation"],
            target_audience="Business Leaders",
            tone="Professional"
        )
        
        print("✅ Article generated successfully!")
        print(f"   Title: {result['title'][:60]}...")
        print(f"   Content Length: {len(result['content'])} characters")
        print(f"   Word Count: {result['metadata']['word_count']}")
        print(f"   Model Used: {result['metadata']['model']}")
        print(f"   Provider: {result['metadata'].get('provider', 'unknown')}")
        
        if 'tokens_used' in result['metadata']:
            print(f"   Tokens Used: {result['metadata']['tokens_used']}")
        
        # Show first 200 characters of content
        print(f"\n📄 Content Preview:")
        print(f"   {result['content'][:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Article generation failed: {e}")
        return False

if __name__ == "__main__":
    success = test_openai_upgrade()
    if success:
        print("\n🎉 OpenAI model upgrade successful!")
        print("You can now use GPT-3.5-turbo or GPT-4 models by setting:")
        print("   OPENAI_API_KEY=your_api_key")
        print("   And configuring model_name='gpt-3.5-turbo' or 'gpt-4'")
    else:
        print("\n❌ OpenAI model upgrade failed")
    
    sys.exit(0 if success else 1)