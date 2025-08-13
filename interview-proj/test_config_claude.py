#!/usr/bin/env python3
import os
import sys
sys.path.append('.')

# Set environment variable from .env file
if not os.getenv('CLAUDE_API_KEY'):
    print("Please set CLAUDE_API_KEY environment variable")

from src.model.config import ModelConfig

config = ModelConfig()
print('Provider:', config.provider)
print('Model:', config.model_name)
print('Claude API Key Set:', bool(config.claude_api_key))
print('OpenAI API Key Set:', bool(config.openai_api_key))

if config.claude_api_key:
    print('Claude Key first 20 chars:', config.claude_api_key[:20] + '...')