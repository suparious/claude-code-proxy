"""Tests for the SAP Hyperspace (HAI) provider."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from providers.base import ProviderConfig
from providers.hyperspace import HYPERSPACE_DEFAULT_BASE, HyperspaceProvider


class MockMessage:
    def __init__(self, role, content):
        self.role = role
        self.content = content


class MockRequest:
    def __init__(self, **kwargs):
        self.model = "gemini-2.5-pro"
        self.messages = [MockMessage("user", "Hello")]
        self.max_tokens = 100
        self.temperature = 0.5
        self.top_p = 0.9
        self.system = "System prompt"
        self.stop_sequences = None
        self.tools = []
        self.tool_choice = None
        self.metadata = None
        self.extra_body = {}
        self.thinking = MagicMock()
        self.thinking.enabled = True
        for k, v in kwargs.items():
            setattr(self, k, v)

    def model_dump(self, *, exclude_none=False):
        data = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in self.messages],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "system": self.system,
            "stop_sequences": self.stop_sequences,
            "tools": self.tools,
            "tool_choice": self.tool_choice,
            "metadata": self.metadata,
            "extra_body": self.extra_body,
        }
        if exclude_none:
            data = {k: v for k, v in data.items() if v is not None}
        return data


class FakeResponse:
    def __init__(self, *, status_code=200, lines=None, text=""):
        self.status_code = status_code
        self._lines = lines or []
        self._text = text
        self.is_closed = False

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def aread(self):
        return self._text.encode()

    def raise_for_status(self):
        import httpx

        response = httpx.Response(
            self.status_code,
            request=httpx.Request(
                "POST", "http://localhost:6655/anthropic/v1/messages"
            ),
            text=self._text,
        )
        response.raise_for_status()

    async def aclose(self):
        self.is_closed = True


@pytest.fixture
def hyperspace_config():
    return ProviderConfig(
        api_key="test_hyperspace_key",
        base_url="http://localhost:6655/anthropic/v1",
        rate_limit=10,
        rate_window=60,
    )


@pytest.fixture(autouse=True)
def mock_rate_limiter():
    @asynccontextmanager
    async def _slot():
        yield

    with patch("providers.anthropic_messages.GlobalRateLimiter") as mock:
        instance = mock.get_scoped_instance.return_value

        async def _passthrough(fn, *args, **kwargs):
            return await fn(*args, **kwargs)

        instance.execute_with_retry = AsyncMock(side_effect=_passthrough)
        instance.concurrency_slot.side_effect = _slot
        yield instance


@pytest.fixture
def hyperspace_provider(hyperspace_config):
    return HyperspaceProvider(hyperspace_config)


def test_default_base_is_local_anthropic_relay():
    assert HYPERSPACE_DEFAULT_BASE == "http://localhost:6655/anthropic/v1"


def test_init(hyperspace_config):
    """Provider initializes with the configured key and base URL."""
    with patch("httpx.AsyncClient") as mock_client:
        provider = HyperspaceProvider(hyperspace_config)
        assert provider._api_key == "test_hyperspace_key"
        assert provider._base_url == "http://localhost:6655/anthropic/v1"
        mock_client.assert_called_once()


def test_build_request_body_is_native_anthropic(hyperspace_provider):
    body = hyperspace_provider._build_request_body(MockRequest())

    assert body["model"] == "gemini-2.5-pro"
    assert body["temperature"] == 0.5
    assert body["messages"] == [{"role": "user", "content": "Hello"}]
    assert body["system"] == "System prompt"
    # Generic native builder strips the client-only extra_body envelope.
    assert "extra_body" not in body


def test_request_headers_use_bearer_and_anthropic_version(hyperspace_provider):
    headers = hyperspace_provider._request_headers()
    assert headers["Authorization"] == "Bearer test_hyperspace_key"
    assert headers["anthropic-version"] == "2023-06-01"
    assert headers["Accept"] == "text/event-stream"


@pytest.mark.asyncio
async def test_stream_response_passes_native_sse_events(hyperspace_provider):
    response = FakeResponse(
        lines=[
            "event: message_start",
            'data: {"type":"message_start","message":{}}',
            "",
            "event: content_block_delta",
            'data: {"type":"content_block_delta","index":0,'
            '"delta":{"type":"text_delta","text":"Hello"}}',
            "",
            "event: message_stop",
            'data: {"type":"message_stop"}',
            "",
            "event: data",
            "data: [DONE]",
            "",
        ]
    )

    with (
        patch.object(hyperspace_provider._client, "build_request") as mock_build,
        patch.object(
            hyperspace_provider._client,
            "send",
            new_callable=AsyncMock,
            return_value=response,
        ),
    ):
        events = [e async for e in hyperspace_provider.stream_response(MockRequest())]

    _, kwargs = mock_build.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer test_hyperspace_key"
    assert kwargs["headers"]["anthropic-version"] == "2023-06-01"
    assert events[0].startswith("event: message_start")
    assert events[-1].startswith("event: message_stop")
    assert any("Hello" in event for event in events)
    assert "[DONE]" not in "".join(events)
    assert response.is_closed
