"""Minimal OpenAI-compatible chat-completions provider.

The repository does not require this provider. Deterministic mode is the
reproducible default. The provider is intentionally generic so local or hosted
OpenAI-compatible endpoints can be used without embedding a vendor-specific SDK.
"""

from __future__ import annotations

import json
from typing import Any

import httpx


class OpenAICompatibleProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 90.0,
        temperature: float = 0.1,
    ) -> None:
        if not api_key:
            raise ValueError("An API key is required for the OpenAI-compatible provider")
        if not model:
            raise ValueError("A model name is required for the OpenAI-compatible provider")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature

    def generate_json(self, *, system: str, user: str) -> dict[str, Any]:
        payload = {
            "model": self.model_name,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout_seconds, headers=headers) as client:
            response = client.post(f"{self.base_url}/chat/completions", json=payload)
            if response.status_code >= 400 and "response_format" in response.text:
                payload.pop("response_format", None)
                response = client.post(f"{self.base_url}/chat/completions", json=payload)
            response.raise_for_status()
            body = response.json()
        content = body["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(
                str(item.get("text", "")) if isinstance(item, dict) else str(item)
                for item in content
            )
        return _parse_json_object(str(content))


def _parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].lstrip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError as exc:
        start, end = stripped.find("{"), stripped.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Provider response did not contain a JSON object") from exc
        value = json.loads(stripped[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("Provider JSON response must be an object")
    return value
