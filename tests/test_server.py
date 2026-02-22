"""Tests for chatjimmy server module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test /health endpoint."""
    
    def test_health_check_success(self, test_client):
        """Test health check when upstream is healthy."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            mock_health = MagicMock()
            mock_health.healthy = True
            mock_health.backend = "healthy"
            mock_health.timestamp = "2024-01-01T00:00:00Z"
            mock_client.health.return_value = mock_health
            mock_get_client.return_value = mock_client
            
            response = test_client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["healthy"] is True
            assert data["backend"] == "healthy"
    
    def test_health_check_unhealthy(self, test_client):
        """Test health check when upstream is unhealthy."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            mock_health = MagicMock()
            mock_health.healthy = False
            mock_health.backend = "unhealthy"
            mock_health.timestamp = "2024-01-01T00:00:00Z"
            mock_client.health.return_value = mock_health
            mock_get_client.return_value = mock_client
            
            response = test_client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert data["healthy"] is False
    
    def test_health_check_exception(self, test_client):
        """Test health check when upstream throws exception."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.health.side_effect = Exception("Connection failed")
            mock_get_client.return_value = mock_client
            
            response = test_client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert data["healthy"] is False


class TestModelsEndpoint:
    """Test /v1/models endpoint."""
    
    def test_list_models_success(self, test_client):
        """Test listing models successfully."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            mock_model = MagicMock()
            mock_model.id = "llama3.1-8B"
            mock_model.object = "model"
            mock_model.created = 0
            mock_model.owned_by = "Taalas Inc."
            mock_client.models.return_value = [mock_model]
            mock_get_client.return_value = mock_client
            
            response = test_client.get(
                "/v1/models",
                headers={"Authorization": "Bearer sk-test-key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["object"] == "list"
            assert len(data["data"]) == 1
            assert data["data"][0]["id"] == "llama3.1-8B"
            assert data["data"][0]["owned_by"] == "Taalas Inc."
    
    def test_list_models_fallback(self, test_client):
        """Test listing models falls back to default on error."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.models.side_effect = Exception("API error")
            mock_get_client.return_value = mock_client
            
            response = test_client.get(
                "/v1/models",
                headers={"Authorization": "Bearer sk-test-key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]) == 1
            assert data["data"][0]["id"] == "llama3.1-8B"


class TestChatCompletionsEndpoint:
    """Test /v1/chat/completions endpoint."""
    
    def test_chat_completion_success(self, test_client, valid_chat_request):
        """Test successful chat completion."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Hello! How can I help you?"
            mock_response.stats = MagicMock()
            mock_response.stats.prefill_tokens = 10
            mock_response.stats.decode_tokens = 20
            mock_response.stats.total_tokens = 30
            mock_response.stats.done_reason = "stop"
            mock_client.chat.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            response = test_client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer sk-test-key"},
                json=valid_chat_request,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["object"] == "chat.completion"
            assert data["model"] == "llama3.1-8B"
            assert len(data["choices"]) == 1
            assert data["choices"][0]["message"]["content"] == "Hello! How can I help you?"
            assert data["choices"][0]["finish_reason"] == "stop"
            assert data["usage"]["prompt_tokens"] == 10
            assert data["usage"]["completion_tokens"] == 20
            assert data["usage"]["total_tokens"] == 30
    
    def test_chat_completion_no_auth(self, test_client, valid_chat_request):
        """Test chat completion without API key when auth is required."""
        with patch("chatjimmy.config.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.api_key = "sk-test-key"
            mock_settings.cors_origins = ["*"]
            mock_get_settings.return_value = mock_settings
            
            response = test_client.post(
                "/v1/chat/completions",
                json=valid_chat_request,
            )
            
            assert response.status_code == 401
            assert "Authorization" in response.json()["detail"]
    
    def test_chat_completion_invalid_auth(self, test_client, valid_chat_request):
        """Test chat completion with invalid API key."""
        response = test_client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer wrong-key"},
            json=valid_chat_request,
        )
        
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
    
    def test_chat_completion_empty_messages(self, test_client):
        """Test chat completion with empty messages."""
        request_data = {
            "model": "llama3.1-8B",
            "messages": [],
        }
        
        response = test_client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer sk-test-key"},
            json=request_data,
        )
        
        assert response.status_code == 422
    
    def test_chat_completion_tools_not_supported(self, test_client):
        """Test that tools parameter is rejected."""
        request_data = {
            "model": "llama3.1-8B",
            "messages": [{"role": "user", "content": "Hello"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "description": "Get weather",
                        "parameters": {"type": "object", "properties": {}}
                    }
                }
            ]
        }
        
        response = test_client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer sk-test-key"},
            json=request_data,
        )
        
        assert response.status_code == 400
        assert "not supported" in response.json()["detail"].lower()
    
    def test_chat_completion_json_mode_not_supported(self, test_client):
        """Test that response_format json_object is rejected."""
        request_data = {
            "model": "llama3.1-8B",
            "messages": [{"role": "user", "content": "Hello"}],
            "response_format": {"type": "json_object"}
        }
        
        response = test_client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer sk-test-key"},
            json=request_data,
        )
        
        assert response.status_code == 400
        assert "not supported" in response.json()["detail"].lower()
    
    def test_chat_completion_json_schema_not_supported(self, test_client):
        """Test that response_format json_schema is rejected."""
        request_data = {
            "model": "llama3.1-8B",
            "messages": [{"role": "user", "content": "Hello"}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"type": "object"}
            }
        }
        
        response = test_client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer sk-test-key"},
            json=request_data,
        )
        
        assert response.status_code == 400
    
    def test_chat_completion_upstream_error(self, test_client, valid_chat_request):
        """Test chat completion when upstream API fails."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat.side_effect = Exception("Upstream API error")
            mock_get_client.return_value = mock_client
            
            response = test_client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer sk-test-key"},
                json=valid_chat_request,
            )
            
            assert response.status_code == 502
            assert "upstream" in response.json()["detail"].lower()


class TestStreamingChatCompletions:
    """Test streaming chat completions."""
    
    def test_chat_completion_streaming(self, test_client, valid_chat_request_streaming):
        """Test streaming chat completion."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            
            def mock_stream(*args, **kwargs):
                yield "Hello", None
                yield " ", None
                yield "world!", None
                stats = MagicMock()
                stats.prefill_tokens = 5
                stats.decode_tokens = 10
                stats.total_tokens = 15
                stats.done_reason = "stop"
                yield "", stats
            
            mock_client._chat_stream = mock_stream
            mock_get_client.return_value = mock_client
            
            response = test_client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer sk-test-key"},
                json=valid_chat_request_streaming,
            )
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream; charset=utf-8"
            
            # Parse SSE response
            content = response.content.decode()
            assert "data:" in content
            assert "[DONE]" in content


