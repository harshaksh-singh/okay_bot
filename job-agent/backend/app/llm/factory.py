from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.llm.base import LLMProvider
from app.llm.mock import MockLLMProvider


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    s = get_settings()
    provider = (s.llm_provider or "mock").lower()
    if provider == "mock" or s.mock_mode:
        return MockLLMProvider()
    if provider == "openai":
        try:
            from app.llm.openai_provider import OpenAIProvider
            return OpenAIProvider()
        except Exception:
            return MockLLMProvider()
    if provider == "anthropic":
        try:
            from app.llm.anthropic_provider import AnthropicProvider
            return AnthropicProvider()
        except Exception:
            return MockLLMProvider()
    if provider == "gemini":
        try:
            from app.llm.gemini_provider import GeminiProvider
            return GeminiProvider()
        except Exception:
            return MockLLMProvider()
    return MockLLMProvider()
