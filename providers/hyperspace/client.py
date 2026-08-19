"""SAP Hyperspace (HAI) provider implementation.

Hyperspace exposes a native Anthropic Messages API (default
``http://localhost:6655/anthropic/v1``) backed by the internal AI relay, so
Claude Code traffic passes through unchanged while the relay routes it to
Claude, GPT, or Gemini model families. Transport-wise this is identical to the
OpenRouter native-Anthropic provider: Bearer auth + the ``anthropic-version``
header, with the shared native SSE block policy for thinking-block handling.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from core.anthropic import append_request_id, iter_provider_stream_error_sse_events
from core.anthropic.native_sse_block_policy import (
    NativeSseBlockPolicyState,
    is_terminal_openrouter_done_event,
    parse_native_sse_event,
    transform_native_sse_block_event,
)
from providers.anthropic_messages import AnthropicMessagesTransport, StreamChunkMode
from providers.base import ProviderConfig
from providers.defaults import HYPERSPACE_DEFAULT_BASE

from .request import build_request_body

_ANTHROPIC_VERSION = "2023-06-01"


class HyperspaceProvider(AnthropicMessagesTransport):
    """SAP Hyperspace provider using the native Anthropic-compatible messages API."""

    stream_chunk_mode: StreamChunkMode = "event"

    def __init__(self, config: ProviderConfig):
        super().__init__(
            config,
            provider_name="HYPERSPACE",
            default_base_url=HYPERSPACE_DEFAULT_BASE,
        )

    def _build_request_body(
        self, request: Any, thinking_enabled: bool | None = None
    ) -> dict:
        """Internal helper for tests and direct request dispatch."""
        return build_request_body(
            request,
            thinking_enabled=self._is_thinking_enabled(request, thinking_enabled),
        )

    def _request_headers(self) -> dict[str, str]:
        """Return Hyperspace's Anthropic-compatible messages headers."""
        return {
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "anthropic-version": _ANTHROPIC_VERSION,
        }

    def _new_stream_state(self, request: Any, *, thinking_enabled: bool) -> Any:
        """Create per-stream state for thinking block filtering."""
        return NativeSseBlockPolicyState()

    def _transform_stream_event(
        self,
        event: str,
        state: Any,
        *,
        thinking_enabled: bool,
    ) -> str | None:
        """Drop provider-specific terminal noise and hidden thinking events."""
        if isinstance(state, NativeSseBlockPolicyState):
            event_name, data_text = parse_native_sse_event(event)
            if state.message_stopped or is_terminal_openrouter_done_event(
                event_name, data_text
            ):
                return None
            if event_name == "message_stop":
                state.message_stopped = True

        if isinstance(state, NativeSseBlockPolicyState):
            return transform_native_sse_block_event(
                event, state, thinking_enabled=thinking_enabled
            )
        return event

    def _format_error_message(self, base_message: str, request_id: str | None) -> str:
        """Keep the shared request-id suffix format."""
        return append_request_id(base_message, request_id)

    def _emit_error_events(
        self,
        *,
        request: Any,
        input_tokens: int,
        error_message: str,
        sent_any_event: bool,
    ) -> Iterator[str]:
        """Emit the Anthropic SSE error shape expected by Claude clients."""
        yield from iter_provider_stream_error_sse_events(
            request=request,
            input_tokens=input_tokens,
            error_message=error_message,
            sent_any_event=sent_any_event,
            log_raw_sse_events=self._config.log_raw_sse_events,
        )
