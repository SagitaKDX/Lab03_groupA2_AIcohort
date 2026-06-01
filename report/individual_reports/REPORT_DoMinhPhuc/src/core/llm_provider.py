import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Generator

class LLMProvider(ABC):
    """
    Abstract Base Class for LLM Providers.
    Supports OpenAI, Gemini, and Local models.
    """

    def __init__(self, model_name: str, api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Produce a non-streaming completion.
        Returns:
            Dict containing:
            - content: The response text
            - usage: { 'prompt_tokens', 'completion_tokens' }
            - latency_ms: Response time
        """
        pass

    @abstractmethod
    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        """Produce a streaming completion."""
        pass


def get_provider(provider_name: Optional[str] = None) -> "LLMProvider":
    """
    Factory function: returns the correct LLMProvider instance.
    Falls back to DEFAULT_PROVIDER env var, then 'openai'.

    Usage:
        provider = get_provider()           # uses DEFAULT_PROVIDER from .env
        provider = get_provider("gemini")   # explicit override
    """
    # Lazy import to avoid circular deps and unnecessary package loading
    from dotenv import load_dotenv
    load_dotenv()

    name = (provider_name or os.getenv("DEFAULT_PROVIDER", "openai")).lower().strip()

    if name == "openai":
        from src.core.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY"))

    elif name == "gemini":
        from src.core.gemini_provider import GeminiProvider
        return GeminiProvider(api_key=os.getenv("GEMINI_API_KEY"))

    elif name == "local":
        from src.core.local_provider import LocalProvider
        model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        return LocalProvider(model_path=model_path)

    else:
        raise ValueError(
            f"Unknown provider '{name}'. "
            "Set DEFAULT_PROVIDER to 'openai', 'gemini', or 'local' in your .env"
        )