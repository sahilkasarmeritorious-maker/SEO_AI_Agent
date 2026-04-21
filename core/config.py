import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env file
ENV_FILE = Path(__file__).parent.parent / ".env"
load_dotenv(ENV_FILE)

class Config:
    """Application configuration."""
    
    # API Keys
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # LLM Settings
    LLM_MODEL = "llama-3.1-8b-instant"  # Groq model
    LLM_TEMPERATURE = 0.0  # No randomness for consistent analysis
    LLM_MAX_TOKENS = 2048
    
    # Scraper Settings
    SCRAPER_TIMEOUT_MS = 30000  # 30 seconds
    SCRAPER_VIEWPORT_WIDTH = 1440
    SCRAPER_VIEWPORT_HEIGHT = 900
    
    # Retry Settings
    MAX_RETRIES = 3
    RETRY_BACKOFF_FACTOR = 2  # 2^attempt seconds
    
    @classmethod
    def validate(cls):
        """Validate all required configs are set."""
        if not cls.GROQ_API_KEY:
            raise ValueError("❌ GROQ_API_KEY not set in .env file!")
        print("✅ Configuration loaded successfully!")

if __name__ == "__main__":
    Config.validate()
    print(f"✅ GROQ_API_KEY: {Config.GROQ_API_KEY[:20]}...")