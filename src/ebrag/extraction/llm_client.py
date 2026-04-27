from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, cast

import httpx


class LLMClient(Protocol):
    def complete_json(self, *, prompt: str, paper_id: str) -> dict[str, Any]:
        """Return structured JSON for a paper extraction prompt."""


class FakeLLMClient:
    def __init__(self, fixture_by_paper_id: dict[str, dict[str, Any]]) -> None:
        self.fixture_by_paper_id = fixture_by_paper_id

    @classmethod
    def from_json_file(cls, path: Path) -> FakeLLMClient:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            msg = "Fake LLM fixture must be an object keyed by paper_id"
            raise ValueError(msg)
        return cls(data)

    def complete_json(self, *, prompt: str, paper_id: str) -> dict[str, Any]:
        _ = prompt
        if paper_id not in self.fixture_by_paper_id:
            msg = f"No fake LLM fixture for paper_id={paper_id}"
            raise KeyError(msg)
        return self.fixture_by_paper_id[paper_id]


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _loads_json_object(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(_strip_json_fence(text))
    except json.JSONDecodeError as exc:
        msg = "LLM response must be valid JSON"
        raise ValueError(msg) from exc
    if not isinstance(payload, dict):
        msg = "LLM response JSON must be an object"
        raise ValueError(msg)
    return payload


class StructuredJSONClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        http_client: httpx.Client | None = None,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.http_client = http_client or httpx.Client(timeout=timeout_seconds)
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def complete_json(self, *, prompt: str, paper_id: str) -> dict[str, Any]:
        return self._request_json(
            prompt=(
                "Return only a JSON object matching the requested schema. "
                f"The current paper_id is {paper_id}.\n\n{prompt}"
            )
        )

    def synthesize_json(self, *, prompt: str, evidence_pack: Any) -> dict[str, Any]:
        _ = evidence_pack
        return self._request_json(
            prompt="Return only a JSON synthesis object with cited ids.\n\n" + prompt
        )

    def verify_json(self, *, prompt: str) -> dict[str, Any]:
        return self._request_json(prompt="Return only a JSON verification object.\n\n" + prompt)

    def _request_json(self, *, prompt: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for _attempt in range(self.max_retries + 1):
            try:
                return _loads_json_object(self._request_text(prompt=prompt))
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
        if isinstance(last_error, ValueError):
            raise last_error
        msg = "LLM request failed after retries"
        raise RuntimeError(msg) from last_error

    def _request_text(self, *, prompt: str) -> str:
        raise NotImplementedError


class OpenAICompatibleJSONClient(StructuredJSONClient):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        http_client: httpx.Client | None = None,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
    ) -> None:
        super().__init__(
            api_key=api_key,
            model=model,
            http_client=http_client,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )
        self.base_url = base_url.rstrip("/")

    def _request_text(self, *, prompt: str) -> str:
        response = self.http_client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "You are a strict JSON API."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            msg = "OpenAI-compatible response content must be text"
            raise ValueError(msg)
        return content


class AnthropicJSONClient(StructuredJSONClient):
    def _request_text(self, *, prompt: str) -> str:
        response = self.http_client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": self.model,
                "max_tokens": 4096,
                "temperature": 0,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt + "\n\nReturn only valid JSON. No markdown.",
                    }
                ],
            },
        )
        response.raise_for_status()
        payload = response.json()
        for block in payload.get("content", []):
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                return cast(str, block["text"])
        msg = "Anthropic response did not include a text content block"
        raise ValueError(msg)


class GoogleJSONClient(StructuredJSONClient):
    def _request_text(self, *, prompt: str) -> str:
        response = self.http_client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            params={"key": self.api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0,
                    "responseMimeType": "application/json",
                },
            },
        )
        response.raise_for_status()
        payload = response.json()
        candidates = payload.get("candidates", [])
        if not candidates:
            msg = "Google response did not include candidates"
            raise ValueError(msg)
        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                return cast(str, part["text"])
        msg = "Google response did not include a text part"
        raise ValueError(msg)
