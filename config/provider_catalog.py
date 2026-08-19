"""Neutral provider catalog: IDs, credentials, defaults, proxy and capability metadata.

Adapter factories live in :mod:`providers.registry`; this module stays free of
provider implementation imports (see contract tests).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

TransportType = Literal["openai_chat", "anthropic_messages"]

# Default upstream base URLs (also re-exported via :mod:`providers.defaults`)
NVIDIA_NIM_DEFAULT_BASE = "https://integrate.api.nvidia.com/v1"
# DeepSeek Anthropic-compatible Messages API (not OpenAI ``/v1`` chat completions).
DEEPSEEK_ANTHROPIC_DEFAULT_BASE = "https://api.deepseek.com/anthropic"
# Historical export name: DeepSeek upstream is the native Anthropic path above.
DEEPSEEK_DEFAULT_BASE = DEEPSEEK_ANTHROPIC_DEFAULT_BASE
OPENROUTER_DEFAULT_BASE = "https://openrouter.ai/api/v1"
LMSTUDIO_DEFAULT_BASE = "http://localhost:1234/v1"
LLAMACPP_DEFAULT_BASE = "http://localhost:8080/v1"
OLLAMA_DEFAULT_BASE = "http://localhost:11434"
FRIENDLIAI_DEFAULT_BASE = "https://api.friendli.ai/serverless/v1"
FIREWORKS_DEFAULT_BASE = "https://api.fireworks.ai/inference/v1"
VLLM_DEFAULT_BASE = "http://localhost:8000/v1"
CLIPROXYAPI_DEFAULT_BASE = "http://localhost:8317/v1"
GROQ_DEFAULT_BASE = "https://api.groq.com/openai/v1"
CEREBRAS_DEFAULT_BASE = "https://api.cerebras.ai/v1"
TOGETHER_DEFAULT_BASE = "https://api.together.xyz/v1"
KIMI_DEFAULT_BASE = "https://api.moonshot.ai/v1"
# SAP Hyperspace AI proxy (HAI). Exposes a native Anthropic Messages API at
# ``/anthropic/v1`` backed by the internal proxy, so Claude Code can route to
# Claude, GPT, and Gemini model families through a single approved endpoint.
HYPERSPACE_DEFAULT_BASE = "http://localhost:6655/anthropic/v1"


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    """Metadata for building :class:`~providers.base.ProviderConfig` and factory wiring."""

    provider_id: str
    transport_type: TransportType
    capabilities: tuple[str, ...]
    credential_env: str | None = None
    credential_url: str | None = None
    credential_attr: str | None = None
    credential_list_attr: str | None = None
    key_usage_limit_attr: str | None = None
    static_credential: str | None = None
    default_base_url: str | None = None
    base_url_attr: str | None = None
    proxy_attr: str | None = None


PROVIDER_CATALOG: dict[str, ProviderDescriptor] = {
    "nvidia_nim": ProviderDescriptor(
        provider_id="nvidia_nim",
        transport_type="openai_chat",
        credential_env="NVIDIA_NIM_API_KEY",
        credential_url="https://build.nvidia.com/settings/api-keys",
        credential_attr="nvidia_nim_api_key",
        credential_list_attr="nvidia_nim_api_keys",
        key_usage_limit_attr="nvidia_nim_key_usage_limit",
        default_base_url=NVIDIA_NIM_DEFAULT_BASE,
        proxy_attr="nvidia_nim_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "rate_limit"),
    ),
    "open_router": ProviderDescriptor(
        provider_id="open_router",
        transport_type="anthropic_messages",
        credential_env="OPENROUTER_API_KEY",
        credential_url="https://openrouter.ai/keys",
        credential_attr="open_router_api_key",
        credential_list_attr="open_router_api_keys",
        key_usage_limit_attr="open_router_key_usage_limit",
        default_base_url=OPENROUTER_DEFAULT_BASE,
        proxy_attr="open_router_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "native_anthropic"),
    ),
    "deepseek": ProviderDescriptor(
        provider_id="deepseek",
        transport_type="anthropic_messages",
        credential_env="DEEPSEEK_API_KEY",
        credential_url="https://platform.deepseek.com/api_keys",
        credential_attr="deepseek_api_key",
        credential_list_attr="deepseek_api_keys",
        key_usage_limit_attr="deepseek_key_usage_limit",
        default_base_url=DEEPSEEK_ANTHROPIC_DEFAULT_BASE,
        capabilities=("chat", "streaming", "tools", "thinking", "native_anthropic"),
    ),
    "lmstudio": ProviderDescriptor(
        provider_id="lmstudio",
        transport_type="anthropic_messages",
        credential_env="LM_STUDIO_API_KEY",
        credential_attr="lm_studio_api_key",
        static_credential="lm-studio",
        default_base_url=LMSTUDIO_DEFAULT_BASE,
        base_url_attr="lm_studio_base_url",
        proxy_attr="lmstudio_proxy",
        capabilities=("chat", "streaming", "tools", "native_anthropic", "local"),
    ),
    "llamacpp": ProviderDescriptor(
        provider_id="llamacpp",
        transport_type="anthropic_messages",
        static_credential="llamacpp",
        default_base_url=LLAMACPP_DEFAULT_BASE,
        base_url_attr="llamacpp_base_url",
        proxy_attr="llamacpp_proxy",
        capabilities=("chat", "streaming", "tools", "native_anthropic", "local"),
    ),
    "ollama": ProviderDescriptor(
        provider_id="ollama",
        transport_type="anthropic_messages",
        static_credential="ollama",
        default_base_url=OLLAMA_DEFAULT_BASE,
        base_url_attr="ollama_base_url",
        capabilities=(
            "chat",
            "streaming",
            "tools",
            "thinking",
            "native_anthropic",
            "local",
        ),
    ),
    "friendliai": ProviderDescriptor(
        provider_id="friendliai",
        transport_type="anthropic_messages",
        credential_env="FRIENDLIAI_API_KEY",
        credential_url="https://friendli.ai",
        credential_attr="friendliai_api_key",
        credential_list_attr="friendliai_api_keys",
        key_usage_limit_attr="friendliai_key_usage_limit",
        default_base_url=FRIENDLIAI_DEFAULT_BASE,
        proxy_attr="friendliai_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "native_anthropic"),
    ),
    "fireworks": ProviderDescriptor(
        provider_id="fireworks",
        transport_type="anthropic_messages",
        credential_env="FIREWORKS_API_KEY",
        credential_url="https://fireworks.ai/account/api-keys",
        credential_attr="fireworks_api_key",
        credential_list_attr="fireworks_api_keys",
        key_usage_limit_attr="fireworks_key_usage_limit",
        default_base_url=FIREWORKS_DEFAULT_BASE,
        proxy_attr="fireworks_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "native_anthropic"),
    ),
    "vllm": ProviderDescriptor(
        provider_id="vllm",
        transport_type="anthropic_messages",
        static_credential="vllm",
        default_base_url=VLLM_DEFAULT_BASE,
        base_url_attr="vllm_base_url",
        proxy_attr="vllm_proxy",
        capabilities=("chat", "streaming", "tools", "native_anthropic", "local"),
    ),
    "cliproxyapi": ProviderDescriptor(
        provider_id="cliproxyapi",
        transport_type="anthropic_messages",
        static_credential="dummy",
        default_base_url=CLIPROXYAPI_DEFAULT_BASE,
        base_url_attr="cliproxyapi_base_url",
        proxy_attr="cliproxyapi_proxy",
        capabilities=(
            "chat",
            "streaming",
            "tools",
            "thinking",
            "native_anthropic",
            "local",
        ),
    ),
    "groq": ProviderDescriptor(
        provider_id="groq",
        transport_type="openai_chat",
        credential_env="GROQ_API_KEY",
        credential_url="https://console.groq.com/keys",
        credential_attr="groq_api_key",
        credential_list_attr="groq_api_keys",
        key_usage_limit_attr="groq_key_usage_limit",
        default_base_url=GROQ_DEFAULT_BASE,
        proxy_attr="groq_proxy",
        capabilities=("chat", "streaming", "tools", "rate_limit"),
    ),
    "cerebras": ProviderDescriptor(
        provider_id="cerebras",
        transport_type="openai_chat",
        credential_env="CEREBRAS_API_KEY",
        credential_url="https://cloud.cerebras.ai",
        credential_attr="cerebras_api_key",
        credential_list_attr="cerebras_api_keys",
        key_usage_limit_attr="cerebras_key_usage_limit",
        default_base_url=CEREBRAS_DEFAULT_BASE,
        proxy_attr="cerebras_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "rate_limit"),
    ),
    "together": ProviderDescriptor(
        provider_id="together",
        transport_type="openai_chat",
        credential_env="TOGETHER_API_KEY",
        credential_url="https://api.together.xyz",
        credential_attr="together_api_key",
        credential_list_attr="together_api_keys",
        key_usage_limit_attr="together_key_usage_limit",
        default_base_url=TOGETHER_DEFAULT_BASE,
        proxy_attr="together_proxy",
        capabilities=("chat", "streaming", "tools", "rate_limit"),
    ),
    "kimi": ProviderDescriptor(
        provider_id="kimi",
        transport_type="openai_chat",
        credential_env="KIMI_API_KEY",
        credential_url="https://platform.moonshot.ai/console/api-keys",
        credential_attr="kimi_api_key",
        credential_list_attr="kimi_api_keys",
        key_usage_limit_attr="kimi_key_usage_limit",
        default_base_url=KIMI_DEFAULT_BASE,
        proxy_attr="kimi_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "rate_limit"),
    ),
    "hyperspace": ProviderDescriptor(
        provider_id="hyperspace",
        transport_type="anthropic_messages",
        credential_env="HYPERSPACE_API_KEY",
        credential_url="https://hyperspace.only.sap",
        credential_attr="hyperspace_api_key",
        credential_list_attr="hyperspace_api_keys",
        key_usage_limit_attr="hyperspace_key_usage_limit",
        default_base_url=HYPERSPACE_DEFAULT_BASE,
        base_url_attr="hyperspace_base_url",
        proxy_attr="hyperspace_proxy",
        capabilities=("chat", "streaming", "tools", "thinking", "native_anthropic"),
    ),
}

# Order matches docs / historical error text; must match PROVIDER_CATALOG keys.
SUPPORTED_PROVIDER_IDS: tuple[str, ...] = tuple(PROVIDER_CATALOG.keys())

if len(set(SUPPORTED_PROVIDER_IDS)) != len(SUPPORTED_PROVIDER_IDS):
    raise AssertionError("Duplicate provider ids in PROVIDER_CATALOG key order")
