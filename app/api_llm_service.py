from dataclasses import dataclass
import httpx
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Config:
    api_key: str = "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"
    base_url: str = "https://openrouter.ai/api/v1"
    embedding_model: str = "all-MiniLM-L6-v2"
    similarity_threshold: float = 0.55
    max_memory_cells: int = 1000
    experience_reward_decay: float = 0.9
    enable_emotions: bool = True


class APIClient:
    """Simple async client for OpenRouter / OpenAI-compatible chat completions.

    This keeps the same async `generate(user_prompt, sys_prompt)` signature
    so it can replace a local pipeline with minimal changes.
    """

    def __init__(self, config: Config = Config(), timeout: float = 60.0):
        self.config = config
        self._client = httpx.AsyncClient(timeout=timeout, headers={
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        })

    async def generate(self, user_prompt: str, sys_prompt: str = "you are a qwen assitant", model: str = "qwen/qwen3-vl-30b-a3b-thinking") -> str:
        messages = [
            {"role": "system", "content": [{"type": "text", "text": sys_prompt}]},
            {"role": "user", "content": [{"type": "text", "text": user_prompt}]},
        ]

        body = {
            "model": model,
            "messages": messages,
        }

        url = f"{self.config.base_url}/chat/completions"

        resp = await self._client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()

        # Try to extract the message content robustly
        try:
            choice = data.get("choices", [])[0]
            message = choice.get("message", {})
            content = message.get("content")

            if isinstance(content, list):
                parts: List[str] = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        parts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        parts.append(part)
                return "".join(parts)

            if isinstance(content, str):
                return content

            # fallback to top-level text
            if "text" in choice:
                return choice["text"]

        except Exception as e:
            logger.debug("Failed to parse completion response: %s", e)

        # As a last resort, return the raw JSON string
        return str(data)

    async def close(self):
        await self._client.aclose()


def generate(user_prompt, sys_prompt="you are a qwen assitant"):
    """Convenience sync wrapper for quick scripts (uses async under the hood).

    If you prefer to call `await APIClient.generate(...)` directly, create an
    instance instead of using this wrapper.
    """
    import asyncio

    client = APIClient()

    return asyncio.get_event_loop().run_until_complete(
        client.generate(user_prompt, sys_prompt)
    )
