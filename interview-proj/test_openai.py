#!/usr/bin/env python3
import os
import sys
sys.path.append('.')

# Set OpenAI API key from environment or .env file
if not os.getenv('OPENAI_API_KEY'):
    print("Please set OPENAI_API_KEY environment variable")

from openai import OpenAI

def test_openai_api():
    """Test OpenAI API with a simple request"""
    print("Testing OpenAI API connection...")
    
    try:
        client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
        print(f"✅ OpenAI client created successfully")
        print(f"📝 API key: {os.environ['OPENAI_API_KEY'][:20]}...")
        
        # Make a simple test request
        print("🚀 Making test API call...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Say hello"}
            ],
            max_tokens=10
        )
        
        print("✅ API call successful!")
        print(f"📤 Response: {response.choices[0].message.content}")
        print(f"🔢 Tokens used: {response.usage.total_tokens if response.usage else 'N/A'}")
        return True
        
    except Exception as e:
        print(f"❌ API call failed: {e}")
        print(f"🔍 Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = test_openai_api()
    sys.exit(0 if success else 1)