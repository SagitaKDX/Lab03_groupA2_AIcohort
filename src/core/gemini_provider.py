import os
import time
import google.generativeai as genai
from typing import Dict, Any, Optional, Generator
from src.core.llm_provider import LLMProvider

class GeminiProvider(LLMProvider):
    def __init__(self, model_name: str = "gemini-1.5-flash", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        # In Gemini, system instruction is passed during model initialization or as a prefix
        # For simplicity in this lab, we'll prepend it if provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

        response = self.model.generate_content(full_prompt)

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        try:
            content = response.text
        except ValueError as e:
            finish_reason = "Unknown"
            if hasattr(response, "candidates") and response.candidates:
                try:
                    finish_reason = str(response.candidates[0].finish_reason)
                except Exception:
                    pass
            content = f"Error: Gemini response generation blocked/failed (FinishReason: {finish_reason}). Raw error: {str(e)}"

        try:
            usage = {
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count
            }
        except Exception:
            usage = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "google"
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

        try:
            response = self.model.generate_content(full_prompt, stream=True)
            for chunk in response:
                try:
                    yield chunk.text
                except ValueError as e:
                    finish_reason = "Unknown"
                    if hasattr(chunk, "candidates") and chunk.candidates:
                        try:
                            finish_reason = str(chunk.candidates[0].finish_reason)
                        except Exception:
                            pass
                    yield f" [Error: Stream chunk blocked/failed (FinishReason: {finish_reason}): {str(e)}] "
        except Exception as e:
            yield f" [Error: Stream failed to start: {str(e)}] "
