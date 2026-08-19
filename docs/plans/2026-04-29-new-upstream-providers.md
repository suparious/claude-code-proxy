# New Upstream Providers — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

 **Goal:** Add 7 new upstream model providers (FriendliAI, Fireworks AI, vLLM, CLIProxyAPI, Groq, Cerebras, Together AI) to the proxy, split across the two existing transport archetypes: native Anthropic Messages and OpenAI Chat compat.

**Architecture:** Follow the existing two-transport pattern. Anthropic Messages providers extend `AnthropicMessagesTransport` (minimal code — auth header + optional request body customization). OpenAI Chat providers extend `OpenAIChatTransport` (medium code — Anthropic→OpenAI request conversion + reasoning handling). All new providers register through the same 4 touchpoints: `config/provider_catalog.py`, `config/settings.py`, `providers/registry.py`, and `providers/defaults.py`.

**Tech Stack:** Python 3.14, httpx, openai SDK, FastAPI, Pydantic — same stack as existing providers.

---

## Candidate Summary

| # | Provider | Transport | Endpoint | Auth Header | Key Env Var | Effort | Rationale |
|---|----------|-----------|----------|-------------|-------------|--------|-----------|
| 1 | **FriendliAI** | `anthropic_messages` | `https://api.friendli.ai/serverless/v1` | `Authorization: Bearer` | `FRIENDLIAI_API_KEY` | Low | Native Anthropic Messages — essentially a drop-in like DeepSeek. Hosts open models (GLM, MiniMax, DeepSeek) on fast infrastructure. |
| 2 | **Fireworks AI** | `anthropic_messages` | `https://api.fireworks.ai/inference` | `Authorization: Bearer` | `FIREWORKS_API_KEY` | Low | Native Anthropic Messages at `/inference` (separate base from their OpenAI compat `/inference/v1`). Mixture-of-Agents, function calling, reasoning support. |
| 3 | **Groq** | `openai_chat` | `https://api.groq.com/openai/v1` | `Authorization: Bearer` | `GROQ_API_KEY` | Medium | LPU inference — fastest tokens/sec of any provider. OpenAI-compatible chat completions. Good free tier. |
| 4 | **Cerebras** | `openai_chat` | `https://api.cerebras.ai/v1` | `Authorization: Bearer` | `CEREBRAS_API_KEY` | Medium | Wafer-Scale Engine — extreme throughput. OpenAI-compatible. `reasoning_effort` param, `clear_thinking` extra_body field. |
 | 5 | **Together AI** | `openai_chat` | `https://api.together.xyz/v1` | `Authorization: Bearer` | `TOGETHER_API_KEY` | Medium | Widest open model catalog. OpenAI-compatible. Good fallback for models not on other providers. |
 | 6 | **vLLM** | `anthropic_messages` | `http://localhost:8000/v1` | `Authorization: Bearer` (optional) | `VLLM_BASE_URL` | Low | Self-hosted inference engine with native Anthropic Messages endpoint. Local provider like llama.cpp. Serves any GGUF/Safetensors model. |
 | 7 | **CLIProxyAPI** | `anthropic_messages` | `http://localhost:8317/v1` | `x-api-key` | `CLIPROXYAPI_BASE_URL` | Low | Wraps Claude Code OAuth credentials, exposes Anthropic Messages API. Use your Claude subscription as a backend. Local-only provider. |

## How Transport Choice Determines Implementation

```
AnthropicMessagesTransport          OpenAIChatTransport
─────────────────────────          ────────────────────
Auth header override        →      Auth via openai SDK
Optional build_request_body →      Full build_request_body (conversion)
Optional stream transform   →      reasoning_content handling
Optional error format       →      _get_retry_request_body (NIM pattern)
Minimal — ~30 lines         →      Moderate — ~100-250 lines
```

---

## Phase A: Anthropic Messages Providers (Simplest)

### Provider Architecture Recap (for Anthropic Messages)

Every Anthropic Messages provider touches these files:

