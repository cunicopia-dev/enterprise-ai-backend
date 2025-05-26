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
    
    # Directory configurations (legacy, kept for migration)
    CHAT_HISTORY_DIR: str = os.getenv("CHAT_HISTORY_DIR", "chats")
    SYSTEM_PROMPT_FILE: str = os.getenv("SYSTEM_PROMPT_FILE", "system_prompt.txt")
    SYSTEM_PROMPTS_DIR: str = os.getenv("SYSTEM_PROMPTS_DIR", "system_prompts")
    
    # Database configuration
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "postgres")
    DB_USER: str = os.getenv("DB_USER", "streamlitdemo")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "streamlitdemo")
    
    # Provider configuration
    DEFAULT_PROVIDER: str = os.getenv("DEFAULT_PROVIDER", "ollama")
    
    # Provider API Keys
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY", None)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY", None)
    
    # Provider-specific settings
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "30"))
    
    ANTHROPIC_TIMEOUT: int = int(os.getenv("ANTHROPIC_TIMEOUT", "60"))
    ANTHROPIC_MAX_RETRIES: int = int(os.getenv("ANTHROPIC_MAX_RETRIES", "3"))
    
    OPENAI_TIMEOUT: int = int(os.getenv("OPENAI_TIMEOUT", "60"))
    OPENAI_MAX_RETRIES: int = int(os.getenv("OPENAI_MAX_RETRIES", "3"))
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL", None)  # For Azure OpenAI or custom endpoints
    
    GOOGLE_TIMEOUT: int = int(os.getenv("GOOGLE_TIMEOUT", "60"))
    GOOGLE_MAX_RETRIES: int = int(os.getenv("GOOGLE_MAX_RETRIES", "3"))
    
    # Constructed database URL for SQLAlchemy
    @property
    def DATABASE_URL(self) -> str:
        """Get the database URL for SQLAlchemy"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration"""
        if not cls.API_KEY:
            raise ValueError("API_KEY environment variable is required. Please set it in your .env file or environment variables.")
        
        # Database validation
        required_db_vars = ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
        missing_vars = [var for var in required_db_vars if not getattr(cls, var)]
        
        if missing_vars:
            missing_vars_str = ", ".join(missing_vars)
            print(f"Warning: The following database environment variables are using default values: {missing_vars_str}")

# Create a singleton instance
config = Config()