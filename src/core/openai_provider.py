import time
from typing import Dict, Any, Optional, Generator, List
from openai import OpenAI
from src.core.llm_provider import LLMProvider


class OpenAIProvider(LLMProvider):
    DEFAULT_TIMEOUT_S = 30
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 1024
    MAX_RETRIES = 3

    def __init__(
        self,
        model_name: str = "gpt-4o",
        api_key: Optional[str] = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        super().__init__(model_name, api_key)
        self.client = OpenAI(api_key=self.api_key, timeout=timeout_s)
        self.temperature = temperature
        self.max_tokens = max_tokens

    def _build_messages(self, prompt: str, system_prompt: Optional[str]) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _completion_params(self) -> Dict[str, Any]:
        return {
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        messages = self._build_messages(prompt, system_prompt)

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            **self._completion_params(),
        )

        latency_ms = int((time.time() - start_time) * 1000)
        content = response.choices[0].message.content or ""
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }
        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "openai",
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        messages = self._build_messages(prompt, system_prompt)
        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=True,
            **self._completion_params(),
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
