# chatjimmy

Unofficial Python wrapper for the chatjimmy.ai API with OpenAI-compatible server.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/tests-80%25%2B-brightgreen.svg)](./tests)

[chatjimmy.ai](https://chatjimmy.ai) is a demo chatbot by [Taalas](https://taalas.com), running **Llama 3.1 8B** on their custom HC1 silicon at ~17,000 tokens/sec per user.

This project provides both a **Python client library** and an **OpenAI-compatible API server** that can be deployed to Render or other platforms.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Client Library Usage](#client-library-usage)
- [API Server](#api-server)
- [OpenAI SDK Compatibility](#openai-sdk-compatibility)
- [Deployment](#deployment)
- [Configuration](#configuration)
- [Limitations](#limitations)
- [Testing](#testing)
- [Documentation](#documentation)

---

## Features

### Client Library
- 🚀 Simple, intuitive API
- 💬 Streaming and non-streaming chat
- 📊 Detailed inference stats (tokens/sec, TTFT, latency)
- 🌐 HTTP/HTTPS proxy support via environment variables

### API Server
- 🔌 **OpenAI-compatible endpoints** (`/v1/chat/completions`, `/v1/models`)
- 🔑 **API Key authentication**
- 🌐 **CORS support**
- 📡 **Streaming responses** (simulated)
- 🌐 **Proxy configuration** via environment variables
- 🚀 **Ready for Render deployment**

---

## Installation

### Client Library Only

```bash
pip install chatjimmy
```

### With Server Support

```bash
pip install "chatjimmy[server]"
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add chatjimmy --extra server
```

### Development (with tests)

```bash
pip install "chatjimmy[dev]"
```

---

## Client Library Usage

### Simple Question

```python
from chatjimmy import ChatJimmy

client = ChatJimmy()
print(client.ask("Explain quantum computing in one sentence."))
```

### Using Proxy

```python
from chatjimmy import ChatJimmy

# Proxy is automatically loaded from HTTP_PROXY/HTTPS_PROXY environment variables
# Or pass explicitly:
client = ChatJimmy(
    proxies={
        "http": "http://proxy.example.com:8080",
        "https": "http://proxy.example.com:8080",
    }
)
print(client.ask("Hello!"))
```

### Chat with Options

```python
from chatjimmy import ChatJimmy

client = ChatJimmy()

response = client.chat(
    messages=[{"role": "user", "content": "Explain recursion"}],
    system_prompt="You are a computer science tutor.",
    top_k=4,
)

print(response.text)
print(f"Output tokens: {response.stats.decode_tokens}")
print(f"Speed: {response.stats.decode_rate:.0f} tokens/sec")
```

### Streaming

```python
from chatjimmy import ChatJimmy

client = ChatJimmy()

for chunk in client.chat_stream(
    messages=[{"role": "user", "content": "Write a haiku about code"}]
):
    print(chunk, end="", flush=True)
print()
```

---

## API Server

### Quick Start

```bash
# Install with server dependencies
pip install "chatjimmy[server]"

# Set API key
export API_KEY="your-secret-api-key"

# Configure proxy (if needed)
export HTTP_PROXY="http://proxy.example.com:8080"
export HTTPS_PROXY="http://proxy.example.com:8080"

# Start server
python -m chatjimmy
```

The server will start on `http://localhost:8000`.

### API Documentation

Once running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_KEY` | Recommended | - | API key for client authentication |
| `CHATJIMMY_BASE_URL` | No | `https://chatjimmy.ai` | chatjimmy API base URL |
| `CHATJIMMY_TIMEOUT` | No | `30` | Request timeout in seconds |
| `PORT` | No | `8000` | Server port |
| `HOST` | No | `0.0.0.0` | Server host |
| `LOG_LEVEL` | No | `info` | Logging level |
| `ALLOWED_ORIGINS` | No | `*` | CORS allowed origins |
| `HTTP_PROXY` | No | - | HTTP proxy URL |
| `HTTPS_PROXY` | No | - | HTTPS proxy URL |

---

## OpenAI SDK Compatibility

Use any OpenAI-compatible SDK with your deployed server:

### Python

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://your-api.onrender.com/v1",
    api_key="your-api-key",
)

# Simple chat
response = client.chat.completions.create(
    model="llama3.1-8B",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)

# Streaming
for chunk in client.chat.completions.create(
    model="llama3.1-8B",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True,
):
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### JavaScript/TypeScript

```typescript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'https://your-api.onrender.com/v1',
  apiKey: 'your-api-key',
});

const response = await client.chat.completions.create({
  model: 'llama3.1-8B',
  messages: [{ role: 'user', content: 'Hello!' }],
});

console.log(response.choices[0].message.content);
```

### cURL

```bash
curl https://your-api.onrender.com/v1/chat/completions \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1-8B",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

---

## Deployment

### Deploy to Render (Recommended)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

**Manual deployment:**

1. Fork this repository
2. Create a new Web Service on [Render](https://render.com)
3. Connect your forked repository
4. Set environment variables:
   - `API_KEY`: Your secret API key
   - `HTTP_PROXY` / `HTTPS_PROXY`: (Optional) Proxy settings
5. Deploy!

See [docs/deployment.md](docs/deployment.md) for detailed instructions.

### Docker

```bash
# Build
docker build -t chatjimmy-api .

# Run with proxy
docker run -p 8000:8000 \
  -e API_KEY=your-key \
  -e HTTP_PROXY=http://proxy:8080 \
  -e HTTPS_PROXY=http://proxy:8080 \
  chatjimmy-api
```

### Local Development

```bash
# Clone
git clone https://github.com/pf-sjtu/chatjimmy-api.git
cd chatjimmy-api

# Install
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your settings

# Run
python -m chatjimmy
```

---

## Configuration

### Using .env File

Create a `.env` file:

```env
API_KEY=your-secret-api-key
CHATJIMMY_TIMEOUT=30
LOG_LEVEL=info
ALLOWED_ORIGINS=https://your-frontend.com

# Proxy settings (if needed)
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
```

### Proxy Settings

Proxy configuration is automatically loaded from environment variables:

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
```

Or in Python:

```python
from chatjimmy import ChatJimmy

client = ChatJimmy(proxies={
    "http": "http://proxy.example.com:8080",
    "https": "http://proxy.example.com:8080",
})
```

---

## Limitations

This API is a compatibility layer over chatjimmy.ai, which has some inherent limitations:

### Model Limitations

- **Single Model**: Only `llama3.1-8B` is available
- **Context Length**: ~6,064 tokens maximum input
- **No Multi-modal**: Text only, no image/audio support

### ⚠️ Unsupported Features (Return 400 Error)

The following OpenAI API features are **explicitly disabled** and will return a 400 error:

| Feature | Status | Reason |
|---------|--------|--------|
| `tools` | ❌ **Disabled** | chatjimmy.ai does not support native tool calling |
| `tool_choice` | ❌ **Disabled** | chatjimmy.ai does not support native tool calling |
| `response_format` (json_object/json_schema) | ❌ **Disabled** | chatjimmy.ai does not guarantee valid JSON output |

**Why these are disabled:**

These features were previously simulated via prompt engineering, but this approach:
1. Does not comply with OpenAI API standards (no guaranteed behavior)
2. Produces unreliable results (model may not follow instructions)
3. Creates a false sense of compatibility

**Alternative approaches:**

Instead of using `tools`, implement tool calling in your application:

```python
# Don't do this:
response = client.chat.completions.create(
    model="llama3.1-8B",
    messages=messages,
    tools=tools,  # ❌ Will return 400 error
)

# Do this instead:
response = client.chat.completions.create(
    model="llama3.1-8B",
    messages=messages_with_tool_descriptions,
)
# Parse response and handle tool calls in your code
```

Instead of using `response_format`, parse JSON manually:

```python
# Don't do this:
response = client.chat.completions.create(
    model="llama3.1-8B",
    messages=messages,
    response_format={"type": "json_object"},  # ❌ Will return 400 error
)

# Do this instead:
response = client.chat.completions.create(
    model="llama3.1-8B",
    messages=messages_with_json_instructions,
)
import json
data = json.loads(response.choices[0].message.content)
```

### Other Limitations

- **Streaming**: Simulated (not true SSE), full response buffered then chunked
- **Temperature**: Mapped to `top_k`, not true temperature sampling
- **max_tokens**: Cannot be enforced
- **stop sequences**: Not supported
- **logprobs**: Not supported

For complete details, see [docs/api-limitations.md](docs/api-limitations.md).

---

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=chatjimmy --cov-report=term-missing

# Run with coverage report
pytest --cov=chatjimmy --cov-report=html
open htmlcov/index.html

# Run specific test files
pytest tests/test_client.py
pytest tests/test_server.py
pytest tests/test_models.py

# Run with verbose output
pytest -v
```

The test suite achieves **80%+ coverage** with:
- Unit tests for all client functionality
- Unit tests for all server endpoints
- Integration tests for complete flows
- Proxy configuration tests
- Error handling tests

---

## Documentation

- [API Limitations](docs/api-limitations.md) - Detailed compatibility and limitations
- [Deployment Guide](docs/deployment.md) - Deploy to Render, Docker, and more

---

## Project Structure

```
chatjimmy-api/
├── src/chatjimmy/
│   ├── __init__.py          # Package exports
│   ├── client.py            # Client library with proxy support
│   ├── server.py            # FastAPI server
│   ├── models.py            # Pydantic models (with unsupported feature validation)
│   ├── config.py            # Environment configuration
│   └── __main__.py          # CLI entry point
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Test fixtures
│   ├── test_client.py       # Client library tests
│   ├── test_server.py       # API endpoint tests
│   ├── test_models.py       # Model validation tests
│   ├── test_config.py       # Configuration tests
│   └── test_integration.py  # Integration tests
├── docs/
│   ├── api-limitations.md   # API compatibility & limitations
│   └── deployment.md        # Deployment guide
├── render.yaml              # Render deployment configuration
├── .env.example             # Environment variables template
├── pyproject.toml           # Project configuration
├── README.md                # This file
└── AGENTS.md                # Agent documentation
```

---

## How We Know It's Taalas

The connection to Taalas was found in two places inside chatjimmy.ai itself:

1. The main JS bundle (`8642-*.js`) contains footer links to `https://taalas.com/terms-conditions` and `https://taalas.com/privacy-policy` in the chat disclaimer text.
2. The `/api/models` endpoint returns `"owned_by": "Taalas Inc."` in the model metadata.

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Disclaimer

This is an **unofficial** wrapper. [chatjimmy.ai](https://chatjimmy.ai) is a public demo by [Taalas](https://taalas.com). The API has no authentication and could change or go offline at any time.
