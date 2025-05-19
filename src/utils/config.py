import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class to manage environment variables"""
    
    # API Security
    API_KEY: str = os.getenv("API_KEY", "")
    
    # Rate Limiting
    RATE_LIMIT_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
    
    # Directory configurations
    CHAT_HISTORY_DIR: str = os.getenv("CHAT_HISTORY_DIR", "chats")
    SYSTEM_PROMPT_FILE: str = os.getenv("SYSTEM_PROMPT_FILE", "system_prompt.txt")
    SYSTEM_PROMPTS_DIR: str = os.getenv("SYSTEM_PROMPTS_DIR", "system_prompts")
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration"""
        if not cls.API_KEY:
            raise ValueError("API_KEY environment variable is required. Please set it in your .env file or environment variables.")

# Create a singleton instance
config = Config()