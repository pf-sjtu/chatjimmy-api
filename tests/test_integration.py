"""Integration tests for chatjimmy API server."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def integration_client():
    """Create a test client with all dependencies mocked."""
    from chatjimmy.server import app, get_chatjimmy_client
    
    # Create a fresh client for each test
    from fastapi.testclient import TestClient
    return TestClient(app)


class TestEndToEndChatFlow:
    """Test complete chat flow end-to-end."""
    
    def test_simple_conversation(self, integration_client):
        """Test a simple conversation flow."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            
            # Mock the chat response
            mock_response = MagicMock()
            mock_response.text = "I'm doing well, thank you!"
            mock_response.stats = MagicMock()
            mock_response.stats.prefill_tokens = 15
            mock_response.stats.decode_tokens = 25
            mock_response.stats.total_tokens = 40
            mock_response.stats.done_reason = "stop"
            
            mock_client.chat.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            # Make the request
            response = integration_client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer sk-test-key"},
                json={
                    "model": "llama3.1-8B",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "How are you?"}
                    ]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "id" in data
            assert data["object"] == "chat.completion"
            assert data["model"] == "llama3.1-8B"
            assert "created" in data
            
            # Verify choices
            assert len(data["choices"]) == 1
            assert data["choices"][0]["message"]["role"] == "assistant"
            assert data["choices"][0]["message"]["content"] == "I'm doing well, thank you!"
            assert data["choices"][0]["finish_reason"] == "stop"
            
            # Verify usage
            assert data["usage"]["prompt_tokens"] == 15
            assert data["usage"]["completion_tokens"] == 25
            assert data["usage"]["total_tokens"] == 40
            
            # Verify the client was called correctly
            call_args = mock_client.chat.call_args
            assert call_args[1]["model"] == "llama3.1-8B"
            assert call_args[1]["system_prompt"] == "You are a helpful assistant."
            assert len(call_args[1]["messages"]) == 1
            assert call_args[1]["messages"][0]["role"] == "user"


class TestAPICompatibility:
    """Test OpenAI API compatibility."""
    
    def test_openai_sdk_request_format(self, integration_client):
        """Test that requests in OpenAI SDK format work."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Response"
            mock_response.stats = None
            mock_client.chat.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            # Typical OpenAI SDK request format
            response = integration_client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer sk-test-key"},
                json={
                    "model": "llama3.1-8B",
                    "messages": [
                        {"role": "system", "content": "Be helpful."},
                        {"role": "user", "content": "Hello!"}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 100,
                    "stream": False,
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Response should match OpenAI format
            assert "id" in data
            assert data["object"] == "chat.completion"
            assert "choices" in data
            assert "usage" in data
    
    def test_openai_sdk_response_format(self, integration_client):
        """Test that responses match OpenAI SDK format."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Test response"
            mock_response.stats = MagicMock()
            mock_response.stats.prefill_tokens = 10
            mock_response.stats.decode_tokens = 20
            mock_response.stats.total_tokens = 30
            mock_response.stats.done_reason = "stop"
            mock_client.chat.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            response = integration_client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer sk-test-key"},
                json={
                    "model": "llama3.1-8B",
                    "messages": [{"role": "user", "content": "Test"}]
                }
            )
            
            data = response.json()
            
            # Verify OpenAI-compatible response structure
            assert "id" in data
            assert data["object"] == "chat.completion"
            assert "created" in data and isinstance(data["created"], int)
            assert data["model"] == "llama3.1-8B"
            
            # Verify choices structure
            choice = data["choices"][0]
            assert "index" in choice
            assert choice["message"]["role"] == "assistant"
            assert "content" in choice["message"]
            assert "finish_reason" in choice
            
            # Verify usage structure
            usage = data["usage"]
            assert "prompt_tokens" in usage
            assert "completion_tokens" in usage
            assert "total_tokens" in usage


class TestProxyIntegration:
    """Test proxy configuration in integration scenarios."""
    
    def test_proxy_passed_to_client(self, integration_client):
        """Test that proxy settings are passed to the client."""
        with patch.dict("os.environ", {
            "HTTP_PROXY": "http://proxy.test:8080",
            "HTTPS_PROXY": "http://proxy.test:8080",
        }):
            with patch("chatjimmy.server.ChatJimmy") as mock_chatjimmy:
                mock_instance = MagicMock()
                mock_instance.health.return_value = MagicMock(healthy=True, backend="healthy")
                mock_chatjimmy.return_value = mock_instance
                
                # Reset the singleton to force new client creation
                import chatjimmy.server as server_module
                server_module._chatjimmy_client = None
                
                # Make a request that triggers client creation
                with patch("chatjimmy.server.get_settings") as mock_get_settings:
                    mock_settings = MagicMock()
                    mock_settings.api_key = "sk-test-key"
                    mock_settings.cors_origins = ["*"]
                    mock_settings.chatjimmy_base_url = "https://chatjimmy.ai"
                    mock_settings.chatjimmy_timeout = 30
                    mock_settings.proxies = {
                        "http": "http://proxy.test:8080",
                        "https": "http://proxy.test:8080",
                    }
                    mock_get_settings.return_value = mock_settings
                    
                    integration_client.get("/health")
                    
                    # Verify client was created with proxy
                    call_kwargs = mock_chatjimmy.call_args[1]
                    assert "proxies" in call_kwargs
                    assert call_kwargs["proxies"]["http"] == "http://proxy.test:8080"


