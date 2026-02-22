"""Tests for chatjimmy client module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from chatjimmy.client import (
    Attachment,
    ChatJimmy,
    ChatResponse,
    HealthStatus,
    Message,
    Model,
    Stats,
    get_proxy_config,
)


class TestProxyConfig:
    """Test proxy configuration."""
    
    def test_get_proxy_config_from_env(self):
        """Test getting proxy config from environment variables."""
        env_vars = {
            "HTTP_PROXY": "http://proxy.example.com:8080",
            "HTTPS_PROXY": "https://proxy.example.com:8080",
        }
        with patch.dict("os.environ", env_vars, clear=False):
            proxies = get_proxy_config()
            assert proxies == {
                "http": "http://proxy.example.com:8080",
                "https": "https://proxy.example.com:8080",
            }
    
    def test_get_proxy_config_http_only(self):
        """Test getting proxy config with HTTP only."""
        env_vars = {"HTTP_PROXY": "http://proxy.example.com:8080"}
        with patch.dict("os.environ", env_vars, clear=False):
            with patch.dict("os.environ", {"HTTPS_PROXY": ""}, clear=False):
                proxies = get_proxy_config()
                assert proxies == {"http": "http://proxy.example.com:8080"}
    
    def test_get_proxy_config_none(self):
        """Test getting proxy config when no env vars set."""
        with patch.dict("os.environ", {}, clear=True):
            proxies = get_proxy_config()
            assert proxies is None


class TestStats:
    """Test Stats dataclass."""
    
    def test_stats_creation(self):
        """Test creating Stats instance."""
        stats = Stats(
            prefill_tokens=10,
            decode_tokens=20,
            total_tokens=30,
        )
        assert stats.prefill_tokens == 10
        assert stats.decode_tokens == 20
        assert stats.total_tokens == 30
    
    def test_stats_from_dict(self):
        """Test creating Stats from dictionary."""
        data = {
            "prefill_tokens": 10,
            "decode_tokens": 20,
            "unknown_field": "ignored",
        }
        stats = Stats.from_dict(data)
        assert stats.prefill_tokens == 10
        assert stats.decode_tokens == 20
        assert stats.total_tokens == 0  # Default value


class TestChatJimmyInitialization:
    """Test ChatJimmy client initialization."""
    
    def test_default_initialization(self):
        """Test default client initialization."""
        with patch("chatjimmy.client.requests.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value = mock_session
            
            client = ChatJimmy()
            
            assert client.base_url == "https://chatjimmy.ai"
            assert client.timeout == 30
            assert client.proxies is None
            mock_session.headers.update.assert_called_once()
    
    def test_custom_initialization(self):
        """Test client initialization with custom parameters."""
        with patch("chatjimmy.client.requests.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value = mock_session
            
            proxies = {"http": "http://proxy:8080"}
            client = ChatJimmy(
                base_url="https://custom.example.com",
                timeout=60,
                proxies=proxies,
            )
            
            assert client.base_url == "https://custom.example.com"
            assert client.timeout == 60
            assert client.proxies == proxies
            mock_session.proxies.update.assert_called_once_with(proxies)
    
    def test_proxy_from_env(self):
        """Test that proxy is loaded from environment."""
        env_vars = {"HTTP_PROXY": "http://proxy.example.com:8080"}
        with patch.dict("os.environ", env_vars, clear=False):
            with patch("chatjimmy.client.requests.Session") as MockSession:
                mock_session = MagicMock()
                MockSession.return_value = mock_session
                
                client = ChatJimmy()
                
                assert client.proxies == {"http": "http://proxy.example.com:8080"}


class TestChatJimmyHealth:
    """Test health check functionality."""
    
    def test_health_check_success(self, client_with_mock_session, mock_session):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "ok",
            "nextjs": "healthy",
            "backend": "healthy",
            "backendStatus": 200,
            "backendDetails": {},
            "timestamp": "2024-01-01T00:00:00Z",
        }
        mock_session.get.return_value = mock_response
        
        health = client_with_mock_session.health()
        
        assert health.healthy is True
        assert health.status == "ok"
        assert health.backend == "healthy"
        mock_session.get.assert_called_once_with(
            "https://chatjimmy.ai/api/health",
            timeout=30,
            proxies=client_with_mock_session.proxies,
        )
    
    def test_health_check_unhealthy(self, client_with_mock_session, mock_session):
        """Test health check when backend is unhealthy."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "error",
            "nextjs": "healthy",
            "backend": "unhealthy",
            "backendStatus": 500,
        }
        mock_session.get.return_value = mock_response
        
        health = client_with_mock_session.health()
        
        assert health.healthy is False
    
    def test_health_check_request_error(self, client_with_mock_session, mock_session):
        """Test health check when request fails."""
        mock_session.get.side_effect = requests.RequestException("Connection error")
        
        with pytest.raises(requests.RequestException):
            client_with_mock_session.health()


