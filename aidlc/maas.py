from __future__ import annotations

import os
from typing import Any

import httpx

from aidlc.settings import settings


class MaaSClient:
    def __init__(self) -> None:
        self.api_key = os.environ.get("MAAS_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("MAAS_API_KEY is not configured")

    def complete(self, system: str, user: str, temperature: float = 0.1) -> dict[str, Any]:
        payload = {
            "model": settings.maas_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        with httpx.Client(timeout=180) as client:
            response = client.post(
                f"{settings.maas_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        response.raise_for_status()
        data = response.json()
        return {
            "content": data["choices"][0]["message"]["content"],
            "usage": data.get("usage", {}),
            "request_id": response.headers.get("x-request-id") or data.get("id"),
            "model": data.get("model", settings.maas_model),
        }

