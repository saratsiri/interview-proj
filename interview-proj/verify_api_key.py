#!/usr/bin/env python3
"""
Verify OpenAI API key works
Usage: python verify_api_key.py [your_api_key]
"""
import sys
from openai import OpenAI

def test_api_key(api_key):
    """Test if an OpenAI API key works"""
    print(f"🔍 Testing API key: {api_key[:20]}...")
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Make a minimal test request
        print("🚀 Making test API call...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'Hello'"}],
            max_tokens=5
        )
        
        print("✅ SUCCESS! API key works perfectly!")
        print(f"📝 Response: {response.choices[0].message.content}")
        print(f"🔢 Tokens used: {response.usage.total_tokens}")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        if "quota" in str(e).lower():
            print("💳 This API key has no quota/billing")
        elif "401" in str(e):
            print("🔑 Invalid API key")
        elif "429" in str(e):
            print("⏳ Rate limited - try again in a moment")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test provided API key
        api_key = sys.argv[1]
        success = test_api_key(api_key)
    else:
        # Test API key from .env
        try:
            with open('.env', 'r') as f:
                content = f.read()
                for line in content.split('\n'):
                    if line.startswith('OPENAI_API_KEY='):
                        api_key = line.split('=', 1)[1]
                        success = test_api_key(api_key)
                        break
                else:
                    print("❌ No OPENAI_API_KEY found in .env file")
                    sys.exit(1)
        except FileNotFoundError:
            print("❌ No .env file found")
            print("Usage: python verify_api_key.py your_api_key_here")
            sys.exit(1)
    
    if success:
        print("\n🎉 This API key will work in the system!")
        print("📋 Next steps:")
        print("1. Update .env file with this key")
        print("2. Restart the API server")
        print("3. Test generation - you'll see requests in OpenAI dashboard")
    else:
        print("\n💡 Try with the API key that has quota on your dashboard:")
        print("python verify_api_key.py sk-...")
    
    sys.exit(0 if success else 1)