```
config/provider_catalog.py    ← ProviderDescriptor (transport_type, credential_env, base_url, capabilities)
config/settings.py            ← Settings field (API key, API keys tuple, key_usage_limit)
providers/defaults.py         ← re-export default base URL constant
providers/registry.py         ← ProviderFactory function + PROVIDER_FACTORIES entry
providers/<new_provider>/     ← Subpackage with client.py (+ optional request.py)
```

Minimal provider (c.f. LM Studio — 16 lines):
```python
class NewProvider(AnthropicMessagesTransport):
    def __init__(self, config: ProviderConfig):
        super().__init__(
            config, provider_name="NEWPROV", default_base_url=NEWPROV_DEFAULT_BASE
        )

    def _request_headers(self) -> dict[str, str]:
        return {
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
```

### A1: FriendliAI (`friendliai`)

**Transport:** `anthropic_messages`
**Auth:** `Authorization: Bearer flp_<key>`
**Serverless endpoint:** `https://api.friendli.ai/serverless/v1` → POST `/messages`
**Dedicated endpoint:** `https://api.friendli.ai/dedicated/v1` → POST `/messages`
**Note:** Uses custom `anthropic-version` header? FriendliAI docs suggest standard Anthropic messages format with no version header needed. Check live API for exact requirements.

**Complexity:** ~30 lines — essentially identical to DeepSeek provider (auth header with `Authorization: Bearer`, no `x-api-key`).

#### Task A1.1: Add provider catalog entry

**Files:**
- Modify: `config/provider_catalog.py`
- Modify: `providers/defaults.py`

```python
# config/provider_catalog.py — add constant
FRIENDLIAI_DEFAULT_BASE = "https://api.friendli.ai/serverless/v1"

# Add to PROVIDER_CATALOG dict
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

# providers/defaults.py — add re-export
from config.provider_catalog import FRIENDLIAI_DEFAULT_BASE
```

#### Task A1.2: Add settings fields

**File:** `config/settings.py`

```python
# FriendliAI Config
friendliai_api_key: str = Field(default="", validation_alias="FRIENDLIAI_API_KEY")
friendliai_api_keys: Annotated[tuple[str, ...], NoDecode] = Field(
    default=(), validation_alias="FRIENDLIAI_API_KEYS"
)
friendliai_key_usage_limit: int = Field(
    default=0, validation_alias="FRIENDLIAI_KEY_USAGE_LIMIT"
)

# Per-provider proxy
friendliai_proxy: str = Field(default="", validation_alias="FRIENDLIAI_PROXY")


# Add to field_validator for api_keys tuple
@field_validator("friendliai_api_keys", mode="before")
@classmethod
def parse_api_key_tuple(cls, v: Any) -> Any: ...


# Add to field_validator for key_usage_limit
@field_validator("friendliai_key_usage_limit")
@classmethod
def validate_key_usage_limit(cls, v: int) -> int: ...
```

#### Task A1.3: Create provider subpackage

**Files:**
- Create: `providers/friendliai/__init__.py`
- Create: `providers/friendliai/client.py`

```python
# providers/friendliai/__init__.py
from .client import FriendliAIProvider

__all__ = ("FriendliAIProvider",)

# providers/friendliai/client.py
"""FriendliAI provider implementation (native Anthropic Messages)."""
from providers.anthropic_messages import AnthropicMessagesTransport
from providers.base import ProviderConfig
from providers.defaults import FRIENDLIAI_DEFAULT_BASE


class FriendliAIProvider(AnthropicMessagesTransport):
    """FriendliAI using native Anthropic Messages API (serverless/dedicated)."""

    def __init__(self, config: ProviderConfig):
        super().__init__(
            config,
            provider_name="FRIENDLIAI",
            default_base_url=FRIENDLIAI_DEFAULT_BASE,
        )

    def _request_headers(self) -> dict[str, str]:
        return {
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
```

#### Task A1.4: Register factory

**File:** `providers/registry.py`

```python
def _create_friendliai(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.friendliai import FriendliAIProvider
    return FriendliAIProvider(config)

# Add to PROVIDER_FACTORIES dict
"friendliai": _create_friendliai,
```

#### Task A1.5: Write unit tests

**Files:**
- Create: `tests/providers/test_friendliai.py`

