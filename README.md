# chatjimmy

Unofficial Python wrapper for the chatjimmy.ai API with OpenAI-compatible server.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)

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
- [Documentation](#documentation)

---

## Features

### Client Library
- 🚀 Simple, intuitive API
- 💬 Streaming and non-streaming chat
- 📊 Detailed inference stats (tokens/sec, TTFT, latency)

### API Server
- 🔌 **OpenAI-compatible endpoints** (`/v1/chat/completions`, `/v1/models`)
- 🔧 **Tool Use / Function Calling** (via prompt engineering)
- 📋 **JSON Mode / Structured Outputs** (via prompt engineering)
- 🔑 **API Key authentication**
- 🌐 **CORS support**
- 📡 **Streaming responses** (simulated)
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

---

## Client Library Usage

### Simple Question

```python
from chatjimmy import ChatJimmy

client = ChatJimmy()
print(client.ask("Explain quantum computing in one sentence."))
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

## Advanced Features

### Tool Use / Function Calling

> ⚠️ Tool use is simulated via prompt engineering. See [API Limitations](docs/api-limitations.md) for details.

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://your-api.onrender.com/v1",
    api_key="your-api-key",
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"]
            }
        }
    }
]

response = client.chat.completions.create(
    model="llama3.1-8B",
    messages=[{"role": "user", "content": "What's the weather in Paris?"}],
    tools=tools,
    tool_choice="auto",
)

# Check if model wants to call a tool
if response.choices[0].finish_reason == "tool_calls":
    tool_call = response.choices[0].message.tool_calls[0]
    print(f"Tool: {tool_call.function.name}")
    print(f"Arguments: {tool_call.function.arguments}")
```

### JSON Mode

> ⚠️ JSON mode is simulated via prompt engineering. See [API Limitations](docs/api-limitations.md) for details.

```python
response = client.chat.completions.create(
    model="llama3.1-8B",
    messages=[{
        "role": "user",
        "content": "List 3 planets in our solar system"
    }],
    response_format={"type": "json_object"},
)

import json
data = json.loads(response.choices[0].message.content)
print(data)
```

### JSON Schema

```python
response = client.chat.completions.create(
    model="llama3.1-8B",
    messages=[{
        "role": "user",
        "content": "Generate a user profile"
    }],
    response_format={
        "type": "json_object",
        "json_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "email": {"type": "string"}
            },
            "required": ["name", "age"]
        }
    },
)
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
5. Deploy!

See [docs/deployment.md](docs/deployment.md) for detailed instructions.

### Docker

```bash
# Build
docker build -t chatjimmy-api .

# Run
docker run -p 8000:8000 -e API_KEY=your-key chatjimmy-api
```

### Local Development

```bash
# Clone
git clone https://github.com/pf-sjtu/chatjimmy-api.git
cd chatjimmy-api

# Install
pip install -e ".[server]"

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
```

### Proxy Settings

If you need to use a proxy to access chatjimmy.ai:

```env
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=http://proxy.example.com:8080
```

---

## Limitations

This API is a compatibility layer over chatjimmy.ai, which has some inherent limitations:

### Model Limitations

- **Single Model**: Only `llama3.1-8B` is available
- **Context Length**: ~6,064 tokens maximum input
- **No Multi-modal**: Text only, no image/audio support

### API Limitations

- **Simulated Streaming**: chatjimmy.ai doesn't truly stream; we simulate it
- **Tool Use**: Simulated via prompt engineering, not native
- **JSON Mode**: Simulated via prompt engineering, no schema validation
- **No logprobs**: Not supported by upstream API
- **Temperature**: Mapped to `top_k`, not true temperature sampling

For complete details, see [docs/api-limitations.md](docs/api-limitations.md).

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
│   ├── client.py            # Original client library
│   ├── server.py            # FastAPI server (NEW)
│   ├── models.py            # Pydantic models (NEW)
│   ├── config.py            # Configuration (NEW)
│   └── __main__.py          # CLI entry point (NEW)
├── docs/
│   ├── api-limitations.md   # API limitations documentation
│   └── deployment.md        # Deployment guide
├── render.yaml              # Render deployment config
├── .env.example             # Environment variables template
├── pyproject.toml           # Project configuration
└── README.md                # This file
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
