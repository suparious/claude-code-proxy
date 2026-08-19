"""Provider descriptors, factory, and runtime registry."""

from __future__ import annotations

from collections.abc import Callable, MutableMapping

from config.provider_catalog import (
    PROVIDER_CATALOG,
    SUPPORTED_PROVIDER_IDS,
    ProviderDescriptor,
)
from config.settings import Settings
from providers.base import BaseProvider, ProviderConfig
from providers.exceptions import AuthenticationError, UnknownProviderTypeError

ProviderFactory = Callable[[ProviderConfig, Settings], BaseProvider]

# Backwards-compatible name for the catalog (single source: ``config.provider_catalog``).
PROVIDER_DESCRIPTORS: dict[str, ProviderDescriptor] = PROVIDER_CATALOG


def _create_nvidia_nim(config: ProviderConfig, settings: Settings) -> BaseProvider:
    from providers.nvidia_nim import NvidiaNimProvider

    return NvidiaNimProvider(config, nim_settings=settings.nim)


def _create_open_router(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.open_router import OpenRouterProvider

    return OpenRouterProvider(config)


def _create_deepseek(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.deepseek import DeepSeekProvider

    return DeepSeekProvider(config)


def _create_lmstudio(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.lmstudio import LMStudioProvider

    return LMStudioProvider(config)


def _create_llamacpp(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.llamacpp import LlamaCppProvider

    return LlamaCppProvider(config)


def _create_ollama(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.ollama import OllamaProvider

    return OllamaProvider(config)


def _create_friendliai(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.friendliai import FriendliAIProvider

    return FriendliAIProvider(config)


def _create_fireworks(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.fireworks import FireworksProvider

    return FireworksProvider(config)


def _create_vllm(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.vllm import VllmProvider

    return VllmProvider(config)


def _create_cliproxyapi(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.cliproxyapi import CLIProxyAPIProvider

    return CLIProxyAPIProvider(config)


def _create_groq(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.groq import GroqProvider

    return GroqProvider(config)


def _create_cerebras(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.cerebras import CerebrasProvider

    return CerebrasProvider(config)


def _create_together(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.together import TogetherProvider

    return TogetherProvider(config)


def _create_kimi(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.kimi import KimiProvider

    return KimiProvider(config)


def _create_hyperspace(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.hyperspace import HyperspaceProvider

    return HyperspaceProvider(config)


PROVIDER_FACTORIES: dict[str, ProviderFactory] = {
    "nvidia_nim": _create_nvidia_nim,
    "open_router": _create_open_router,
    "deepseek": _create_deepseek,
    "lmstudio": _create_lmstudio,
    "llamacpp": _create_llamacpp,
    "ollama": _create_ollama,
    "friendliai": _create_friendliai,
    "fireworks": _create_fireworks,
    "vllm": _create_vllm,
    "cliproxyapi": _create_cliproxyapi,
    "groq": _create_groq,
    "cerebras": _create_cerebras,
    "together": _create_together,
    "kimi": _create_kimi,
    "hyperspace": _create_hyperspace,
}

if set(PROVIDER_DESCRIPTORS) != set(SUPPORTED_PROVIDER_IDS) or set(
    PROVIDER_FACTORIES
) != set(SUPPORTED_PROVIDER_IDS):
    raise AssertionError(
        "PROVIDER_DESCRIPTORS, PROVIDER_FACTORIES, and SUPPORTED_PROVIDER_IDS are out of sync: "
        f"descriptors={set(PROVIDER_DESCRIPTORS)!r} factories={set(PROVIDER_FACTORIES)!r} "
        f"ids={set(SUPPORTED_PROVIDER_IDS)!r}"
    )


def _string_attr(settings: Settings, attr_name: str | None, default: str = "") -> str:
    if attr_name is None:
        return default
    value = getattr(settings, attr_name, default)
    return value if isinstance(value, str) else default


def _string_tuple_attr(settings: Settings, attr_name: str | None) -> tuple[str, ...]:
    if attr_name is None:
        return ()
    value = getattr(settings, attr_name, ())
    if not isinstance(value, tuple):
        return ()
    return tuple(part for part in value if isinstance(part, str) and part.strip())


def _int_attr(settings: Settings, attr_name: str | None, default: int = 0) -> int:
    if attr_name is None:
        return default
    value = getattr(settings, attr_name, default)
    return value if isinstance(value, int) else default


def _credential_for(descriptor: ProviderDescriptor, settings: Settings) -> str:
    if descriptor.credential_attr:
        credential = _string_attr(settings, descriptor.credential_attr)
        if credential:
            return credential
        fallbacks = _string_tuple_attr(settings, descriptor.credential_list_attr)
        if fallbacks:
            return fallbacks[0]
    if descriptor.static_credential is not None:
        return descriptor.static_credential
    return ""


def _require_credential(descriptor: ProviderDescriptor, credential: str) -> None:
    if descriptor.credential_env is None:
        return
    if credential and credential.strip():
        return
    message = f"{descriptor.credential_env} is not set. Add it to your .env file."
    if descriptor.credential_url:
        message = f"{message} Get a key at {descriptor.credential_url}"
    raise AuthenticationError(message)


def _credential_fallbacks(
    descriptor: ProviderDescriptor, settings: Settings, primary: str
) -> tuple[str, ...]:
    configured = _string_tuple_attr(settings, descriptor.credential_list_attr)
    keys: list[str] = []
    for key in (primary, *configured):
        stripped = key.strip()
        if stripped and stripped not in keys:
            keys.append(stripped)
    return tuple(keys)


def build_provider_config(
    descriptor: ProviderDescriptor, settings: Settings
) -> ProviderConfig:
    credential = _credential_for(descriptor, settings)
    _require_credential(descriptor, credential)
    base_url = _string_attr(
        settings, descriptor.base_url_attr, descriptor.default_base_url or ""
    )
    proxy = _string_attr(settings, descriptor.proxy_attr)
    api_keys = _credential_fallbacks(descriptor, settings, credential)
    return ProviderConfig(
        api_key=credential,
        api_keys=api_keys if len(api_keys) > 1 else (),
        key_usage_limit=_int_attr(settings, descriptor.key_usage_limit_attr),
        base_url=base_url or descriptor.default_base_url,
        rate_limit=settings.provider_rate_limit,
        rate_window=settings.provider_rate_window,
        max_concurrency=settings.provider_max_concurrency,
        max_retries=settings.provider_max_retries,
        retry_base_delay=settings.provider_retry_base_delay,
        retry_max_delay=settings.provider_retry_max_delay,
        http_read_timeout=settings.http_read_timeout,
        http_write_timeout=settings.http_write_timeout,
        http_connect_timeout=settings.http_connect_timeout,
        enable_thinking=settings.enable_model_thinking,
        proxy=proxy,
        log_raw_sse_events=settings.log_raw_sse_events,
        log_api_error_tracebacks=settings.log_api_error_tracebacks,
    )


def create_provider(provider_id: str, settings: Settings) -> BaseProvider:
    descriptor = PROVIDER_DESCRIPTORS.get(provider_id)
    if descriptor is None:
        supported = "', '".join(PROVIDER_DESCRIPTORS)
        raise UnknownProviderTypeError(
            f"Unknown provider_type: '{provider_id}'. Supported: '{supported}'"
        )

    config = build_provider_config(descriptor, settings)
    factory = PROVIDER_FACTORIES.get(provider_id)
    if factory is None:
        raise AssertionError(f"Unhandled provider descriptor: {provider_id}")
    return factory(config, settings)


class ProviderRegistry:
    """Cache and clean up provider instances by provider id."""

    def __init__(self, providers: MutableMapping[str, BaseProvider] | None = None):
        self._providers = providers if providers is not None else {}

    def is_cached(self, provider_id: str) -> bool:
        """Return whether a provider for this id is already in the cache."""
        return provider_id in self._providers

    def get(self, provider_id: str, settings: Settings) -> BaseProvider:
        if provider_id not in self._providers:
            self._providers[provider_id] = create_provider(provider_id, settings)
        return self._providers[provider_id]

    async def cleanup(self) -> None:
        """Call ``cleanup`` on every cached provider, then clear the cache.

        Attempts all providers even if one fails. A single failure is re-raised
        as-is; multiple failures are wrapped in :exc:`ExceptionGroup`.
        """
        items = list(self._providers.items())
        errors: list[Exception] = []
        try:
            for _pid, provider in items:
                try:
                    await provider.cleanup()
                except Exception as e:
                    errors.append(e)
        finally:
            self._providers.clear()
        if len(errors) == 1:
            raise errors[0]
        if len(errors) > 1:
            msg = "One or more provider cleanups failed"
            raise ExceptionGroup(msg, errors)
