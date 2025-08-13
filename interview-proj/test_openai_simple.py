#!/usr/bin/env python3
"""Simple OpenAI test with different API key if available"""
import os
import sys

# Test with a different approach - check if there's an OPENAI_API_KEY_ALT or use a test key
test_keys = [
    os.getenv('OPENAI_API_KEY'),
    os.getenv('OPENAI_API_KEY_ALT'), 
    # Add a test key here if you have one
]

for key in test_keys:
    if key and key.strip():
        print(f"Testing API key: {key[:20]}...")
        
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=key)
            
            # Make minimal request
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=5
            )
            
            print("✅ SUCCESS! OpenAI API working")
            print(f"Response: {response.choices[0].message.content}")
            print(f"This API key will work in the system!")
            break
            
        except Exception as e:
            print(f"❌ Failed: {e}")
            continue
else:
    print("❌ No working API key found")
    print("\n💡 To test with a working key:")
    print("export OPENAI_API_KEY_ALT='your_working_key_here'")
    print("python test_openai_simple.py")