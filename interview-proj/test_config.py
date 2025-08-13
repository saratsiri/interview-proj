#!/usr/bin/env python3
import sys
import os
sys.path.append('.')

# Set OpenAI API key from environment or .env file
if not os.getenv('OPENAI_API_KEY'):
    print("Please set OPENAI_API_KEY environment variable")

from src.model.config import ModelConfig

config = ModelConfig()
print('Provider:', config.provider)
print('Model:', config.model_name)
print('API Key Set:', bool(config.openai_api_key))
print('Max Tokens:', config.max_tokens)

if config.openai_api_key:
    print('API Key first 20 chars:', config.openai_api_key[:20] + '...')