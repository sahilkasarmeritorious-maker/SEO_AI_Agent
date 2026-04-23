from langchain_google_genai import ChatGoogleGenerativeAI
from tenacity import retry, stop_after_attempt, wait_exponential
from core.config import Config

class LLMManager:
    """Manages ChatGoogleGenerativeAI instance with retry logic."""
    
    _instance = None  # Singleton pattern
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize ChatGoogleGenerativeAI once."""
        if self._initialized:
            return
        
        Config.validate()  # Ensure API key exists
        
        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            temperature=Config.LLM_TEMPERATURE,
            max_output_tokens=Config.LLM_MAX_TOKENS,
            google_api_key=Config.GEMINI_API_KEY,
        )
        
        self._initialized = True
        print(f"✅ LLMManager initialized with gemini-2.5-flash-lite")
    
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
            Response from ChatGoogleGenerativeAI
        
        Raises:
            Exception after max retries exhausted
        """
        return self.model.invoke(messages)

# Singleton instance
llm = LLMManager()