class TestParameterMapping:
    """Test parameter mapping between OpenAI and chatjimmy formats."""
    
    def test_temperature_to_top_k_mapping(self, test_client):
        """Test that temperature is mapped to top_k."""
        test_cases = [
            (0.0, 1),   # Minimum
            (0.5, 10),  # Middle
            (1.0, 20),  # Default-ish
            (2.0, 40),  # Maximum
            (3.0, 40),  # Clamped to max
        ]
        
        for temp, expected_top_k in test_cases:
            with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
                mock_client = MagicMock()
                mock_response = MagicMock()
                mock_response.text = "Response"
                mock_response.stats = None
                mock_client.chat.return_value = mock_response
                mock_get_client.return_value = mock_client
                
                request_data = {
                    "model": "llama3.1-8B",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "temperature": temp,
                }
                
                test_client.post(
                    "/v1/chat/completions",
                    headers={"Authorization": "Bearer sk-test-key"},
                    json=request_data,
                )
                
                call_args = mock_client.chat.call_args
                assert call_args[1]["top_k"] == expected_top_k, f"Failed for temperature={temp}"
    
    def test_explicit_top_k(self, test_client):
        """Test that explicit top_k is used when provided."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Response"
            mock_response.stats = None
            mock_client.chat.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            request_data = {
                "model": "llama3.1-8B",
                "messages": [{"role": "user", "content": "Hello"}],
                "temperature": 1.0,  # Would map to 20
                "top_k": 15,  # But explicit top_k should win
            }
            
            test_client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer sk-test-key"},
                json=request_data,
            )
            
            call_args = mock_client.chat.call_args
            assert call_args[1]["top_k"] == 15
    
    def test_system_prompt_extraction(self, test_client):
        """Test that system prompt is extracted from messages."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Response"
            mock_response.stats = None
            mock_client.chat.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            request_data = {
                "model": "llama3.1-8B",
                "messages": [
                    {"role": "system", "content": "You are helpful."},
                    {"role": "user", "content": "Hello"}
                ],
            }
            
            test_client.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer sk-test-key"},
                json=request_data,
            )
            
            call_args = mock_client.chat.call_args
            assert call_args[1]["system_prompt"] == "You are helpful."
            # User messages should be separate
            assert len(call_args[1]["messages"]) == 1
            assert call_args[1]["messages"][0]["role"] == "user"


class TestCORS:
    """Test CORS configuration."""
    
    def test_cors_headers(self, test_client):
        """Test that CORS headers are present."""
        response = test_client.options(
            "/v1/chat/completions",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            }
        )
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestErrorHandling:
    """Test error handling."""
    
    def test_generic_exception_handler(self, test_client):
        """Test that generic exceptions are handled."""
        with patch("chatjimmy.server.get_chatjimmy_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.models.side_effect = Exception("Unexpected error")
            mock_get_client.return_value = mock_client
            
            response = test_client.get("/v1/models", headers={"Authorization": "Bearer sk-test-key"})
            
            # Should not crash, should return 200 with fallback data
            assert response.status_code == 200
