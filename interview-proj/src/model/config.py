"""Model configuration"""
from dataclasses import dataclass
import os
from typing import Optional

@dataclass
class ModelConfig:
    """Configuration for model and generation"""
    # Model provider settings
    provider: str = "claude"  # "huggingface", "openai", or "claude"
    model_name: str = "claude-3-haiku-20240307"
    openai_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    max_tokens: int = 1000
    
    # Generation parameters
    temperature: float = 0.8
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.2
    
    # OpenAI specific parameters
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    # Training parameters (for future fine-tuning)
    learning_rate: float = 5e-5
    batch_size: int = 4
    num_epochs: int = 3
    
    def __post_init__(self):
        """Initialize configuration from environment variables"""
        # Get API keys from environment
        if not self.openai_api_key:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.claude_api_key:
            self.claude_api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        
        # Auto-detect provider based on available API keys
        if self.claude_api_key:
            self.provider = "claude"
            if not self.model_name.startswith("claude"):
                self.model_name = "claude-3-haiku-20240307"
        elif self.openai_api_key:
            self.provider = "openai"
            if self.model_name.startswith("claude"):
                self.model_name = "gpt-3.5-turbo"
        else:
            # Fallback to HuggingFace if no API keys
            self.provider = "huggingface"
            if self.model_name.startswith(("gpt-", "claude")):
                self.model_name = "gpt2"
        
        # Adjust max_tokens for different models
        if self.provider == "claude":
            if "claude-3" in self.model_name:
                self.max_tokens = min(self.max_tokens, 4096)
        elif self.provider == "openai":
            if self.model_name.startswith("gpt-4"):
                self.max_tokens = min(self.max_tokens, 8192)
            elif self.model_name.startswith("gpt-3.5"):
                self.max_tokens = min(self.max_tokens, 4096)
    
    @property
    def max_length(self) -> int:
        """Backward compatibility property"""
        return self.max_tokens