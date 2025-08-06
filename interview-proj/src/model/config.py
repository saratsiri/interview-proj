"""Model configuration"""
from dataclasses import dataclass

@dataclass
class ModelConfig:
    """Configuration for model and generation"""
    # Model settings
    model_name: str = "gpt2"
    max_length: int = 512
    
    # Generation parameters
    temperature: float = 0.8
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.2
    
    # Training parameters (for future fine-tuning)
    learning_rate: float = 5e-5
    batch_size: int = 4
    num_epochs: int = 3