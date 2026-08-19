"""Centralized configuration using Pydantic Settings."""

import os
import re
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from dotenv import dotenv_values
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from .constants import HTTP_CONNECT_TIMEOUT_DEFAULT
from .nim import NimSettings
from .provider_ids import SUPPORTED_PROVIDER_IDS


def _env_files() -> tuple[Path, ...]:
    """Return env file paths in priority order (later overrides earlier)."""
    files: list[Path] = [
        # Legacy config path is read first; the renamed proxy config overrides it.
        Path.home() / ".config" / "free-claude-code" / ".env",
        Path.home() / ".config" / "claude-code-proxy" / ".env",
        Path(".env"),
    ]
    if explicit := os.environ.get("FCC_ENV_FILE"):
        files.append(Path(explicit))
    return tuple(files)


def _configured_env_files(model_config: Mapping[str, Any]) -> tuple[Path, ...]:
    """Return the currently configured env files for Settings."""
    configured = model_config.get("env_file")
    if configured is None:
        return ()
    if isinstance(configured, (str, Path)):
        return (Path(configured),)
    return tuple(Path(item) for item in configured)


def _env_file_contains_key(path: Path, key: str) -> bool:
    """Check whether a dotenv-style file defines the given key."""
    return _env_file_value(path, key) is not None


def _env_file_value(path: Path, key: str) -> str | None:
    """Return a dotenv value when the file explicitly defines the key."""
    if not path.is_file():
        return None

    try:
        values = dotenv_values(path)
    except OSError:
        return None

    if key not in values:
        return None
    value = values[key]
    return "" if value is None else value


def _env_file_override(model_config: Mapping[str, Any], key: str) -> str | None:
    """Return the last configured dotenv value that explicitly defines a key."""
    configured_value: str | None = None
    for env_file in _configured_env_files(model_config):
        value = _env_file_value(env_file, key)
        if value is not None:
            configured_value = value
    return configured_value


