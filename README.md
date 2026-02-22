# chatjimmy

Unofficial Python wrapper for the chatjimmy.ai API.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[chatjimmy.ai](https://chatjimmy.ai) is a demo chatbot by [Taalas](https://taalas.com), running **Llama 3.1 8B** on their custom HC1 silicon at ~17,000 tokens/sec per user.

## Features

- 🚀 Simple, intuitive API
- 💬 Streaming and non-streaming chat
- 📊 Detailed inference stats (tokens/sec, TTFT, latency)
- 🏥 Health check and model listing
- 📎 File attachment support
- 🔒 No authentication required

## Installation

```bash
pip install chatjimmy
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add chatjimmy
```

## Quick Start

```python
from chatjimmy import ChatJimmy

client = ChatJimmy()

# Simple question
answer = client.ask("What is the capital of France?")
print(answer)
```

## Usage

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

### Multi-turn Conversation

```python
from chatjimmy import ChatJimmy

client = ChatJimmy()

messages = [{"role": "user", "content": "My name is Mohamed."}]
resp = client.chat(messages)
print(resp.text)

messages.append({"role": "assistant", "content": resp.text})
messages.append({"role": "user", "content": "What's my name?"})
resp = client.chat(messages)
print(resp.text)
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

### Health Check

```python
from chatjimmy import ChatJimmy

client = ChatJimmy()
health = client.health()

print(health.healthy)       # True/False
print(health.backend)       # "healthy"
print(health.timestamp)     # ISO timestamp
```

### List Models

```python
from chatjimmy import ChatJimmy

client = ChatJimmy()

for model in client.models():
    print(f"{model.id} (by {model.owned_by})")
```

### Using Message Objects

```python
from chatjimmy import ChatJimmy, Message

client = ChatJimmy()

response = client.chat(
    messages=[Message(role="user", content="Hello!")],
    system_prompt="Reply in French.",
)
print(response.text)
```

### Attachments

```python
from chatjimmy import ChatJimmy, Attachment

client = ChatJimmy()

attachment = Attachment(name="data.txt", size=11, content="hello world")
response = client.chat(
    messages=[{"role": "user", "content": "Summarize this file"}],
    attachment=attachment,
)
print(response.text)
```

## Response Stats

Every chat response includes detailed inference stats from the Taalas HC1 hardware:

```python
response = client.chat(messages=[{"role": "user", "content": "hi"}])
stats = response.stats

stats.prefill_tokens    # input tokens processed
stats.prefill_rate      # input processing speed (tokens/sec)
stats.decode_tokens     # output tokens generated
stats.decode_rate       # output generation speed (tokens/sec)
stats.total_tokens      # prefill + decode
stats.ttft              # time to first token (seconds)
stats.total_time        # total inference time (seconds)
stats.roundtrip_time    # network round trip (ms)
stats.done_reason       # "stop" (natural end)
```

## API Reference

### `ChatJimmy(base_url, timeout)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` | `https://chatjimmy.ai` | API base URL |
| `timeout` | `int` | `30` | Request timeout in seconds |

### Methods

| Method | Description |
|--------|-------------|
| `ask(prompt, ...)` | Single-turn convenience method. Returns response text as string. |
| `chat(messages, ...)` | Full chat method. Returns `ChatResponse` with `.text` and `.stats`. |
| `chat_stream(messages, ...)` | Generator that yields text chunks as they arrive. |
| `health()` | Returns `HealthStatus` with `.healthy` property. |
| `models()` | Returns list of `Model` objects. |

### Chat Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `messages` | `list[dict \| Message]` | required | List of message dicts or `Message` objects |
| `model` | `str` | `llama3.1-8B` | Model ID |
| `system_prompt` | `str` | `""` | System prompt |
| `top_k` | `int` | `8` | Top-K sampling parameter |
| `attachment` | `Attachment` | `None` | File attachment |

## Known Limitations

- **Input limit**: ~6,064 prefill tokens. Requests exceeding this return an empty 200 response with no error.
- **Output**: No hard cap. Model stops naturally via EOS token (~1,200-2,400 tokens typical).
- **Model**: Only `llama3.1-8B` is available.

## About Taalas

The connection to Taalas was found in two places inside chatjimmy.ai itself:

1. The main JS bundle contains footer links to `https://taalas.com/terms-conditions` and `https://taalas.com/privacy-policy`.
2. The `/api/models` endpoint returns `"owned_by": "Taalas Inc."` in the model metadata.

## Disclaimer

This is an **unofficial** wrapper. [chatjimmy.ai](https://chatjimmy.ai) is a public demo by [Taalas](https://taalas.com). The API has no authentication and could change or go offline at any time.

## License

MIT License - see [LICENSE](LICENSE) file for details.
