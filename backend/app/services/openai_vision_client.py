from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Any

import httpx

from app.models.schemas import RankedArticle


class OpenAIVisionClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        project_root: Path,
        base_url: str = "https://api.openai.com/v1",
    ):
        self.api_key = api_key
        self.model = model
        self.project_root = project_root
        self.base_url = base_url.rstrip("/")

    async def analyze(self, article: RankedArticle) -> str:
        image_part = await self._build_image_part(article.image_path)
        if image_part is None:
            return ""

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self._user_prompt(article),
                        },
                        image_part,
                    ],
                },
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices", [])
        if not choices:
            return ""

        content = choices[0].get("message", {}).get("content", "")
        if isinstance(content, list):
            return "".join(str(item.get("text", "")) if isinstance(item, dict) else str(item) for item in content)
        return str(content)

    async def _build_image_part(self, image_path: str | None) -> dict[str, Any] | None:
        if not image_path:
            return None

        if image_path.startswith(("http://", "https://")):
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                response = await client.get(image_path)
                response.raise_for_status()
                image_bytes = response.content
                mime_type = response.headers.get("Content-Type", "").split(";")[0].strip() or self._guess_mime_type(image_path)
        else:
            local_path = Path(image_path)
            if not local_path.is_absolute():
                local_path = self.project_root / local_path
            if not local_path.exists():
                return None
            image_bytes = local_path.read_bytes()
            mime_type = self._guess_mime_type(str(local_path))

        encoded = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{encoded}"
        return {"type": "image_url", "image_url": {"url": data_url}}

    def _guess_mime_type(self, path: str) -> str:
        guessed, _ = mimetypes.guess_type(path)
        return guessed or "image/jpeg"

    def _system_prompt(self) -> str:
        return (
            "You analyze news article images. "
            "Return only valid JSON matching this schema: "
            '{"image_summary":"string","detected_theme":"string","relevance_to_article":"high|medium|low",'
            '"notable_visual_elements":["string"],"confidence_score":0.0}. '
            "Base the analysis on the image, but use the article title/snippet only to judge relevance. "
            "Keep image_summary concise and factual. "
            "Set confidence_score between 0 and 1."
        )

    def _user_prompt(self, article: RankedArticle) -> str:
        return (
            "Analyze the attached image for this news article.\n"
            f"Title: {article.title}\n"
            f"Source: {article.source}\n"
            f"Snippet: {article.snippet}\n"
            "Explain what is visually present, identify the likely theme, list 3-5 notable visual elements, "
            "and rate how strongly the image supports the article."
        )
