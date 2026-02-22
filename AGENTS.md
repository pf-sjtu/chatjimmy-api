# AGENTS.md - chatjimmy

> Agent-focused documentation for the chatjimmy project.

## Project Overview

**chatjimmy** is an unofficial Python wrapper for the [chatjimmy.ai](https://chatjimmy.ai) API - a demo chatbot running Llama 3.1 8B on Taalas HC1 custom silicon.

- **Purpose**: Provide a simple Python interface to interact with the chatjimmy.ai API
- **Architecture**: Single-module client library with dataclass-based models
- **API Base URL**: `https://chatjimmy.ai`

## Project Structure

```
chatjimmy-api/
├── src/
│   └── chatjimmy/
│       ├── __init__.py          # Public API exports
│       └── client.py            # Core implementation (all classes)
├── pyproject.toml               # Project metadata & dependencies
├── LICENSE                      # MIT License
├── README.md                    # User documentation
└── AGENTS.md                    # This file
```

## Code Architecture

### Core Components

All code lives in `src/chatjimmy/client.py`:

| Component | Type | Description |
|-----------|------|-------------|
| `ChatJimmy` | Class | Main client - handles HTTP requests |
| `Stats` | Dataclass | Inference statistics from HC1 hardware |
| `ChatResponse` | Dataclass | Response with text and stats |
| `Model` | Dataclass | Available model metadata |
| `HealthStatus` | Dataclass | Server health status |
| `Message` | Dataclass | Chat message (role + content) |
| `Attachment` | Dataclass | File attachment for chat |

### Data Flow

```
User Input → ChatJimmy.chat() → _chat_stream() → HTTP POST /api/chat
                                           ↓
                              Parse SSE response + stats block
                                           ↓
                              Return ChatResponse(text, stats)
```

The API returns responses with a special stats block delimited by `<|stats|>...<|/stats|>` which is parsed using regex `_STATS_RE`.

## Development Guide

### Environment Setup

This project uses [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
# Install dependencies
uv sync

# Run Python with dependencies
uv run python

# Build the package
uv build
```

### Dependencies

- `requests>=2.28.0` - HTTP client library
- Python >= 3.10

### Adding New Features

When modifying `client.py`:

1. **Add new dataclasses at the top** (after imports, before `ChatJimmy`)
2. **Update `__all__` in `__init__.py`** if adding new exports
3. **Follow existing patterns**: Use dataclasses, type hints, and docstrings
4. **Handle errors gracefully**: Use `r.raise_for_status()` for HTTP errors

### API Endpoint Mapping

| Method | HTTP | Endpoint | Purpose |
|--------|------|----------|---------|
| `health()` | GET | `/api/health` | Check server status |
| `models()` | GET | `/api/models` | List available models |
| `chat()` / `_chat_stream()` | POST | `/api/chat` | Send chat messages |

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

## Testing Considerations

- **No authentication**: API is completely open
- **No rate limiting observed**: Tested with 20 concurrent + 30 sequential bursts
- **Input limit**: ~6,064 prefill tokens (returns empty 200 if exceeded)
- **Single model**: Only `llama3.1-8B` available

## Important Notes

1. **Streaming is simulated**: The current implementation buffers the entire response and yields chunks after parsing. True streaming may be added in future.

2. **Stats extraction**: The regex `_STATS_RE` must handle cases where stats block is malformed or missing.

3. **Session reuse**: `requests.Session()` is used for connection pooling and header consistency.

4. **Error handling**: Currently relies on `requests` exceptions. Custom exception classes may be added for API-specific errors.

## Versioning

Follow [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- Current: `0.1.0` (Alpha stage)

## Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update `README.md` if API changes
- [ ] Update `AGENTS.md` if architecture changes
- [ ] Test all examples in README
- [ ] Run `uv build` to verify package builds
- [ ] Tag release on GitHub
