#!/usr/bin/env python3
"""
Test Claude API integration
Usage: python test_claude.py [your_claude_api_key]
"""
import sys
import os
sys.path.append('.')

from src.model.claude_handler import ClaudeHandler

def test_claude_api(api_key):
    """Test if a Claude API key works"""
    print(f"🔍 Testing Claude API key: {api_key[:20]}...")
    
    try:
        handler = ClaudeHandler(api_key=api_key, model="claude-3-haiku-20240307")
        
        # Test connection
        print("🚀 Testing connection...")
        success = handler.test_connection()
        
        if success:
            print("✅ SUCCESS! Claude API working perfectly!")
            
            # Test article generation
            print("📝 Testing article generation...")
            response = handler.generate_completion(
                messages=[
                    {"role": "system", "content": "You are a Jenosize business writer."},
                    {"role": "user", "content": "Write a 2-sentence summary of AI in marketing."}
                ],
                max_tokens=100
            )
            
            print("✅ Generation successful!")
            print(f"📝 Response: {response.content[0].text}")
            print(f"🔢 Tokens: {response.usage.input_tokens} in, {response.usage.output_tokens} out")
            return True
        else:
            return False
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        if "api_key" in str(e).lower() or "401" in str(e):
            print("🔑 Invalid API key")
        elif "429" in str(e):
            print("⏳ Rate limited - try again in a moment")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test provided API key
        api_key = sys.argv[1]
        success = test_claude_api(api_key)
    else:
        # Check for API key in environment
        api_key = os.getenv('CLAUDE_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            success = test_claude_api(api_key)
        else:
            print("❌ No Claude API key provided")
            print("Usage: python test_claude.py your_claude_api_key_here")
            print("Or set CLAUDE_API_KEY environment variable")
            sys.exit(1)
    
    if success:
        print("\n🎉 Claude API is working! Next steps:")
        print("1. Add CLAUDE_API_KEY to .env file")
        print("2. Restart the API server")
        print("3. Test generation - you'll see requests in Anthropic console")
    else:
        print("\n💡 Get a Claude API key from: https://console.anthropic.com/")
    
    sys.exit(0 if success else 1)