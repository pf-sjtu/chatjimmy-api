"""Pytest configuration and fixtures."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

# Set test environment variables before importing app
# Use a test-only key that is clearly not a real secret
os.environ.setdefault("API_KEY", "test-only-fake-key-for-testing")
os.environ.setdefault("CHATJIMMY_BASE_URL", "https://chatjimmy.ai")
os.environ.setdefault("CHATJIMMY_TIMEOUT", "30")
os.environ.setdefault("LOG_LEVEL", "debug")


@pytest.fixture
def mock_env_vars():
    """Set up test environment variables."""
    env_vars = {
        "API_KEY": "test-only-fake-key-for-testing",
        "CHATJIMMY_BASE_URL": "https://chatjimmy.ai",
        "CHATJIMMY_TIMEOUT": "30",
        "HTTP_PROXY": "http://localhost:10808",
        "HTTPS_PROXY": "http://localhost:10808",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield env_vars


@pytest.fixture
def mock_stats():
    """Create mock stats data."""
    from chatjimmy.client import Stats
    
    return Stats(
        created_at=1234567890.0,
        done=True,
        done_reason="stop",
        total_duration=1.5,
        ttft=0.1,
        prefill_tokens=10,
        prefill_rate=5000.0,
        decode_tokens=50,
        decode_rate=17000.0,
        total_tokens=60,
        total_time=1.5,
        roundtrip_time=100.0,
        topk=8,
        status=200,
        reason="OK",
    )


@pytest.fixture
def mock_chat_response(mock_stats):
    """Create mock chat response."""
    from chatjimmy.client import ChatResponse
    
    return ChatResponse(
        text="This is a test response.",
        stats=mock_stats,
    )


@pytest.fixture
def mock_health_status():
    """Create mock health status."""
    from chatjimmy.client import HealthStatus
    
    return HealthStatus(
        status="ok",
        nextjs="healthy",
        backend="healthy",
        backend_status=200,
        backend_details={},
        timestamp="2024-01-01T00:00:00Z",
    )


@pytest.fixture
def mock_models():
    """Create mock models list."""
    from chatjimmy.client import Model
    
    return [
        Model(
            id="llama3.1-8B",
            object="model",
            created=0,
            owned_by="Taalas Inc.",
        )
    ]


@pytest.fixture
def mock_session():
    """Create mock requests session."""
    session = MagicMock()
    session.headers = {}
    session.proxies = {}
    return session


@pytest.fixture
def client_with_mock_session(mock_session):
    """Create ChatJimmy client with mocked session."""
    from chatjimmy.client import ChatJimmy
    
    with patch("chatjimmy.client.requests.Session") as MockSession:
        MockSession.return_value = mock_session
        client = ChatJimmy(base_url="https://chatjimmy.ai", timeout=30)
        yield client


@pytest.fixture
def test_app():
    """Create FastAPI test app."""
    from chatjimmy.server import app
    
    return app


@pytest.fixture
def test_client(test_app):
    """Create FastAPI test client."""
    from fastapi.testclient import TestClient
    
    return TestClient(test_app)


@pytest.fixture
def valid_chat_request():
    """Create valid chat completion request data."""
    return {
        "model": "llama3.1-8B",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ],
        "stream": False,
        "temperature": 0.7,
        "top_k": 8,
    }


@pytest.fixture
def valid_chat_request_streaming():
    """Create valid streaming chat completion request data."""
    return {
        "model": "llama3.1-8B",
        "messages": [
            {"role": "user", "content": "Hello!"}
        ],
        "stream": True,
    }


@pytest.fixture
def test_api_key():
    """Return a test-only API key."""
    return "test-only-fake-key-for-testing"


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances before each test."""
    # Reset server singleton
    import chatjimmy.server as server_module
    server_module._chatjimmy_client = None
    yield