class TestChatJimmyModels:
    """Test models listing functionality."""
    
    def test_list_models_success(self, client_with_mock_session, mock_session):
        """Test successful models listing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "llama3.1-8B",
                    "object": "model",
                    "created": 0,
                    "owned_by": "Taalas Inc.",
                }
            ]
        }
        mock_session.get.return_value = mock_response
        
        models = client_with_mock_session.models()
        
        assert len(models) == 1
        assert models[0].id == "llama3.1-8B"
        assert models[0].owned_by == "Taalas Inc."
        mock_session.get.assert_called_once_with(
            "https://chatjimmy.ai/api/models",
            timeout=30,
            proxies=client_with_mock_session.proxies,
        )
    
    def test_list_models_empty(self, client_with_mock_session, mock_session):
        """Test models listing with empty response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_session.get.return_value = mock_response
        
        models = client_with_mock_session.models()
        
        assert len(models) == 0


class TestChatJimmyChat:
    """Test chat functionality."""
    
    def test_chat_success(self, client_with_mock_session, mock_session):
        """Test successful chat completion."""
        stats_json = json.dumps({
            "prefill_tokens": 10,
            "decode_tokens": 20,
            "total_tokens": 30,
            "decode_rate": 17000.0,
            "done_reason": "stop",
        })
        response_text = f"Hello there!<|stats|>{stats_json}<|/stats|>"
        
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [response_text.encode()]
        mock_session.post.return_value = mock_response
        
        response = client_with_mock_session.chat(
            messages=[{"role": "user", "content": "Hi!"}],
            model="llama3.1-8B",
            system_prompt="Be helpful.",
            top_k=8,
        )
        
        assert response.text == "Hello there!"
        assert response.stats is not None
        assert response.stats.prefill_tokens == 10
        assert response.stats.decode_tokens == 20
        
        # Verify request
        call_args = mock_session.post.call_args
        assert call_args[0][0] == "https://chatjimmy.ai/api/chat"
        assert call_args[1]["json"]["chatOptions"]["selectedModel"] == "llama3.1-8B"
        assert call_args[1]["json"]["chatOptions"]["systemPrompt"] == "Be helpful."
        assert call_args[1]["json"]["chatOptions"]["topK"] == 8
    
    def test_chat_no_stats(self, client_with_mock_session, mock_session):
        """Test chat completion without stats in response."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"Simple response"]
        mock_session.post.return_value = mock_response
        
        response = client_with_mock_session.chat(
            messages=[{"role": "user", "content": "Hi!"}],
        )
        
        assert response.text == "Simple response"
        assert response.stats is None
    
    def test_chat_with_message_objects(self, client_with_mock_session, mock_session):
        """Test chat with Message objects."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"Response<|stats|>{}<|/stats|>"]
        mock_session.post.return_value = mock_response
        
        messages = [
            Message(role="system", content="System prompt"),
            Message(role="user", content="User message"),
        ]
        
        client_with_mock_session.chat(messages=messages)
        
        call_args = mock_session.post.call_args
        sent_messages = call_args[1]["json"]["messages"]
        assert len(sent_messages) == 2
        assert sent_messages[0]["role"] == "system"
        assert sent_messages[0]["content"] == "System prompt"
    
    def test_chat_with_attachment(self, client_with_mock_session, mock_session):
        """Test chat with attachment."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"Response<|stats|>{}<|/stats|>"]
        mock_session.post.return_value = mock_response
        
        attachment = Attachment(name="test.txt", size=100, content="file content")
        
        client_with_mock_session.chat(
            messages=[{"role": "user", "content": "Read this"}],
            attachment=attachment,
        )
        
        call_args = mock_session.post.call_args
        assert call_args[1]["json"]["attachment"] == {
            "name": "test.txt",
            "size": 100,
            "content": "file content",
        }
    
    def test_chat_error(self, client_with_mock_session, mock_session):
        """Test chat when request fails."""
        mock_session.post.side_effect = requests.RequestException("Network error")
        
        with pytest.raises(requests.RequestException):
            client_with_mock_session.chat(messages=[{"role": "user", "content": "Hi!"}])


class TestChatJimmyChatStream:
    """Test streaming chat functionality."""
    
    def test_chat_stream(self, client_with_mock_session, mock_session):
        """Test streaming chat."""
        stats_json = json.dumps({
            "decode_tokens": 20,
            "done_reason": "stop",
        })
        response_text = f"Streaming response<|stats|>{stats_json}<|/stats|>"
        
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [response_text.encode()]
        mock_session.post.return_value = mock_response
        
        chunks = list(client_with_mock_session.chat_stream(
            messages=[{"role": "user", "content": "Hi!"}],
        ))
        
        assert len(chunks) == 1
        assert chunks[0] == "Streaming response"


class TestChatJimmyAsk:
    """Test simple ask functionality."""
    
    def test_ask(self, client_with_mock_session, mock_session):
        """Test simple ask method."""
        stats_json = json.dumps({"decode_tokens": 5})
        response_text = f"Answer<|stats|>{stats_json}<|/stats|>"
        
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [response_text.encode()]
        mock_session.post.return_value = mock_response
        
        answer = client_with_mock_session.ask("What is 2+2?")
        
        assert answer == "Answer"
        
        # Verify request structure
        call_args = mock_session.post.call_args
        messages = call_args[1]["json"]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What is 2+2?"
    
    def test_ask_with_system_prompt(self, client_with_mock_session, mock_session):
        """Test ask with system prompt."""
        mock_response = MagicMock()
        mock_response.iter_content.return_value = [b"Answer<|stats|>{}<|/stats|>"]
        mock_session.post.return_value = mock_response
        
        client_with_mock_session.ask(
            prompt="Hello",
            model="llama3.1-8B",
            system_prompt="Be concise.",
            top_k=4,
        )
        
        call_args = mock_session.post.call_args
        assert call_args[1]["json"]["chatOptions"]["systemPrompt"] == "Be concise."
        assert call_args[1]["json"]["chatOptions"]["topK"] == 4


class TestDataClasses:
    """Test supporting dataclasses."""
    
    def test_message_to_dict(self):
        """Test Message to_dict method."""
        msg = Message(role="user", content="Hello")
        assert msg.to_dict() == {"role": "user", "content": "Hello"}
    
    def test_attachment_to_dict(self):
        """Test Attachment to_dict method."""
        att = Attachment(name="file.txt", size=100, content="data")
        assert att.to_dict() == {
            "name": "file.txt",
            "size": 100,
            "content": "data",
        }
    
    def test_chat_response_creation(self):
        """Test ChatResponse creation."""
        response = ChatResponse(text="Hello", stats=None)
        assert response.text == "Hello"
        assert response.stats is None
    
    def test_model_creation(self):
        """Test Model creation."""
        model = Model(id="test-model", owned_by="Test Inc.")
        assert model.id == "test-model"
        assert model.owned_by == "Test Inc."
        assert model.object == "model"
    
    def test_health_status_healthy(self):
        """Test HealthStatus healthy property."""
        status = HealthStatus(status="ok", backend="healthy")
        assert status.healthy is True
    
    def test_health_status_unhealthy(self):
        """Test HealthStatus unhealthy states."""
        assert HealthStatus(status="error", backend="healthy").healthy is False
        assert HealthStatus(status="ok", backend="unhealthy").healthy is False
        assert HealthStatus(status="", backend="").healthy is False
