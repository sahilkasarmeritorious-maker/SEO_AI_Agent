from langchain_groq import ChatGroq
from tenacity import retry, stop_after_attempt, wait_exponential
from core.config import Config

class LLMManager:
    """Manages ChatGroq instance with retry logic."""
    
    _instance = None  # Singleton pattern
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize ChatGroq once."""
        if self._initialized:
            return
        
        Config.validate()  # Ensure API key exists
        
        self.model = ChatGroq(
            model_name=Config.LLM_MODEL,
            temperature=Config.LLM_TEMPERATURE,
            max_tokens=Config.LLM_MAX_TOKENS,
            api_key=Config.GEMINI_API_KEY,
            verbose=False
        )
        
        self._initialized = True
        print(f"✅ LLMManager initialized with {Config.LLM_MODEL}")
    
    @retry(
        stop=stop_after_attempt(Config.MAX_RETRIES),
        wait=wait_exponential(
            multiplier=1,
            min=1,
            max=10
        )
    )
    def invoke(self, messages):
        """
        Invoke the LLM with automatic retry.
        
        Args:
            messages: List of message dicts or LangChain Message objects
        
        Returns:
            Response from ChatGroq
        
        Raises:
            Exception after max retries exhausted
        """
        return self.model.invoke(messages)

# Singleton instance
llm = LLMManager()