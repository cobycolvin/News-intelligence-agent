from __future__ import annotations

import httpx


class OllamaClient:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model

    async def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
