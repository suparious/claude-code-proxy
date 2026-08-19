<div align="center">

# Claude Code Proxy

Use Claude Code CLI, VS Code, or JetBrains ACP through your own Anthropic-compatible proxy.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)
[![Python 3.14](https://img.shields.io/badge/python-3.14-3776ab.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json&style=for-the-badge)](https://github.com/astral-sh/uv)
[![Tested with Pytest](https://img.shields.io/badge/testing-Pytest-00c0ff.svg?style=for-the-badge)](https://github.com/suparious/claude-code-proxy/actions/workflows/tests.yml)
[![Type checking: Ty](https://img.shields.io/badge/type%20checking-ty-ffcc00.svg?style=for-the-badge)](https://pypi.org/project/ty/)
[![Code style: Ruff](https://img.shields.io/badge/code%20formatting-ruff-f5a623.svg?style=for-the-badge)](https://github.com/astral-sh/ruff)
[![Logging: Loguru](https://img.shields.io/badge/logging-loguru-4ecdc4.svg?style=for-the-badge)](https://github.com/Delgan/loguru)

Claude Code Proxy routes Anthropic Messages API traffic from Claude Code to hosted and local upstream providers. It keeps Claude Code's client-side protocol stable while letting you choose NVIDIA NIM, OpenRouter, DeepSeek, LM Studio, llama.cpp, Ollama, FriendliAI, Fireworks AI, vLLM, CLIProxyAPI, Groq, Cerebras, Together AI, Kimi, or a SAP Hyperspace (HAI) relay.

[Quick Start](#quick-start) · [Providers](#choose-a-provider) · [Clients](#connect-claude-code) · [Troubleshooting](#troubleshooting) · [Development](#development)

</div>

<div align="center">
  <img src="pic.png" alt="Claude Code Proxy in action" width="700">
</div>

## What You Get

- Drop-in proxy for Claude Code's Anthropic API calls.
- Fifteen provider backends: NVIDIA NIM, OpenRouter, DeepSeek, LM Studio, llama.cpp, Ollama, FriendliAI, Fireworks AI, vLLM, CLIProxyAPI, Groq, Cerebras, Together AI, Kimi, and SAP Hyperspace (HAI).
- Per-model routing: send Opus, Sonnet, Haiku, and fallback traffic to different providers.
- Streaming, tool use, reasoning/thinking block handling, and local request optimizations.

## Quick Start

### 1. Install Requirements

Install [Claude Code](https://github.com/anthropics/claude-code), then install `uv` and Python 3.14.

macOS/Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv self update
uv python install 3.14
```

Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
uv self update
uv python install 3.14
```

### 2. Clone And Configure

```bash
git clone https://github.com/suparious/claude-code-proxy.git
cd claude-code-proxy
cp .env.example .env
```

PowerShell uses:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and choose one provider. For the default NVIDIA NIM path:

```dotenv
NVIDIA_NIM_API_KEY="nvapi-your-key"
MODEL="nvidia_nim/z-ai/glm4.7"
ANTHROPIC_AUTH_TOKEN="freecc"
```

Use any local secret for `ANTHROPIC_AUTH_TOKEN`; Claude Code will send the same value back to this proxy. Leave it empty only for local/private testing.

### 3. Start The Proxy

From source (reads `.env` for `HOST` and `PORT`):

```bash
uv run python server.py
```

If you need to override host/port on the command line:

```bash
uv run uvicorn server:app --host 127.0.0.1 --port 8082
```

Package install alternative:

```bash
uv tool install git+https://github.com/suparious/claude-code-proxy.git
ccp-init
claude-code-proxy
```

`ccp-init` creates `~/.config/claude-code-proxy/.env` from the bundled template. The legacy `fcc-init` and `free-claude-code` script names are still installed as compatibility aliases.

### 4. Run Claude Code

Point `ANTHROPIC_BASE_URL` at the proxy root. Do not append `/v1`.

PowerShell:

```powershell
$env:ANTHROPIC_AUTH_TOKEN="freecc"; $env:ANTHROPIC_BASE_URL="http://localhost:8082"; claude
```

Bash:

```bash
ANTHROPIC_AUTH_TOKEN="freecc" ANTHROPIC_BASE_URL="http://localhost:8082" claude
```

## Choose A Provider

Model values use this format:

```text
provider_id/model/name
```

`MODEL` is the fallback. `MODEL_OPUS`, `MODEL_SONNET`, and `MODEL_HAIKU` override routing for requests that Claude Code sends for those tiers.

| Provider | Prefix | Transport | Key | Default base URL |
| --- | --- | --- | --- | --- |
| NVIDIA NIM | `nvidia_nim/...` | OpenAI chat translation | `NVIDIA_NIM_API_KEY` | `https://integrate.api.nvidia.com/v1` |
| OpenRouter | `open_router/...` | Anthropic Messages | `OPENROUTER_API_KEY` | `https://openrouter.ai/api/v1` |
| DeepSeek | `deepseek/...` | Anthropic Messages | `DEEPSEEK_API_KEY` | `https://api.deepseek.com/anthropic` |
| LM Studio | `lmstudio/...` | Anthropic Messages | none | `http://localhost:1234/v1` |
| llama.cpp | `llamacpp/...` | Anthropic Messages | none | `http://localhost:8080/v1` |
| Ollama | `ollama/...` | Anthropic Messages | none | `http://localhost:11434` |
| FriendliAI | `friendliai/...` | Anthropic Messages | `FRIENDLIAI_API_KEY` | `https://api.friendli.ai/serverless/v1` |
| Fireworks AI | `fireworks/...` | Anthropic Messages | `FIREWORKS_API_KEY` | `https://api.fireworks.ai/inference/v1` |
| vLLM | `vllm/...` | Anthropic Messages | none (local) | `http://localhost:8000/v1` |
| CLIProxyAPI | `cliproxyapi/...` | Anthropic Messages | none (local, OAuth) | `http://localhost:8317/v1` |
| Groq | `groq/...` | OpenAI chat translation | `GROQ_API_KEY` | `https://api.groq.com/openai/v1` |
| Cerebras | `cerebras/...` | OpenAI chat translation | `CEREBRAS_API_KEY` | `https://api.cerebras.ai/v1` |
| Together AI | `together/...` | OpenAI chat translation | `TOGETHER_API_KEY` | `https://api.together.xyz/v1` |
| Kimi / Moonshot | `kimi/...` | OpenAI chat translation | `KIMI_API_KEY` | `https://api.moonshot.ai/v1` |
| SAP Hyperspace (HAI) | `hyperspace/...` | Anthropic Messages | `HYPERSPACE_API_KEY` | `http://localhost:6655/anthropic/v1` |

<details>
<summary><b>NVIDIA NIM</b></summary>

Get a key at [build.nvidia.com/settings/api-keys](https://build.nvidia.com/settings/api-keys).

```dotenv
NVIDIA_NIM_API_KEY="nvapi-your-key"
MODEL="nvidia_nim/z-ai/glm4.7"
```

Popular examples:

- `nvidia_nim/z-ai/glm4.7`
- `nvidia_nim/z-ai/glm5`
- `nvidia_nim/moonshotai/kimi-k2.5`
- `nvidia_nim/minimaxai/minimax-m2.5`

Browse current models at [build.nvidia.com](https://build.nvidia.com/explore/discover).

</details>

<details>
<summary><b>OpenRouter</b></summary>

Get a key at [openrouter.ai/keys](https://openrouter.ai/keys).

```dotenv
OPENROUTER_API_KEY="sk-or-your-key"
MODEL="open_router/stepfun/step-3.5-flash:free"
```

Browse [all models](https://openrouter.ai/models) or [free models](https://openrouter.ai/collections/free-models).

</details>

<details>
<summary><b>DeepSeek</b></summary>

Get a key at [platform.deepseek.com/api_keys](https://platform.deepseek.com/api_keys).

```dotenv
DEEPSEEK_API_KEY="your-deepseek-key"
MODEL="deepseek/deepseek-chat"
```

This provider uses DeepSeek's Anthropic-compatible endpoint, not the OpenAI chat-completions endpoint.

</details>

<details>
<summary><b>LM Studio</b></summary>

Start LM Studio's local server, load a model, then configure:

```dotenv
LM_STUDIO_BASE_URL="http://localhost:1234/v1"
MODEL="lmstudio/your-loaded-model"
```

Use the model identifier shown by LM Studio. Prefer models with tool-use support for Claude Code workflows.

</details>

<details>
<summary><b>llama.cpp</b></summary>

Start `llama-server` with an Anthropic-compatible `/v1/messages` endpoint and enough context for Claude Code requests.

```dotenv
LLAMACPP_BASE_URL="http://localhost:8080/v1"
MODEL="llamacpp/local-model"
```

For local coding models, context size matters. If llama.cpp returns HTTP 400 for normal Claude Code requests, increase `--ctx-size` and verify the model/server build supports the requested features.

</details>

<details>
<summary><b>Ollama</b></summary>

Run Ollama and pull a model:

```bash
ollama pull llama3.1
ollama serve
```

Then configure the proxy. `OLLAMA_BASE_URL` is the Ollama server root; do not append `/v1`.

```dotenv
OLLAMA_BASE_URL="http://localhost:11434"
MODEL="ollama/llama3.1"
```

Use the same tag shown by `ollama list`, for example `ollama/llama3.1:8b`.

</details>

<details>
<summary><b>FriendliAI</b></summary>

Get a key at [friendli.ai](https://friendli.ai).

```dotenv
FRIENDLIAI_API_KEY="***"
MODEL="friendliai/meta-llama/Llama-4-Maverick-17B-128E-Instruct"
```

Popular models:

- `friendliai/meta-llama/Llama-4-Maverick-17B-128E-Instruct`
- `friendliai/z-ai/glm-4.7`
- `friendliai/deepseek-ai/DeepSeek-V3`

</details>

<details>
<summary><b>Fireworks AI</b></summary>

Get a key at [fireworks.ai/account/api-keys](https://fireworks.ai/account/api-keys).

```dotenv
FIREWORKS_API_KEY="***"
MODEL="fireworks/accounts/fireworks/models/llama-v4-maverick-17b"
```

Popular models:

- `fireworks/accounts/fireworks/models/llama-v4-maverick-17b`
- `fireworks/accounts/fireworks/models/deepseek-v3`

Fireworks exposes an Anthropic Messages endpoint at `/inference/v1` (separate from their OpenAI-compatible endpoint). Function calling and reasoning are supported on compatible models.

</details>

<details>
<summary><b>vLLM</b></summary>

Start a vLLM server with a model, then configure:

```dotenv
VLLM_BASE_URL="http://localhost:8000/v1"
MODEL="vllm/meta-llama/Llama-4-Maverick-17B-128E-Instruct"
```

vLLM exposes a native Anthropic Messages endpoint at `/v1/messages` (since v0.8+). The proxy treats vLLM as a local provider and does not require an API key by default.

Prefer models with tool-use support for Claude Code workflows.

</details>

<details>
<summary><b>CLIProxyAPI</b></summary>

Install [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI), authenticate with Claude Code, then configure:

```dotenv
CLIPROXYAPI_BASE_URL="http://localhost:8317/v1"
MODEL="cliproxyapi/claude-sonnet-4-5-20250929"
```

CLIProxyAPI wraps your Claude Pro/Max OAuth credentials and exposes an Anthropic Messages API. Set `auth.providers: []` in CLIProxyAPI's config to disable key validation. Uses `x-api-key` auth (not Bearer).

Use Claude model names (e.g., `claude-sonnet-4-5-20250929`, `claude-opus-4-20250514`).

</details>

<details>
<summary><b>Groq</b></summary>

Get a key at [console.groq.com/keys](https://console.groq.com/keys).

```dotenv
GROQ_API_KEY="***"
MODEL="groq/llama-4-maverick-17b-128e"
```

Groq uses LPU inference — the fastest tokens-per-second of any provider. The proxy converts Anthropic Messages to OpenAI chat format and streams back as Anthropic SSE. Popular models:

- `groq/llama-4-maverick-17b-128e`
- `groq/llama-4-scout-17b-16e`
- `groq/deepseek-r1-distill-llama-70b`
- `groq/qwen-2.5-coder-32b`

Groq doesn't return a native `reasoning_content` field. Reasoning models emit think tags in the content stream, which the proxy's parser handles automatically.

</details>

<details>
<summary><b>Cerebras</b></summary>

Get a free key at [cloud.cerebras.ai](https://cloud.cerebras.ai).

```dotenv
CEREBRAS_API_KEY="***"
MODEL="cerebras/llama-4-maverick-17b"
```

Cerebras uses Wafer-Scale Engine inference — extreme throughput for supported models. Supports `reasoning_effort` for thinking control. Popular models:

- `cerebras/llama-4-maverick-17b`
- `cerebras/llama-4-scout-17b`
- `cerebras/zai-glm-4.7`
- `cerebras/deepseek-r1`

Non-standard parameters like `clear_thinking` go through `extra_body` automatically.

</details>

<details>
<summary><b>Together AI</b></summary>

Get a key at [api.together.xyz](https://api.together.xyz).

```dotenv
TOGETHER_API_KEY="***"
MODEL="together/meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8"
```

Together AI hosts the widest catalog of open-weight models with an OpenAI-compatible API. Model names use `vendor/model-name` format. Popular models:

- `together/meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8`
- `together/deepseek-ai/DeepSeek-V3`
- `together/Qwen/Qwen2.5-Coder-32B-Instruct`

Standard OpenAI-compatible API — the most vanilla of the OpenAI Chat providers.

</details>

<details>
<summary><b>Kimi / Moonshot</b></summary>

Get a key at [platform.moonshot.ai/console/api-keys](https://platform.moonshot.ai/console/api-keys).

```dotenv
KIMI_API_KEY="***"
MODEL="kimi/kimi-k2.6"
```

Kimi uses Moonshot's OpenAI-compatible chat API. Reasoning history is replayed as `reasoning_content` for tool-call turns when thinking is enabled.

</details>

<details>
<summary><b>SAP Hyperspace (HAI)</b></summary>

The SAP Hyperspace AI proxy ("HAI") exposes a **native Anthropic Messages API** and routes requests to Claude, GPT, and Gemini model families through a single SAP-approved endpoint. This lets Claude Code users pick a cheaper or different model (e.g. Gemini or GPT) instead of always paying for the most expensive default.

Point the proxy at your Hyperspace relay's `/anthropic/v1` endpoint and set the bearer token:

```dotenv
HYPERSPACE_BASE_URL="http://localhost:6655/anthropic/v1"
HYPERSPACE_API_KEY="***"
MODEL="hyperspace/gemini-2.5-pro"
# or: hyperspace/gpt-5, hyperspace/claude-sonnet-latest
```

Transport is native Anthropic Messages (Bearer auth + `anthropic-version` header), so streaming, tool use, and thinking blocks pass through unchanged — identical handling to the OpenRouter native path. Because Hyperspace resolves model aliases server-side, `MODEL` accepts whatever model IDs your relay advertises.

</details>

<details>
<summary><b>Mix providers by model tier</b></summary>

Each tier can use a different provider:

```dotenv
NVIDIA_NIM_API_KEY="nvapi-your-key"
OPENROUTER_API_KEY="sk-or-your-key"

MODEL_OPUS="nvidia_nim/moonshotai/kimi-k2.5"
MODEL_SONNET="open_router/deepseek/deepseek-r1-0528:free"
MODEL_HAIKU="lmstudio/unsloth/GLM-4.7-Flash-GGUF"
MODEL="nvidia_nim/z-ai/glm4.7"
```

</details>

## Connect Claude Code

### Claude Code CLI

```bash
ANTHROPIC_AUTH_TOKEN="freecc" ANTHROPIC_BASE_URL="http://localhost:8082" claude
```

### VS Code Extension

Open Settings, search for `claude-code.environmentVariables`, choose **Edit in settings.json**, and add:

```json
"claudeCode.environmentVariables": [
  { "name": "ANTHROPIC_BASE_URL", "value": "http://localhost:8082" },
  { "name": "ANTHROPIC_AUTH_TOKEN", "value": "freecc" }
]
```

Reload the extension. If the extension shows a login screen, choose the Anthropic Console path once; the local proxy still handles model traffic after the environment variables are active.

### JetBrains ACP

Edit the installed Claude ACP config:

- Windows: `C:\Users\%USERNAME%\AppData\Roaming\JetBrains\acp-agents\installed.json`
- Linux/macOS: `~/.jetbrains/acp.json`

Set the environment for `acp.registry.claude-acp`:

```json
"env": {
  "ANTHROPIC_BASE_URL": "http://localhost:8082",
  "ANTHROPIC_AUTH_TOKEN": "freecc"
}
```

Restart the IDE after changing the file.

### Model Picker

`claude-pick` lets you choose a model at launch time. It appends the selected
`provider/model` to the auth token so the running proxy can route that Claude
Code process without restarting the service or editing `.env`.

```bash
brew install fzf
alias claude-pick="/absolute/path/to/claude-code-proxy/claude-pick"
claude-pick
```

You can also create fixed aliases:

```bash
alias claude-kimi='ANTHROPIC_BASE_URL="http://localhost:8082" ANTHROPIC_AUTH_TOKEN="freecc:nvidia_nim/moonshotai/kimi-k2.5" claude'
```

## Configuration Reference

[`.env.example`](.env.example) is the canonical list of variables. The sections below are the ones most users change.

### Model Routing

```dotenv
MODEL="nvidia_nim/z-ai/glm4.7"
MODEL_OPUS=
MODEL_SONNET=
MODEL_HAIKU=
ENABLE_MODEL_THINKING=true
ENABLE_OPUS_THINKING=
ENABLE_SONNET_THINKING=
ENABLE_HAIKU_THINKING=
```

Blank per-tier values inherit the fallback. Blank thinking overrides inherit `ENABLE_MODEL_THINKING`.

### Provider Keys And URLs

```dotenv
NVIDIA_NIM_API_KEY=""
NVIDIA_NIM_API_KEYS=""
NVIDIA_NIM_KEY_USAGE_LIMIT=0
OPENROUTER_API_KEY=""
OPENROUTER_API_KEYS=""
OPENROUTER_KEY_USAGE_LIMIT=0
DEEPSEEK_API_KEY=""
DEEPSEEK_API_KEYS=""
DEEPSEEK_KEY_USAGE_LIMIT=0
LM_STUDIO_BASE_URL="http://localhost:1234/v1"
LLAMACPP_BASE_URL="http://localhost:8080/v1"
OLLAMA_BASE_URL="http://localhost:11434"
FRIENDLIAI_API_KEY=***
FRIENDLIAI_API_KEYS=***
FRIENDLIAI_KEY_USAGE_LIMIT=0
FIREWORKS_API_KEY=***
FIREWORKS_API_KEYS=***
FIREWORKS_KEY_USAGE_LIMIT=0
VLLM_BASE_URL="http://localhost:8000/v1"
CLIPROXYAPI_BASE_URL="http://localhost:8317/v1"
GROQ_API_KEY=***
GROQ_API_KEYS=***
GROQ_KEY_USAGE_LIMIT=0
CEREBRAS_API_KEY=***
CEREBRAS_API_KEYS=***
CEREBRAS_KEY_USAGE_LIMIT=0
TOGETHER_API_KEY=***
TOGETHER_API_KEYS=***
TOGETHER_KEY_USAGE_LIMIT=0
KIMI_API_KEY=***
KIMI_API_KEYS=***
KIMI_KEY_USAGE_LIMIT=0
```

Hosted providers can use fallback keys with comma or whitespace separated
`*_API_KEYS` values. `*_KEY_USAGE_LIMIT=0` disables proactive per-key rotation;
set a positive number to rotate after that many successful requests. On
key-scoped 401/429 failures, the proxy rotates to the next configured key before
returning an upstream error.

Proxy settings are per provider:

```dotenv
NVIDIA_NIM_PROXY=""
OPENROUTER_PROXY=""
LMSTUDIO_PROXY=""
LLAMACPP_PROXY=""
FRIENDLIAI_PROXY=""
FIREWORKS_PROXY=""
VLLM_PROXY=""
CLIPROXYAPI_PROXY=""
GROQ_PROXY=""
CEREBRAS_PROXY=""
TOGETHER_PROXY=""
KIMI_PROXY=""
```

### Rate Limits And Timeouts

```dotenv
PROVIDER_RATE_LIMIT=1
PROVIDER_RATE_WINDOW=3
PROVIDER_MAX_CONCURRENCY=5
PROVIDER_MAX_RETRIES=8
PROVIDER_RETRY_BASE_DELAY=2
PROVIDER_RETRY_MAX_DELAY=120
HTTP_READ_TIMEOUT=
HTTP_WRITE_TIMEOUT=10
HTTP_CONNECT_TIMEOUT=10
```

Use lower limits for free hosted providers; local providers can usually tolerate higher concurrency if the machine can handle it.
The retry settings apply to provider 429s, retryable 5xx responses, and transient network errors; 429 responses honor `Retry-After` when the upstream sends it.
Leave `HTTP_READ_TIMEOUT` blank, `0`, or `none` to wait indefinitely between streamed provider chunks while still enforcing connect/write timeouts.

### Security And Diagnostics

```dotenv
ANTHROPIC_AUTH_TOKEN=
LOG_RAW_API_PAYLOADS=false
LOG_RAW_SSE_EVENTS=false
LOG_API_ERROR_TRACEBACKS=false
```

Raw logging flags can expose prompts, tool arguments, paths, and model output. Keep them off unless you are debugging locally.

### Local Web Tools

```dotenv
ENABLE_WEB_SERVER_TOOLS=false
WEB_FETCH_ALLOWED_SCHEMES=http,https
WEB_FETCH_ALLOW_PRIVATE_NETWORKS=false
```

These tools perform outbound HTTP from the proxy for forced Anthropic `web_search` / `web_fetch` server tools. Keep them disabled unless you explicitly want the proxy to make network requests on behalf of clients. Keep private-network access disabled unless you are in a controlled lab environment; allowing private targets can create SSRF exposure.

## Troubleshooting

### Claude Code says `undefined ... input_tokens`, `$.speed`, or malformed response

Update to the latest commit first. Older versions could emit invalid usage metadata in streaming responses. Then check:

- `ANTHROPIC_BASE_URL` is `http://localhost:8082`, not `http://localhost:8082/v1`.
- The proxy is returning Server-Sent Events for `/v1/messages`.
- `server.log` contains no upstream 400/500 response before the malformed-response error.

### llama.cpp or LM Studio returns HTTP 400

This usually means the local runtime rejected the Anthropic Messages request before the proxy could stream a model answer.

Check:

- The local server supports `POST /v1/messages`.
- The model and runtime support the requested context length and tools.
- llama.cpp was started with enough `--ctx-size` for Claude Code prompts.
- The configured base URL includes `/v1` for LM Studio and llama.cpp.

### Provider disconnects during streaming

Errors like `incomplete chunked read`, `server disconnected`, or a peer closing the body usually come from the upstream provider or gateway. Reduce concurrency, raise timeouts, or retry later.

### Provider rate limits or overloads

Errors like `Provider rate limit reached`, HTTP 429, HTTP 502/503/504, or overload messages come from the selected upstream provider. The proxy retries retryable failures with exponential backoff and honors upstream `Retry-After` headers. If the error still reaches Claude Code, lower `PROVIDER_MAX_CONCURRENCY`, lower `PROVIDER_RATE_LIMIT`, increase retry settings, or route that request to another provider/model with an auth-token suffix.

### Health checks work but authenticated probes return 401

When `ANTHROPIC_AUTH_TOKEN` is set, every protected route needs the same token in `x-api-key`, `authorization: Bearer ...`, or `anthropic-auth-token`. For request-scoped model routing, append the model after a colon, for example `freecc:open_router/google/gemma-4-26b-a4b-it:free`; the proxy validates only the token prefix.

### Tool calls work on one model but not another

Tool support is model and provider dependent. Some OpenAI-compatible models emit malformed tool-call deltas, omit tool names, or return tool calls as plain text. Try another model or provider before assuming the proxy is broken.

### The VS Code extension still shows a login screen

Confirm the extension environment variables are set, then reload the extension or restart VS Code. The browser login flow may still appear once; the local proxy is used when `ANTHROPIC_BASE_URL` is active in the extension process.

## How It Works

```text
Claude Code CLI / IDE
        |
        | Anthropic Messages API
        v
Claude Code Proxy (:8082)
        |
        | provider-specific request/stream adapter
        v
NIM / OpenRouter / DeepSeek / LM Studio / llama.cpp / Ollama / FriendliAI / Fireworks AI / vLLM / CLIProxyAPI / Groq / Cerebras / Together / Kimi / Hyperspace
```

Important pieces:

- FastAPI exposes Anthropic-compatible routes such as `/v1/messages`, `/v1/messages/count_tokens`, and `/v1/models`.
- Model routing resolves the Claude model name to `MODEL_OPUS`, `MODEL_SONNET`, `MODEL_HAIKU`, or `MODEL`.
- NIM uses OpenAI chat streaming translated into Anthropic SSE.
- OpenRouter, DeepSeek, LM Studio, llama.cpp, Ollama, FriendliAI, Fireworks AI, vLLM, CLIProxyAPI, and SAP Hyperspace (HAI) use Anthropic Messages style transports.
- Groq, Cerebras, Together AI, and Kimi use OpenAI chat streaming translated into Anthropic SSE.
- The proxy normalizes thinking blocks, tool calls, token usage metadata, and provider errors into the shape Claude Code expects.
- Request optimizations answer trivial Claude Code probes locally to save latency and quota.

## Development

### Project Structure

```text
claude-code-proxy/
├── server.py              # ASGI entry point
├── api/                   # FastAPI routes, service layer, routing, optimizations
├── core/                  # Shared Anthropic protocol helpers and SSE utilities
├── providers/             # Provider transports, registry, rate limiting
├── cli/                   # Package entry points
├── config/                # Settings, provider catalog, logging
└── tests/                 # Unit and contract tests
```

### Commands

```bash
uv run ruff format
uv run ruff check
uv run ty check
uv run pytest
```

Run them in that order before pushing. CI enforces the same checks.

### Package Scripts

`pyproject.toml` installs:

- `claude-code-proxy`: starts the proxy with configured host and port.
- `ccp-init`: creates the user config template at `~/.config/claude-code-proxy/.env`.
- `free-claude-code` and `fcc-init`: compatibility aliases for the old package name.

### Extending

- Add OpenAI-compatible providers by extending `OpenAIChatTransport`.
- Add Anthropic Messages providers by extending `AnthropicMessagesTransport`.
- Register provider metadata in `config.provider_catalog` and factory wiring in `providers.registry`.

## Contributing

- Report bugs and feature requests in [Issues](https://github.com/suparious/claude-code-proxy/issues).
- Keep changes small and covered by focused tests.
- Do not open Docker integration PRs.
- Do not open README change PRs just open an issue for it.
- Run the full check sequence before opening a pull request.
- The syntax Except X, Y is brought back in python 3.14 final version (not in 3.14 alpha). Keep in mind before opening PRs.

## License

MIT License. See [LICENSE](LICENSE) for details.
