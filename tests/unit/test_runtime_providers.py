from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from ebrag.extraction.llm_client import (
    AnthropicJSONClient,
    FakeLLMClient,
    GoogleJSONClient,
    OpenAICompatibleJSONClient,
)
from ebrag.providers import build_extraction_client
from ebrag.settings import AppSettings


def test_llm_settings_select_openai_compatible_client() -> None:
    settings = AppSettings(
        llm={
            "provider": "openai",
            "api_key": "test-key",
            "model": "gpt-test",
            "base_url": "https://llm.example/v1",
        }
    )

    client = build_extraction_client(settings)

    assert isinstance(client, OpenAICompatibleJSONClient)


@pytest.mark.parametrize(
    ("provider", "expected_type"),
    [
        ("fake", FakeLLMClient),
        ("anthropic", AnthropicJSONClient),
        ("google", GoogleJSONClient),
    ],
)
def test_llm_provider_factory_selects_configured_client(
    provider: str,
    expected_type: type[object],
) -> None:
    settings = AppSettings(
        llm={
            "provider": provider,
            "api_key": "test-key",
            "model": "runtime-test",
        }
    )

    client = build_extraction_client(settings)

    assert isinstance(client, expected_type)


def test_openai_compatible_client_requests_json_and_parses_content() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "paper_id": "P00000001",
                                    "results": [],
                                    "extraction_status": "unverified",
                                }
                            )
                        }
                    }
                ]
            },
        )

    client = OpenAICompatibleJSONClient(
        api_key="test-key",
        model="gpt-test",
        base_url="https://llm.example/v1",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    payload = client.complete_json(prompt="Return JSON", paper_id="P00000001")

    assert captured["url"] == "https://llm.example/v1/chat/completions"
    assert captured["body"]["model"] == "gpt-test"
    assert captured["body"]["response_format"] == {"type": "json_object"}
    assert payload["paper_id"] == "P00000001"


def test_structured_client_rejects_invalid_json_response() -> None:
    client = OpenAICompatibleJSONClient(
        api_key="test-key",
        model="gpt-test",
        base_url="https://llm.example/v1",
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(
                    200,
                    json={"choices": [{"message": {"content": "not-json"}}]},
                )
            )
        ),
    )

    with pytest.raises(ValueError, match="valid JSON"):
        client.complete_json(prompt="Return JSON", paper_id="P00000001")


def test_anthropic_client_parses_text_block_json() -> None:
    client = AnthropicJSONClient(
        api_key="test-key",
        model="claude-test",
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(
                    200,
                    json={
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    {
                                        "answer_id": "answer-1",
                                        "abstained": True,
                                        "sentences": [],
                                        "reasons": ["no evidence"],
                                    }
                                ),
                            }
                        ]
                    },
                )
            )
        ),
    )

    payload = client.synthesize_json(prompt="Return JSON", evidence_pack=_dummy_pack())

    assert payload["answer_id"] == "answer-1"


def test_google_client_parses_candidate_part_json() -> None:
    client = GoogleJSONClient(
        api_key="test-key",
        model="gemini-test",
        http_client=httpx.Client(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(
                    200,
                    json={
                        "candidates": [
                            {
                                "content": {
                                    "parts": [
                                        {
                                            "text": json.dumps(
                                                {
                                                    "claim_id": "CLM00000001",
                                                    "verdict": "supported",
                                                    "reason": "supported by evidence",
                                                }
                                            )
                                        }
                                    ]
                                }
                            }
                        ]
                    },
                )
            )
        ),
    )

    payload = client.complete_json(prompt="Return JSON", paper_id="P00000001")

    assert payload["verdict"] == "supported"


def _dummy_pack() -> Any:
    return {
        "query": "Does compound X work?",
        "route": [],
        "eligible_results": [],
        "supporting_evidence": [],
        "sufficiency": "insufficient",
        "sufficiency_reason": "no evidence",
    }