class TestUnsupportedFeaturesRejection:
    """Test that unsupported features are properly rejected."""
    
    def test_tools_with_complex_schema(self, integration_client):
        """Test that complex tool schemas are rejected."""
        complex_tool_request = {
            "model": "llama3.1-8B",
            "messages": [{"role": "user", "content": "What's the weather?"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather for a location",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "location": {
                                    "type": "string",
                                    "description": "The city name"
                                },
                                "unit": {
                                    "type": "string",
                                    "enum": ["celsius", "fahrenheit"]
                                }
                            },
                            "required": ["location"]
                        }
                    }
                }
            ],
            "tool_choice": "auto"
        }
        
        response = integration_client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer sk-test-key"},
            json=complex_tool_request
        )
        
        assert response.status_code == 400
        error_data = response.json()
        assert "detail" in error_data
        assert "tools" in error_data["detail"].lower() or "not supported" in error_data["detail"].lower()
    
    def test_json_schema_with_nested_objects(self, integration_client):
        """Test that complex JSON schemas are rejected."""
        complex_schema_request = {
            "model": "llama3.1-8B",
            "messages": [{"role": "user", "content": "Generate a user"}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                        "address": {
                            "type": "object",
                            "properties": {
                                "street": {"type": "string"},
                                "city": {"type": "string"}
                            }
                        }
                    },
                    "required": ["name", "age"]
                }
            }
        }
        
        response = integration_client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer sk-test-key"},
            json=complex_schema_request
        )
        
        assert response.status_code == 400
        error_data = response.json()
        assert "detail" in error_data
        assert "json" in error_data["detail"].lower() or "not supported" in error_data["detail"].lower()


class TestErrorPropagation:
    """Test that errors are properly propagated to clients."""
    
    def test_network_error_handling(self, integration_client):
        """Test handling of network errors from upstream."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            import requests
            mock_client.chat.side_effect = requests.ConnectionError("Connection refused")
            mock_get_client.return_value = mock_client
            
            response = integration_client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer sk-test-key"},
                json={
                    "model": "llama3.1-8B",
                    "messages": [{"role": "user", "content": "Hello"}]
                }
            )
            
            assert response.status_code == 502
            error_data = response.json()
            assert "detail" in error_data
            assert "upstream" in error_data["detail"].lower()
    
    def test_timeout_error_handling(self, integration_client):
        """Test handling of timeout errors from upstream."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            import requests
            mock_client.chat.side_effect = requests.Timeout("Request timed out")
            mock_get_client.return_value = mock_client
            
            response = integration_client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer sk-test-key"},
                json={
                    "model": "llama3.1-8B",
                    "messages": [{"role": "user", "content": "Hello"}]
                }
            )
            
            assert response.status_code == 502


class TestResponseConsistency:
    """Test that responses are consistent across different scenarios."""
    
    def test_response_id_format(self, integration_client):
        """Test that response IDs follow expected format."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Response"
            mock_response.stats = None
            mock_client.chat.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            response = integration_client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer sk-test-key"},
                json={
                    "model": "llama3.1-8B",
                    "messages": [{"role": "user", "content": "Test"}]
                }
            )
            
            data = response.json()
            assert data["id"].startswith("chatcmpl-")
            # ID should be alphanumeric with possible hyphens
            assert all(c.isalnum() or c == '-' for c in data["id"])
    
    def test_timestamp_recent(self, integration_client):
        """Test that timestamps are recent."""
        import time
        
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Response"
            mock_response.stats = None
            mock_client.chat.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            before = int(time.time())
            response = integration_client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer sk-test-key"},
                json={
                    "model": "llama3.1-8B",
                    "messages": [{"role": "user", "content": "Test"}]
                }
            )
            after = int(time.time())
            
            data = response.json()
            assert before <= data["created"] <= after
    
    def test_model_consistency(self, integration_client):
        """Test that requested model is returned in response."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Response"
            mock_response.stats = None
            mock_client.chat.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            response = integration_client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer sk-test-key"},
                json={
                    "model": "llama3.1-8B",
                    "messages": [{"role": "user", "content": "Test"}]
                }
            )
            
            data = response.json()
            assert data["model"] == "llama3.1-8B"
