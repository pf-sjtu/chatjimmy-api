# AGENTS.md - chatjimmy

> Agent-focused documentation for the chatjimmy project.

## Project Overview

**chatjimmy** is an unofficial Python wrapper for the [chatjimmy.ai](https://chatjimmy.ai) API - a demo chatbot running Llama 3.1 8B on Taalas HC1 custom silicon.

This project now includes:
1. **Client Library** - Python wrapper for direct API access
2. **API Server** - OpenAI-compatible FastAPI server deployable to Render

- **Purpose**: 
  - Provide a simple Python interface to chatjimmy.ai
  - Provide an OpenAI-compatible API for easy integration
- **Architecture**: 
  - Client: Single-module library with dataclass-based models
  - Server: FastAPI with Pydantic v2 models, environment-based config
- **API Base URL**: `https://chatjimmy.ai`

## Project Structure

```
chatjimmy-api/
├── src/
│   └── chatjimmy/
│       ├── __init__.py          # Public API exports
│       ├── client.py            # Core client implementation
│       ├── server.py            # FastAPI server (OpenAI-compatible)
│       ├── models.py            # Pydantic models for API
│       ├── config.py            # Environment configuration
│       └── __main__.py          # CLI entry point
├── docs/
│   ├── README.md                # Docs index
│   ├── api-limitations.md       # API compatibility & limitations
│   └── deployment.md            # Deployment guide
├── render.yaml                  # Render deployment configuration
├── .env.example                 # Environment variables template
├── pyproject.toml               # Project metadata & dependencies
├── LICENSE                      # MIT License
├── README.md                    # User documentation
└── AGENTS.md                    # This file
```

## Code Architecture

### Client Components (src/chatjimmy/client.py)

| Component | Type | Description |
|-----------|------|-------------|
| `ChatJimmy` | Class | Main client - handles HTTP requests |
| `Stats` | Dataclass | Inference statistics from HC1 hardware |
| `ChatResponse` | Dataclass | Response with text and stats |
| `Model` | Dataclass | Available model metadata |
| `HealthStatus` | Dataclass | Server health status |
| `Message` | Dataclass | Chat message (role + content) |
| `Attachment` | Dataclass | File attachment for chat |

### Server Components

#### server.py
FastAPI application with:
- `/health` - Health check endpoint
- `/v1/models` - List available models
- `/v1/chat/completions` - Chat completion (streaming & non-streaming)
- API Key authentication via Bearer token
- CORS middleware

#### models.py
Pydantic v2 models for OpenAI-compatible request/response:
- `ChatCompletionRequest` / `ChatCompletionResponse`
- `ToolFunction` / `ToolCall` - Function calling support
- `ResponseFormat` - JSON mode support
- Streaming response models

#### config.py
Pydantic-settings based configuration:
- Environment variables with `.env` file support
- Proxy configuration
- CORS settings

### Data Flow

#### Client Mode
```
User Input → ChatJimmy.chat() → _chat_stream() → HTTP POST /api/chat
                                           ↓
                              Parse SSE response + stats block
                                           ↓
                              Return ChatResponse(text, stats)
```

#### Server Mode
```
Client Request → FastAPI → ChatCompletionRequest validation
                                ↓
                    build_enhanced_system_prompt() [tools/json]
                                ↓
                    ChatJimmy.chat() / _chat_stream()
                                ↓
                    OpenAI-compatible Response
```

## Development Guide

### Environment Setup

This project uses [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
# Install all dependencies (including server)
uv sync --extra server

# Run server locally
uv run python -m chatjimmy

# Build package
uv build
```

### Dependencies

**Core:**
- `requests>=2.28.0` - HTTP client library

**Server (optional):**
- `fastapi>=0.110.0` - Web framework
- `uvicorn[standard]>=0.27.0` - ASGI server
- `pydantic>=2.5.0` - Data validation
- `pydantic-settings>=2.1.0` - Configuration management

Python >= 3.10

### Adding New Features

#### Client Changes
When modifying `client.py`:
1. Add new dataclasses at the top (after imports, before `ChatJimmy`)
2. Update `__all__` in `__init__.py` if adding new exports
3. Follow existing patterns: Use dataclasses, type hints, docstrings
4. Handle errors with `r.raise_for_status()`

#### Server Changes
When modifying server code:
1. **models.py**: Add Pydantic models first
2. **server.py**: Implement endpoint handlers
3. Update both streaming and non-streaming paths
4. Add proper error handling and logging

### API Endpoint Mapping

| Method | HTTP | Endpoint | Purpose |
|--------|------|----------|---------|
| Client: `health()` | GET | `/api/health` | Check server status |
| Client: `models()` | GET | `/api/models` | List available models |
| Client: `chat()` | POST | `/api/chat` | Send chat messages |
| Server: `health_check()` | GET | `/health` | Server health check |
| Server: `list_models()` | GET | `/v1/models` | OpenAI-compatible models |
| Server: `create_chat_completion()` | POST | `/v1/chat/completions` | OpenAI-compatible chat |

### Stats Parsing

The API embeds JSON stats in the response text:

```
<|stats|>{"decode_tokens": 42, "decode_rate": 17345.6, ...}<|/stats|>
```

The regex `_STATS_RE` extracts this block. Stats include:
- Token counts (prefill/decode/total)
- Speed metrics (tokens/sec)
- Timing (TTFT, total_time, roundtrip_time)
- Status codes

## Key Implementation Details

### Tool Use Simulation

Since chatjimmy doesn't natively support OpenAI-style tool calling:

1. Tools are converted to system prompt instructions
2. Model is instructed to return JSON: `{"tool": "name", "arguments": {...}}`
3. Server parses this and converts to OpenAI `tool_calls` format

See `models.py::ChatCompletionRequest.build_enhanced_system_prompt()`

### JSON Mode Simulation

Since chatjimmy doesn't natively support JSON mode:

1. Response format is converted to system prompt instructions
2. If schema provided, it's included in the prompt
3. Model is instructed to respond only in JSON

### Streaming Simulation

Since chatjimmy doesn't support true streaming:

1. Full response is collected first
2. Content is split by words
3. Server-Sent Events (SSE) are generated word-by-word with 10ms delay

### Temperature Mapping

OpenAI `temperature` → chatjimmy `top_k`:

```python
top_k = max(1, min(40, int(temperature * 20)))
```

| Temperature | Top-K | Behavior |
|-------------|-------|----------|
| 0.0 | 1 | Most deterministic |
| 0.5 | 10 | Moderate randomness |
| 1.0 | 20 | High randomness |
| 2.0 | 40 | Maximum randomness |

## Testing Considerations

- **No authentication upstream**: API is completely open
- **No rate limiting observed**: Tested with 20 concurrent + 30 sequential bursts
- **Input limit**: ~6,064 prefill tokens (returns empty 200 if exceeded)
- **Single model**: Only `llama3.1-8B` available

## Configuration

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `API_KEY` | Server API key for client authentication |
| `CHATJIMMY_BASE_URL` | Upstream API URL |
| `CHATJIMMY_TIMEOUT` | Request timeout |
| `PORT` / `HOST` | Server binding |
| `LOG_LEVEL` | Logging verbosity |
| `ALLOWED_ORIGINS` | CORS origins |
| `HTTP_PROXY` / `HTTPS_PROXY` | Proxy configuration |

### Render Deployment

Use `render.yaml` for Blueprint deployment:
- Auto-generates `API_KEY` if not provided
- Health check on `/health`
- Python 3.11 runtime

## Important Notes

1. **Streaming is simulated**: Not true SSE, full response buffered then chunked
2. **Tool use is prompt-engineered**: Reliability depends on model following instructions
3. **JSON mode is prompt-engineered**: No schema validation, may output invalid JSON
4. **Session reuse**: `requests.Session()` used for connection pooling
5. **Error handling**: Uses FastAPI exception handlers for consistent responses

## Versioning

Follow [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- Current: `0.1.0` (Alpha stage)

## Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update `README.md` if API changes
- [ ] Update `AGENTS.md` if architecture changes
- [ ] Update `docs/api-limitations.md` if capability changes
- [ ] Test all examples in README
- [ ] Run `uv build` to verify package builds
- [ ] Test Render deployment
- [ ] Tag release on GitHub