def _removed_env_var_message(model_config: Mapping[str, Any]) -> str | None:
    """Return a migration error for removed env vars, if present."""
    removed_keys = ("NIM_ENABLE_THINKING", "ENABLE_THINKING")
    replacement = (
        "ENABLE_MODEL_THINKING, ENABLE_OPUS_THINKING, "
        "ENABLE_SONNET_THINKING, or ENABLE_HAIKU_THINKING"
    )

    for removed_key in removed_keys:
        if removed_key in os.environ:
            return (
                f"{removed_key} has been removed in this release. "
                f"Rename it to {replacement}."
            )

        for env_file in _configured_env_files(model_config):
            if _env_file_contains_key(env_file, removed_key):
                return (
                    f"{removed_key} has been removed in this release. "
                    f"Rename it to {replacement}. Found in {env_file}."
                )

    return None


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ==================== OpenRouter Config ====================
    open_router_api_key: str = Field(default="", validation_alias="OPENROUTER_API_KEY")
    open_router_api_keys: Annotated[tuple[str, ...], NoDecode] = Field(
        default=(), validation_alias="OPENROUTER_API_KEYS"
    )
    open_router_key_usage_limit: int = Field(
        default=0, validation_alias="OPENROUTER_KEY_USAGE_LIMIT"
    )

    # ==================== DeepSeek Config ====================
    deepseek_api_key: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")
    deepseek_api_keys: Annotated[tuple[str, ...], NoDecode] = Field(
        default=(), validation_alias="DEEPSEEK_API_KEYS"
    )
    deepseek_key_usage_limit: int = Field(
        default=0, validation_alias="DEEPSEEK_KEY_USAGE_LIMIT"
    )

    # ==================== NVIDIA NIM Config ====================
    nvidia_nim_api_key: str = ""
    nvidia_nim_api_keys: Annotated[tuple[str, ...], NoDecode] = Field(
        default=(), validation_alias="NVIDIA_NIM_API_KEYS"
    )
    nvidia_nim_key_usage_limit: int = Field(
        default=0, validation_alias="NVIDIA_NIM_KEY_USAGE_LIMIT"
    )

    # ==================== LM Studio Config ====================
    lm_studio_base_url: str = Field(
        default="http://localhost:1234/v1",
        validation_alias="LM_STUDIO_BASE_URL",
    )
    lm_studio_api_key: str = Field(
        default="lm-studio", validation_alias="LM_STUDIO_API_KEY"
    )

    # ==================== Llama.cpp Config ====================
    llamacpp_base_url: str = Field(
        default="http://localhost:8080/v1",
        validation_alias="LLAMACPP_BASE_URL",
    )

    # ==================== Ollama Config ====================
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        validation_alias="OLLAMA_BASE_URL",
    )

    # ==================== FriendliAI Config ====================
    friendliai_api_key: str = Field(default="", validation_alias="FRIENDLIAI_API_KEY")
    friendliai_api_keys: Annotated[tuple[str, ...], NoDecode] = Field(
        default=(), validation_alias="FRIENDLIAI_API_KEYS"
    )
    friendliai_key_usage_limit: int = Field(
        default=0, validation_alias="FRIENDLIAI_KEY_USAGE_LIMIT"
    )

    # ==================== SAP Hyperspace (HAI) Config ====================
    # Native Anthropic Messages proxy (default local HAI relay). Point
    # HYPERSPACE_BASE_URL at your relay's ``/anthropic/v1`` endpoint.
    hyperspace_base_url: str = Field(
        default="http://localhost:6655/anthropic/v1",
        validation_alias="HYPERSPACE_BASE_URL",
    )
    hyperspace_api_key: str = Field(default="", validation_alias="HYPERSPACE_API_KEY")
    hyperspace_api_keys: Annotated[tuple[str, ...], NoDecode] = Field(
        default=(), validation_alias="HYPERSPACE_API_KEYS"
    )
    hyperspace_key_usage_limit: int = Field(
        default=0, validation_alias="HYPERSPACE_KEY_USAGE_LIMIT"
    )

    # ==================== Model ====================
    # All Claude model requests are mapped to this single model (fallback)
    # Format: provider_type/model/name
    model: str = "nvidia_nim/z-ai/glm4.7"

    # Per-model overrides (optional, falls back to MODEL)
    # Each can use a different provider
    model_opus: str | None = Field(default=None, validation_alias="MODEL_OPUS")
    model_sonnet: str | None = Field(default=None, validation_alias="MODEL_SONNET")
    model_haiku: str | None = Field(default=None, validation_alias="MODEL_HAIKU")

    # ==================== Per-Provider Proxy ====================
    nvidia_nim_proxy: str = Field(default="", validation_alias="NVIDIA_NIM_PROXY")
    open_router_proxy: str = Field(default="", validation_alias="OPENROUTER_PROXY")
    lmstudio_proxy: str = Field(default="", validation_alias="LMSTUDIO_PROXY")
    llamacpp_proxy: str = Field(default="", validation_alias="LLAMACPP_PROXY")
    friendliai_proxy: str = Field(default="", validation_alias="FRIENDLIAI_PROXY")
    hyperspace_proxy: str = Field(default="", validation_alias="HYPERSPACE_PROXY")

    # ==================== Fireworks AI Config ====================
    fireworks_api_key: str = Field(default="", validation_alias="FIREWORKS_API_KEY")
    fireworks_api_keys: Annotated[tuple[str, ...], NoDecode] = Field(
        default=(), validation_alias="FIREWORKS_API_KEYS"
    )
    fireworks_key_usage_limit: int = Field(
        default=0, validation_alias="FIREWORKS_KEY_USAGE_LIMIT"
    )
    fireworks_proxy: str = Field(default="", validation_alias="FIREWORKS_PROXY")

    # ==================== vLLM Config ====================
    vllm_base_url: str = Field(
        default="http://localhost:8000/v1",
        validation_alias="VLLM_BASE_URL",
    )
    vllm_proxy: str = Field(default="", validation_alias="VLLM_PROXY")

    # ==================== CLIProxyAPI Config ====================
    cliproxyapi_base_url: str = Field(
        default="http://localhost:8317/v1",
        validation_alias="CLIPROXYAPI_BASE_URL",
    )
    cliproxyapi_proxy: str = Field(default="", validation_alias="CLIPROXYAPI_PROXY")

    # ==================== Groq Config ====================
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")
    groq_api_keys: Annotated[tuple[str, ...], NoDecode] = Field(
        default=(), validation_alias="GROQ_API_KEYS"
    )
    groq_key_usage_limit: int = Field(
        default=0, validation_alias="GROQ_KEY_USAGE_LIMIT"
    )
    groq_proxy: str = Field(default="", validation_alias="GROQ_PROXY")

    # ==================== Cerebras Config ====================
    cerebras_api_key: str = Field(default="", validation_alias="CEREBRAS_API_KEY")
    cerebras_api_keys: Annotated[tuple[str, ...], NoDecode] = Field(
        default=(), validation_alias="CEREBRAS_API_KEYS"
    )
    cerebras_key_usage_limit: int = Field(
        default=0, validation_alias="CEREBRAS_KEY_USAGE_LIMIT"
    )
    cerebras_proxy: str = Field(default="", validation_alias="CEREBRAS_PROXY")

    # ==================== Together AI Config ====================
    together_api_key: str = Field(default="", validation_alias="TOGETHER_API_KEY")
    together_api_keys: Annotated[tuple[str, ...], NoDecode] = Field(
        default=(), validation_alias="TOGETHER_API_KEYS"
    )
    together_key_usage_limit: int = Field(
        default=0, validation_alias="TOGETHER_KEY_USAGE_LIMIT"
    )
    together_proxy: str = Field(default="", validation_alias="TOGETHER_PROXY")

    # ==================== Kimi / Moonshot Config ====================
    kimi_api_key: str = Field(default="", validation_alias="KIMI_API_KEY")
    kimi_api_keys: Annotated[tuple[str, ...], NoDecode] = Field(
        default=(), validation_alias="KIMI_API_KEYS"
    )
    kimi_key_usage_limit: int = Field(
        default=0, validation_alias="KIMI_KEY_USAGE_LIMIT"
    )
    kimi_proxy: str = Field(default="", validation_alias="KIMI_PROXY")

    # ==================== Provider Rate Limiting ====================
    provider_rate_limit: int = Field(default=40, validation_alias="PROVIDER_RATE_LIMIT")
    provider_rate_window: int = Field(
        default=60, validation_alias="PROVIDER_RATE_WINDOW"
    )
    provider_max_concurrency: int = Field(
        default=5, validation_alias="PROVIDER_MAX_CONCURRENCY"
    )
    provider_max_retries: int = Field(
        default=8, validation_alias="PROVIDER_MAX_RETRIES"
    )
    provider_retry_base_delay: float = Field(
        default=2.0, validation_alias="PROVIDER_RETRY_BASE_DELAY"
    )
    provider_retry_max_delay: float = Field(
        default=120.0, validation_alias="PROVIDER_RETRY_MAX_DELAY"
    )
    enable_model_thinking: bool = Field(
        default=True, validation_alias="ENABLE_MODEL_THINKING"
    )
    enable_opus_thinking: bool | None = Field(
        default=None, validation_alias="ENABLE_OPUS_THINKING"
    )
    enable_sonnet_thinking: bool | None = Field(
        default=None, validation_alias="ENABLE_SONNET_THINKING"
    )
    enable_haiku_thinking: bool | None = Field(
        default=None, validation_alias="ENABLE_HAIKU_THINKING"
    )

    # ==================== HTTP Client Timeouts ====================
    http_read_timeout: float | None = Field(
        default=None, validation_alias="HTTP_READ_TIMEOUT"
    )
    http_write_timeout: float = Field(
        default=60.0, validation_alias="HTTP_WRITE_TIMEOUT"
    )
    http_connect_timeout: float = Field(
        default=HTTP_CONNECT_TIMEOUT_DEFAULT,
        validation_alias="HTTP_CONNECT_TIMEOUT",
    )

    # ==================== Fast Prefix Detection ====================
    fast_prefix_detection: bool = True

    # ==================== Optimizations ====================
    enable_network_probe_mock: bool = True
    enable_title_generation_skip: bool = True
    enable_suggestion_mode_skip: bool = True
    enable_filepath_extraction_mock: bool = True

    # ==================== Local web server tools (web_search / web_fetch) ====================
    # Off by default: these tools perform outbound HTTP from the proxy (SSRF risk).
    enable_web_server_tools: bool = Field(
        default=False, validation_alias="ENABLE_WEB_SERVER_TOOLS"
    )
    # Comma-separated URL schemes allowed for web_fetch (default: http,https).
    web_fetch_allowed_schemes: str = Field(
        default="http,https", validation_alias="WEB_FETCH_ALLOWED_SCHEMES"
    )
    # When true, skip private/loopback/link-local IP blocking for web_fetch (lab only).
    web_fetch_allow_private_networks: bool = Field(
        default=False, validation_alias="WEB_FETCH_ALLOW_PRIVATE_NETWORKS"
    )

    # ==================== Debug / diagnostic logging (avoid sensitive content) ====================
    # When false (default), API and SSE helpers log only metadata (counts, lengths, ids).
    log_raw_api_payloads: bool = Field(
        default=False, validation_alias="LOG_RAW_API_PAYLOADS"
    )
    log_raw_sse_events: bool = Field(
        default=False, validation_alias="LOG_RAW_SSE_EVENTS"
    )
    # When false (default), unhandled exceptions log only type + route metadata (no message/traceback).
    log_api_error_tracebacks: bool = Field(
        default=False, validation_alias="LOG_API_ERROR_TRACEBACKS"
    )
    # ==================== NIM Settings ====================
    nim: NimSettings = Field(default_factory=NimSettings)

    # ==================== Server ====================
    host: str = "0.0.0.0"
    port: int = 8082
    log_file: str = "server.log"
    # Optional server API key to protect endpoints (Anthropic-style)
    # Set via env `ANTHROPIC_AUTH_TOKEN`. When empty, no auth is required.
    anthropic_auth_token: str = Field(
        default="", validation_alias="ANTHROPIC_AUTH_TOKEN"
    )

    @model_validator(mode="before")
    @classmethod
    def reject_removed_env_vars(cls, data: Any) -> Any:
        """Fail fast when removed environment variables are still configured."""
        if message := _removed_env_var_message(cls.model_config):
            raise ValueError(message)
        return data

    # Handle empty strings for optional string fields
    @field_validator(
        "model_opus",
        "model_sonnet",
        "model_haiku",
        "enable_opus_thinking",
        "enable_sonnet_thinking",
        "enable_haiku_thinking",
        mode="before",
    )
    @classmethod
    def parse_optional_str(cls, v: Any) -> Any:
        if v == "":
            return None
        return v

    @field_validator("http_read_timeout", mode="before")
    @classmethod
    def parse_optional_read_timeout(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in ("", "none", "null", "off", "disabled"):
                return None
        return v

    @field_validator(
        "open_router_api_keys",
        "deepseek_api_keys",
        "nvidia_nim_api_keys",
        "friendliai_api_keys",
        "fireworks_api_keys",
        "groq_api_keys",
        "cerebras_api_keys",
        "together_api_keys",
        "kimi_api_keys",
        "hyperspace_api_keys",
        mode="before",
    )
    @classmethod
    def parse_api_key_tuple(cls, v: Any) -> Any:
        if isinstance(v, str):
            if not v.strip():
                return ()
            return tuple(
                part.strip() for part in re.split(r"[\s,]+", v) if part.strip()
            )
        if isinstance(v, list | tuple):
            return tuple(str(part).strip() for part in v if str(part).strip())
        return v

    @field_validator(
        "open_router_key_usage_limit",
        "deepseek_key_usage_limit",
        "nvidia_nim_key_usage_limit",
        "friendliai_key_usage_limit",
        "fireworks_key_usage_limit",
        "groq_key_usage_limit",
        "cerebras_key_usage_limit",
        "together_key_usage_limit",
        "kimi_key_usage_limit",
        "hyperspace_key_usage_limit",
    )
    @classmethod
    def validate_key_usage_limit(cls, v: int) -> int:
        if v < 0:
            raise ValueError("key usage limits must be >= 0")
        return v

    @field_validator("http_read_timeout")
    @classmethod
    def normalize_read_timeout(cls, v: float | None) -> float | None:
        if v is None or v <= 0:
            return None
        return v

    @field_validator("web_fetch_allowed_schemes")
    @classmethod
    def validate_web_fetch_allowed_schemes(cls, v: str) -> str:
        schemes = [part.strip().lower() for part in v.split(",") if part.strip()]
        if not schemes:
            raise ValueError("web_fetch_allowed_schemes must list at least one scheme")
        for scheme in schemes:
            if not scheme.isascii() or not scheme.isalpha():
                raise ValueError(
                    f"Invalid URL scheme in web_fetch_allowed_schemes: {scheme!r}"
                )
        return ",".join(schemes)

    @field_validator("ollama_base_url")
    @classmethod
    def validate_ollama_base_url(cls, v: str) -> str:
        if v.rstrip("/").endswith("/v1"):
            raise ValueError(
                "OLLAMA_BASE_URL must be the Ollama root URL for native Anthropic "
                "messages, e.g. http://localhost:11434 (without /v1)."
            )
        return v

    @field_validator("model", "model_opus", "model_sonnet", "model_haiku")
    @classmethod
    def validate_model_format(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if "/" not in v:
            raise ValueError(
                f"Model must be prefixed with provider type. "
                f"Valid providers: {', '.join(SUPPORTED_PROVIDER_IDS)}. "
                f"Format: provider_type/model/name"
            )
        provider = v.split("/", 1)[0]
        if provider not in SUPPORTED_PROVIDER_IDS:
            supported = ", ".join(f"'{p}'" for p in SUPPORTED_PROVIDER_IDS)
            raise ValueError(f"Invalid provider: '{provider}'. Supported: {supported}")
        return v

    @model_validator(mode="after")
    def prefer_dotenv_anthropic_auth_token(self) -> Settings:
        """Let explicit .env auth config override stale shell/client tokens."""
        dotenv_value = _env_file_override(self.model_config, "ANTHROPIC_AUTH_TOKEN")
        if dotenv_value is not None:
            self.anthropic_auth_token = dotenv_value
        return self

    def uses_process_anthropic_auth_token(self) -> bool:
        """Return whether proxy auth came from process env, not dotenv config."""
        if _env_file_override(self.model_config, "ANTHROPIC_AUTH_TOKEN") is not None:
            return False
        return bool(os.environ.get("ANTHROPIC_AUTH_TOKEN"))

    @property
    def provider_type(self) -> str:
        """Extract provider type from the default model string."""
        return Settings.parse_provider_type(self.model)

    @property
    def model_name(self) -> str:
        """Extract the actual model name from the default model string."""
        return Settings.parse_model_name(self.model)

    def resolve_model(self, claude_model_name: str) -> str:
        """Resolve a Claude model name to the configured provider/model string.

        Classifies the incoming Claude model (opus/sonnet/haiku) and
        returns the model-specific override if configured, otherwise the fallback MODEL.
        """
        name_lower = claude_model_name.lower()
        if "opus" in name_lower and self.model_opus is not None:
            return self.model_opus
        if "haiku" in name_lower and self.model_haiku is not None:
            return self.model_haiku
        if "sonnet" in name_lower and self.model_sonnet is not None:
            return self.model_sonnet
        return self.model

    def resolve_thinking(self, claude_model_name: str) -> bool:
        """Resolve whether thinking is enabled for an incoming Claude model name."""
        name_lower = claude_model_name.lower()
        if "opus" in name_lower and self.enable_opus_thinking is not None:
            return self.enable_opus_thinking
        if "haiku" in name_lower and self.enable_haiku_thinking is not None:
            return self.enable_haiku_thinking
        if "sonnet" in name_lower and self.enable_sonnet_thinking is not None:
            return self.enable_sonnet_thinking
        return self.enable_model_thinking

    def web_fetch_allowed_scheme_set(self) -> frozenset[str]:
        """Return normalized schemes allowed for web_fetch."""
        return frozenset(
            part.strip().lower()
            for part in self.web_fetch_allowed_schemes.split(",")
            if part.strip()
        )

    @staticmethod
    def parse_provider_type(model_string: str) -> str:
        """Extract provider type from any 'provider/model' string."""
        return model_string.split("/", 1)[0]

    @staticmethod
    def parse_model_name(model_string: str) -> str:
        """Extract model name from any 'provider/model' string."""
        return model_string.split("/", 1)[1]

    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
