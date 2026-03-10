from dataclasses import dataclass
import httpx
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Auto-load .env file if it exists (loads environment variables for this process)
try:
    from dotenv import load_dotenv
    # Find and load .env from the project root (parent of app/ directory)
    import pathlib
    app_dir = pathlib.Path(__file__).parent  # .../app
    project_root = app_dir.parent  # .../
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)  # override=True to replace existing env vars
    else:
        load_dotenv(override=True)  # fallback: search parent directories
except ImportError:
    # python-dotenv not installed; env vars must be set manually
    pass


@dataclass
class Config:
    # Prefer reading API keys from env; this default should be empty for safety.
    api_key: str = ""
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
        # Resolve API key: prefer explicit config, then common environment vars
        key = (
            config.api_key
            or os.getenv("OPENROUTER_API_KEY")
            or os.getenv("OPENROUTER_KEY")
            or os.getenv("OPENAI_API_KEY")
            or os.getenv("API_KEY")
        )

        if not key:
            raise RuntimeError(
                "Missing API key for OpenRouter/OpenAI. Set OPENROUTER_API_KEY or pass Config(api_key=...)"
            )

        self.config.api_key = key

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
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            # Provide a clearer error for authentication issues
            if e.response.status_code == 401:
                raise RuntimeError(
                    "Authentication failed (401). Check your API key and that it is set in OPENROUTER_API_KEY or Config.api_key."
                ) from e
            raise
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