Test coverage:
- Provider construction with default config
- Auth header format (`Authorization: Bearer <key>`)
- Base URL resolution (config override vs default)
- Key pool integration (API keys fallback)
- Stream response shape (mock httpx response)
- Error mapping (429 → RateLimitError, 401 → AuthenticationError)
- Integration with `build_provider_config`

**Verification:** `uv run pytest tests/providers/test_friendliai.py -v`

---

### A2: Fireworks AI (`fireworks`)

**Transport:** `anthropic_messages` (note: Fireworks has *two* APIs — Anthropic Messages at `/inference` and OpenAI compat at `/inference/v1`; we use the Anthropic Messages one)

**Auth:** `Authorization: Bearer fw_<key>`
**Endpoint:** `https://api.fireworks.ai/inference` → POST `/v1/messages`
**Note:** The base URL does NOT include `/v1` — the `AnthropicMessagesTransport` base class posts to `/messages` (not `/v1/messages`). Verify: Fireworks Anthropic Messages docs show POST to `https://api.fireworks.ai/inference/v1/messages`. The `/v1` *is* part of the base URL here.

**Key observation:** Fireworks' Anthropic endpoint is at `https://api.fireworks.ai/inference/v1/messages` while their OpenAI endpoint is at `https://api.fireworks.ai/inference/v1/chat/completions`. So the base URL for Anthropic Messages should be `https://api.fireworks.ai/inference/v1`.

**Complexity:** ~40 lines. Likely needs thinking/reasoning block filtering similar to OpenRouter since Fireworks models may emit thinking tokens differently. Start minimal, add filtering if smoke tests show issues.

#### Task A2.1: Add provider catalog entry

**Files:** `config/provider_catalog.py`, `providers/defaults.py`

```python
FIREWORKS_DEFAULT_BASE = "https://api.fireworks.ai/inference/v1"

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
```

#### Task A2.2: Add settings fields

**File:** `config/settings.py`

```python
# Fireworks AI Config
fireworks_api_key: str = Field(default="", validation_alias="FIREWORKS_API_KEY")
fireworks_api_keys: Annotated[tuple[str, ...], NoDecode] = Field(
    default=(), validation_alias="FIREWORKS_API_KEYS"
)
fireworks_key_usage_limit: int = Field(
    default=0, validation_alias="FIREWORKS_KEY_USAGE_LIMIT"
)
fireworks_proxy: str = Field(default="", validation_alias="FIREWORKS_PROXY")
```

#### Task A2.3: Create provider subpackage

**Files:** `providers/fireworks/__init__.py`, `providers/fireworks/client.py`

Same pattern as FriendliAI — minimal AnthropicMessagesTransport subclass with `Authorization: Bearer` header.

#### Task A2.4: Register factory

**File:** `providers/registry.py`

```python
def _create_fireworks(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.fireworks import FireworksProvider

    return FireworksProvider(config)
```

#### Task A2.5: Write unit tests

**File:** `tests/providers/test_fireworks.py` — same coverage as FriendliAI tests.

---

### A3: vLLM (`vllm`)

**Transport:** `anthropic_messages`
**Auth:** `Authorization: Bearer <key>` (optional — no auth by default, set `VLLM_API_KEY` env var on the server to require it)
**Endpoint:** `http://localhost:8000/v1` → POST `/messages`
**Context:** vLLM is a high-throughput inference engine that serves open-source LLMs. Since v0.8+, it exposes a native Anthropic Messages API at `/v1/messages`. It auto-discovers this endpoint — the proxy just sends Anthropic-format requests through.
**Note:** vLLM's Anthropic endpoint currently has a known issue with reasoning/thinking tokens (vllm#29915). Thinking may not work reliably. Mark `capabilities` conservatively (no `"thinking"` until verified).
**Auth behavior:** By default vLLM requires NO auth. If the user has set `VLLM_API_KEY`, requests need `Authorization: Bearer <key>`. We use a static credential like llama.cpp, defaulting to `"vllm"`.

**Complexity:** ~30 lines — identical to LM Studio / llama.cpp pattern.

#### Task A3.1: Add provider catalog entry

