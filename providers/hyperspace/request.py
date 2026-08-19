"""Native Anthropic Messages request builder for the SAP Hyperspace proxy."""

from __future__ import annotations

from typing import Any

from loguru import logger

from config.constants import (
    ANTHROPIC_DEFAULT_MAX_OUTPUT_TOKENS as HYPERSPACE_DEFAULT_MAX_TOKENS,
)
from core.anthropic.native_messages_request import (
    build_base_native_anthropic_request_body,
)


def build_request_body(request_data: Any, *, thinking_enabled: bool) -> dict:
    """Build an Anthropic-format request body for the Hyperspace messages API.

    Hyperspace is a straight native-Anthropic pass-through relay, so it uses the
    generic base builder (no provider-specific ``transforms``/``plugins`` hooks).
    """
    logger.debug(
        "HYPERSPACE_REQUEST: conversion start model={} msgs={}",
        getattr(request_data, "model", "?"),
        len(getattr(request_data, "messages", [])),
    )

    body = build_base_native_anthropic_request_body(
        request_data,
        default_max_tokens=HYPERSPACE_DEFAULT_MAX_TOKENS,
        thinking_enabled=thinking_enabled,
    )

    logger.debug(
        "HYPERSPACE_REQUEST: conversion done model={} msgs={} tools={}",
        body.get("model"),
        len(body.get("messages", [])),
        len(body.get("tools", [])),
    )
    return body
