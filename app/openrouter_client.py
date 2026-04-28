from __future__ import annotations

import json
import os
from urllib import request


class OpenRouterClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    def chat(self, model: str, messages: list[dict], tools: list[dict] | None = None) -> dict:
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required")

        payload = {
            "model": model,
            "messages": messages,
            "tools": tools or [],
            "tool_choice": "auto",
        }
        req = request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