**Files:** `config/provider_catalog.py`, `providers/defaults.py`

```python
# config/provider_catalog.py
VLLM_DEFAULT_BASE = "http://localhost:8000/v1"

"vllm": ProviderDescriptor(
    provider_id="vllm",
    transport_type="anthropic_messages",
    static_credential="vllm",
    default_base_url=VLLM_DEFAULT_BASE,
    base_url_attr="vllm_base_url",
    proxy_attr="vllm_proxy",
    capabilities=("chat", "streaming", "tools", "native_anthropic", "local"),
),
```

#### Task A3.2: Add settings fields

**File:** `config/settings.py`

```python
# vLLM Config
vllm_base_url: str = Field(
    default="http://localhost:8000/v1",
    validation_alias="VLLM_BASE_URL",
)
vllm_proxy: str = Field(default="", validation_alias="VLLM_PROXY")
```

#### Task A3.3: Create provider subpackage

**Files:** `providers/vllm/__init__.py`, `providers/vllm/client.py`

```python
# providers/vllm/__init__.py
from .client import VllmProvider

__all__ = ("VllmProvider",)

# providers/vllm/client.py
"""vLLM provider implementation (native Anthropic Messages)."""
from providers.anthropic_messages import AnthropicMessagesTransport
from providers.base import ProviderConfig
from providers.defaults import VLLM_DEFAULT_BASE


class VllmProvider(AnthropicMessagesTransport):
    """vLLM using native Anthropic Messages API endpoint."""

    def __init__(self, config: ProviderConfig):
        super().__init__(
            config,
            provider_name="VLLM",
            default_base_url=VLLM_DEFAULT_BASE,
        )

    def _request_headers(self) -> dict[str, str]:
        return {
            "Accept": "text/event-stream",
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
```

#### Task A3.4: Register factory

**File:** `providers/registry.py`

```python
def _create_vllm(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.vllm import VllmProvider
    return VllmProvider(config)

# Add to PROVIDER_FACTORIES
"vllm": _create_vllm,
```

#### Task A3.5: Write unit tests

**File:** `tests/providers/test_vllm.py` — standard Anthropic Messages provider test suite.

---

### A4: CLIProxyAPI (`cliproxyapi`)

**Transport:** `anthropic_messages` (note: CLIProxyAPI supports BOTH OpenAI `/v1/chat/completions` AND Anthropic `/v1/messages` — PR #2748 added first-class `anthropic-compatibility` config. We use Anthropic Messages to avoid double conversion.)
**Auth:** `x-api-key: dummy` (when `auth.providers: []` in CLIProxyAPI config, no real validation occurs)
**Endpoint:** `http://localhost:8317/v1` → POST `/messages`
**Context:** CLIProxyAPI wraps Claude Code's OAuth credentials and exposes a standard API. It lets you use a Claude Pro/Max subscription as an API backend. Models are Claude model names (e.g., `claude-sonnet-4-5-20250929`).
**Important nuance:** This is a LOCAL provider that depends on Claude Code being installed and logged in. The proxy is routing Claude Code → CLIProxyAPI → Claude Code CLI (which then makes real Anthropic API calls). It's circular but useful for routing specific model tiers through a subscription instead of API credits.
**Auth header:** Uses `x-api-key` (DeepSeek-style), NOT `Authorization: Bearer`. Override `_request_headers()` to use `x-api-key`.

**Complexity:** ~40 lines — AnthropicMessagesTransport with custom auth header.

#### Task A4.1: Add provider catalog entry

**Files:** `config/provider_catalog.py`, `providers/defaults.py`

```python
# config/provider_catalog.py
CLIPROXYAPI_DEFAULT_BASE = "http://localhost:8317/v1"

"cliproxyapi": ProviderDescriptor(
    provider_id="cliproxyapi",
    transport_type="anthropic_messages",
    static_credential="dummy",
    default_base_url=CLIPROXYAPI_DEFAULT_BASE,
    base_url_attr="cliproxyapi_base_url",
    proxy_attr="cliproxyapi_proxy",
    capabilities=("chat", "streaming", "tools", "thinking", "native_anthropic", "local"),
),
```

#### Task A4.2: Add settings fields

**File:** `config/settings.py`

```python
# CLIProxyAPI Config
cliproxyapi_base_url: str = Field(
    default="http://localhost:8317/v1",
    validation_alias="CLIPROXYAPI_BASE_URL",
)
cliproxyapi_proxy: str = Field(default="", validation_alias="CLIPROXYAPI_PROXY")
```

#### Task A4.3: Create provider subpackage

**Files:** `providers/cliproxyapi/__init__.py`, `providers/cliproxyapi/client.py`

```python
# providers/cliproxyapi/__init__.py
from .client import CLIProxyAPIProvider

__all__ = ("CLIProxyAPIProvider",)

# providers/cliproxyapi/client.py
"""CLIProxyAPI provider implementation (Anthropic Messages via Claude Code OAuth)."""
from providers.anthropic_messages import AnthropicMessagesTransport
from providers.base import ProviderConfig
from providers.defaults import CLIPROXYAPI_DEFAULT_BASE


class CLIProxyAPIProvider(AnthropicMessagesTransport):
    """CLIProxyAPI wrapping Claude Code OAuth as an Anthropic Messages endpoint."""

    def __init__(self, config: ProviderConfig):
        super().__init__(
            config,
            provider_name="CLIPROXYAPI",
            default_base_url=CLIPROXYAPI_DEFAULT_BASE,
        )

    def _request_headers(self) -> dict[str, str]:
        return {
            "Accept": "text/event-stream",
            "Content-Type": "application/json",
            "x-api-key": self._api_key,
        }
```

#### Task A4.4: Register factory

**File:** `providers/registry.py`

```python
def _create_cliproxyapi(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.cliproxyapi import CLIProxyAPIProvider
    return CLIProxyAPIProvider(config)

# Add to PROVIDER_FACTORIES
"cliproxyapi": _create_cliproxyapi,
```

#### Task A4.5: Write unit tests

**File:** `tests/providers/test_cliproxyapi.py` — verify `x-api-key` header (not Bearer), static credential, base URL resolution.

---

## Phase B: OpenAI Chat Providers (Moderate Effort — 3 candidates)

### Provider Architecture Recap (for OpenAI Chat)

Every OpenAI Chat provider touches the same 4 config/registry files, plus needs a request builder:

```
providers/<new_provider>/client.py     ← OpenAIChatTransport subclass
providers/<new_provider>/request.py    ← _build_request_body (Anthropic→OpenAI)
```

Request builder pattern (c.f. NvidiaNimProvider):
```python
class NewProvider(OpenAIChatTransport):
    def __init__(self, config, *, provider_settings=None):
        super().__init__(
            config,
            provider_name="NEWPROV",
            base_url=NEWPROV_BASE,
            api_key=config.api_key,
        )
        self._settings = provider_settings

    def _build_request_body(self, request, thinking_enabled=None) -> dict:
        return build_request_body(request, self._settings, thinking_enabled=...)

    def _get_retry_request_body(self, error, body) -> dict | None:
        # Optional: downgrade on unsupported params (NIM pattern)
        return None
```

### B1: Groq (`groq`)

**Transport:** `openai_chat`
**Endpoint:** `https://api.groq.com/openai/v1`
**Auth:** `Authorization: Bearer gsk_<key>`
**Key env:** `GROQ_API_KEY`
**Available models:** `llama-4-maverick-17b-128e`, `llama-4-scout-17b-16e`, `deepseek-r1-distill-llama-70b`, `qwen-2.5-coder-32b`, `gemma2-9b-it`, etc.
**Thinking:** Groq doesn't have a native `reasoning_content` field. Reasoning models emit `reasoning` in the content itself (like `<｜end▁of▁thinking｜>` tags). The existing `ThinkTagParser` in `OpenAIChatTransport._stream_response_impl` handles this already.
**Retry logic:** Groq's API may reject unknown parameters. If they reject `reasoning_effort` or `chat_template_kwargs`, implement `_get_retry_request_body` to strip them (NIM pattern).

**Complexity:** ~150 lines. Request builder similar to NIM but simpler (no NIM-specific chat template params).

#### Task B1.1: Add provider catalog entry

**Files:** `config/provider_catalog.py`, `providers/defaults.py`

```python
GROQ_DEFAULT_BASE = "https://api.groq.com/openai/v1"

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
```

#### Task B1.2: Add settings fields

**File:** `config/settings.py`

```python
# Groq Config
groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")
groq_api_keys: Annotated[tuple[str, ...], NoDecode] = Field(
    default=(), validation_alias="GROQ_API_KEYS"
)
groq_key_usage_limit: int = Field(default=0, validation_alias="GROQ_KEY_USAGE_LIMIT")
groq_proxy: str = Field(default="", validation_alias="GROQ_PROXY")
```

#### Task B1.3: Create request builder

**File:** `providers/groq/request.py`

The request builder converts Anthropic Messages format → OpenAI Chat Completions format. Key work:
- Map messages (system role → system param, user/assistant → messages array)
- Extract tools → OpenAI tool format (with `function` wrapper)
- Set `max_completion_tokens` (Groq uses OpenAI naming, not `max_tokens`)
- Map stop sequences
- Handle streaming flag
- Strip Anthropic-specific fields (thinking, tool_choice anthropic format, etc.)

Core conversion logic:

```python
def build_request_body(request: Any, *, thinking_enabled: bool) -> dict:
    """Build OpenAI chat completions body from Anthropic Messages request."""
    from core.anthropic.native_messages_request import dump_raw_messages_request
    from providers.exceptions import InvalidRequestError

    data = dump_raw_messages_request(request)

    # Validate unsupported types
    _validate_no_unsupported_blocks(data)

    body: dict[str, Any] = {
        "model": data.get("model", ""),
        "messages": _convert_messages(data),
        "stream": True,
    }

    # System prompt as system message (not top-level param — Groq accepts either)
    system = data.get("system")
    if system:
        body["messages"].insert(
            0, {"role": "system", "content": _flatten_system(system)}
        )

    # Max tokens
    if max_tokens := data.get("max_tokens"):
        body["max_completion_tokens"] = max_tokens

    # Tools
    if tools := data.get("tools"):
        body["tools"] = _convert_tools(tools)
        if tool_choice := data.get("tool_choice"):
            body["tool_choice"] = _convert_tool_choice(tool_choice)

    # Stop sequences
    if stops := data.get("stop_sequences"):
        if len(stops) == 1:
            body["stop"] = stops[0]
        else:
            body["stop"] = stops

    # Temperature / top_p
    if "temperature" in data:
        body["temperature"] = data["temperature"]
    if "top_p" in data:
        body["top_p"] = data["top_p"]

    return body
```

#### Task B1.4: Create provider client

**File:** `providers/groq/client.py`

```python
"""Groq provider implementation (OpenAI-compatible chat completions)."""

from providers.base import ProviderConfig
from providers.defaults import GROQ_DEFAULT_BASE
from providers.openai_compat import OpenAIChatTransport

from .request import build_request_body


class GroqProvider(OpenAIChatTransport):
    """Groq using OpenAI-compatible /chat/completions endpoint."""

    def __init__(self, config: ProviderConfig):
        super().__init__(
            config,
            provider_name="GROQ",
            base_url=config.base_url or GROQ_DEFAULT_BASE,
            api_key=config.api_key,
        )

    def _build_request_body(self, request, thinking_enabled=None):
        return build_request_body(
            request,
            thinking_enabled=self._is_thinking_enabled(request, thinking_enabled),
        )
```

#### Task B1.5: Register factory

**File:** `providers/registry.py`

```python
def _create_groq(config: ProviderConfig, _settings: Settings) -> BaseProvider:
    from providers.groq import GroqProvider

    return GroqProvider(config)
```

#### Task B1.6: Write unit tests

**File:** `tests/providers/test_groq.py`

Cover:
- Request body conversion: Anthropic → OpenAI chat format
- System prompt flattening (string vs array)
- Tool conversion (Anthropic tool format → OpenAI function format)
- max_tokens → max_completion_tokens mapping
- Message role mapping (user/assistant preserved)
- Streaming flag presence
- Provider construction and auth header

**Verification:** `uv run pytest tests/providers/test_groq.py -v`

---

### B2: Cerebras (`cerebras`)

**Transport:** `openai_chat`
**Endpoint:** `https://api.cerebras.ai/v1`
**Auth:** `Authorization: Bearer csk_<key>`
**Key env:** `CEREBRAS_API_KEY`
**Available models:** `llama-4-maverick-17b`, `llama-4-scout-17b`, `zai-glm-4.7`, `deepseek-r1`, `deepseek-v3`, `qwen-2.5`, `mistral-large`, etc.
**Special behavior:** 
- `reasoning_effort` parameter (OpenAI-style) controls thinking budget
- `clear_thinking` extra_body field for non-standard thinking control
- May return `reasoning_content` in deltas (already handled by base `OpenAIChatTransport`)
- Uses `max_completion_tokens` not `max_tokens`

**Complexity:** ~200 lines. Near-identical to Groq request builder but with `reasoning_effort` passthrough and `clear_thinking` extra_body support.

#### Task B2.1-B2.5: Follow Groq pattern

Same 5-touchpoint pattern: catalog entry + settings + request.py + client.py + registry + tests.

Unique Cerebras considerations in request builder:
```python
# Pass through reasoning_effort if the model supports it
if thinking_enabled:
    body["reasoning_effort"] = (
        "medium"  # or extract from request thinking.budget_tokens
    )

# Non-standard params go in extra_body
extra_body = {}
if not thinking_enabled:
    extra_body["clear_thinking"] = True
if extra_body:
    body["extra_body"] = extra_body
```

---

### B3: Together AI (`together`)

**Transport:** `openai_chat`
**Endpoint:** `https://api.together.xyz/v1`
**Auth:** `Authorization: Bearer <key>`
**Key env:** `TOGETHER_API_KEY`
**Available models:** Extensive — Llama 4, DeepSeek V3/R1, Qwen 2.5, Mixtral, Gemma, etc.

**Complexity:** ~180 lines. Similar to Groq request builder. Together AI's API is standard OpenAI-compatible with no unusual parameters. May need to handle their model naming convention (`meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8`).

#### Task B3.1-B3.5: Follow Groq pattern

Same structure. Request builder is nearly identical to Groq's — Together AI is the most vanilla OpenAI-compatible API of the three.

---

## Phase C: Integration & Verification

### C1: Smoke tests

After each provider is implemented, add a live smoke test:

**File:** `smoke/prereq/test_local_provider_endpoints_prereq_live.py`

```python
@pytest.mark.live
@pytest.mark.parametrize(
    "provider_info",
    [
        ("friendliai", "friendliai/meta-llama/Llama-4-Maverick-17B-128E-Instruct"),
        ("fireworks", "fireworks/accounts/fireworks/models/llama-v4-maverick-17b"),
        ("groq", "groq/llama-4-maverick-17b-128e"),
        ("cerebras", "cerebras/llama-4-maverick-17b"),
        ("together", "together/meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"),
        ("vllm", "vllm/meta-llama/Llama-4-Maverick-17B-128E-Instruct"),
        ("cliproxyapi", "cliproxyapi/claude-sonnet-4-5-20250929"),
    ],
)
def test_provider_health_check(provider_info, settings):
    provider_id, model_ref = provider_info
    # Skip if API key not configured
    # Create provider, send minimal request, verify 200 + valid SSE
```

### C2: Documentation

Update `README.md` provider table:

```markdown
| FriendliAI | `friendliai/...` | Anthropic Messages | `FRIENDLIAI_API_KEY` | `https://api.friendli.ai/serverless/v1` |
| Fireworks AI | `fireworks/...` | Anthropic Messages | `FIREWORKS_API_KEY` | `https://api.fireworks.ai/inference/v1` |
| Groq | `groq/...` | OpenAI chat translation | `GROQ_API_KEY` | `https://api.groq.com/openai/v1` |
| Cerebras | `cerebras/...` | OpenAI chat translation | `CEREBRAS_API_KEY` | `https://api.cerebras.ai/v1` |
| Together AI | `together/...` | OpenAI chat translation | `TOGETHER_API_KEY` | `https://api.together.xyz/v1` |
| vLLM | `vllm/...` | Anthropic Messages | none (local, optional `VLLM_API_KEY`) | `http://localhost:8000/v1` |
| CLIProxyAPI | `cliproxyapi/...` | Anthropic Messages | none (local, OAuth-based) | `http://localhost:8317/v1` |
```

### C3: Full CI checks

```bash
uv run ruff format
uv run ruff check
uv run ty check
uv run pytest
```

---

## Implementation Order (Recommended)

```
Phase A (Anthropic Messages — lower risk, ~1-2h each):
  1. FriendliAI    ← start here: simplest hosted case, validates pattern
  2. Fireworks AI  ← slightly more complex (base URL nuances)
  3. vLLM          ← local provider, identical to llama.cpp/LM Studio pattern
  4. CLIProxyAPI   ← local provider, unique auth header (x-api-key)

Phase B (OpenAI Chat — medium risk, ~3-5h each):
  5. Groq          ← start here: well-documented, validates OpenAI builder
  6. Cerebras      ← shares ~90% of Groq builder code
  7. Together AI   ← vanilla OpenAI compat, quick after Groq

Phase C (Integration):
  8. Smoke tests   ← run after all providers done
  9. Documentation ← update README table + .env.example
```

## Total File Touchpoints Per Provider

| Touchpoint | Anthropic Messages | OpenAI Chat |
|-----------|-------------------|-------------|
| `config/provider_catalog.py` | +1 descriptor, +1 constant | same |
| `config/settings.py` | API key, keys tuple, usage limit, proxy (4 fields) | same |
| `providers/defaults.py` | +1 re-export | same |
| `providers/registry.py` | +1 factory, +1 dict entry | same |
| New `providers/<id>/__init__.py` | 3 lines | 3 lines |
| New `providers/<id>/client.py` | ~25 lines | ~40 lines |
| New `providers/<id>/request.py` | NOT needed | ~120-180 lines |
| `tests/providers/test_<id>.py` | ~80 lines | ~150 lines |
| **Total new/changed files** | **8** | **9** |

## Risks & Unknowns

1. **FriendliAI `anthropic-version` header** — May need `"anthropic-version": "2023-06-01"` like OpenRouter. Check live API response.
2. **Fireworks base URL** — Confirm the Anthropic Messages endpoint is exactly `https://api.fireworks.ai/inference/v1/messages`. Their docs show the OpenAI compat at `/inference/v1` but Anthropic Messages may be at `/inference` without `/v1`.
3. **Groq thinking/reasoning** — Groq doesn't return `reasoning_content` in deltas. Reasoning models (DeepSeek R1 distill) emit think tags in `content`. The existing `ThinkTagParser` handles this but verify during smoke.
4. **Cerebras `clear_thinking`** — Non-standard param must go in `extra_body`. The base `OpenAIChatTransport._create_stream` passes the entire body dict to `openai.chat.completions.create(**body)`. Extra kwargs beyond OpenAI's schema may cause errors. Use `extra_body` dict nesting.
5. **Together AI model names** — Long paths like `meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8`. The model router already handles `/` in model names (parses `provider/model/name` by splitting on first `/` then second `/`). Verify with `Settings.validate_model_format`.
6. **vLLM reasoning tokens** — vLLM's Anthropic endpoint may not return reasoning/thinking tokens reliably (vllm#29915). Set capabilities without `"thinking"` initially; add after smoke verification.
7. **CLIProxyAPI `x-api-key` header** — Different auth header from all other providers (`x-api-key` vs `Authorization: Bearer`). The `AnthropicMessagesTransport._send_stream_request` doesn't use auth headers directly — it uses `_request_headers()` which we override. No transport changes needed.
8. **CLIProxyAPI model names** — Uses Claude model names (e.g., `claude-sonnet-4-5-20250929`). The user's `.env` MODEL value would look like `cliproxyapi/claude-sonnet-4-5-20250929`. Works fine with existing model routing since Claude model names don't contain `/`.
