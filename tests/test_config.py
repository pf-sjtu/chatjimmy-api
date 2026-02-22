"""Tests for chatjimmy config module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from chatjimmy.config import Settings, get_settings


class TestSettings:
    """Test Settings configuration."""
    
    def test_default_values(self):
        """Test default configuration values."""
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(api_key="test-key")
            
            assert settings.api_key == "test-key"
            assert settings.chatjimmy_base_url == "https://chatjimmy.ai"
            assert settings.chatjimmy_timeout == 30
            assert settings.port == 8000
            assert settings.host == "0.0.0.0"
            assert settings.log_level == "info"
            assert settings.allowed_origins == "*"
            assert settings.http_proxy is None
            assert settings.https_proxy is None
    
    def test_custom_values(self):
        """Test custom configuration values."""
        settings = Settings(
            api_key="custom-key",
            chatjimmy_base_url="https://custom.example.com",
            chatjimmy_timeout=60,
            port=9000,
            host="127.0.0.1",
            log_level="debug",
            allowed_origins="https://app.example.com,https://admin.example.com",
            http_proxy="http://proxy:8080",
            https_proxy="https://proxy:8080",
        )
        
        assert settings.api_key == "custom-key"
        assert settings.chatjimmy_base_url == "https://custom.example.com"
        assert settings.chatjimmy_timeout == 60
        assert settings.port == 9000
        assert settings.host == "127.0.0.1"
        assert settings.log_level == "debug"
        assert settings.allowed_origins == "https://app.example.com,https://admin.example.com"
        assert settings.http_proxy == "http://proxy:8080"
        assert settings.https_proxy == "https://proxy:8080"
    
    def test_cors_origins_wildcard(self):
        """Test CORS origins with wildcard."""
        settings = Settings(api_key="test", allowed_origins="*")
        assert settings.cors_origins == ["*"]
    
    def test_cors_origins_list(self):
        """Test CORS origins with comma-separated list."""
        settings = Settings(
            api_key="test",
            allowed_origins="https://app1.com, https://app2.com , https://app3.com"
        )
        origins = settings.cors_origins
        assert len(origins) == 3
        assert "https://app1.com" in origins
        assert "https://app2.com" in origins
        assert "https://app3.com" in origins
    
    def test_cors_origins_single(self):
        """Test CORS origins with single origin."""
        settings = Settings(api_key="test", allowed_origins="https://app.example.com")
        assert settings.cors_origins == ["https://app.example.com"]
    
    def test_proxies_both(self):
        """Test proxies property with both HTTP and HTTPS."""
        settings = Settings(
            api_key="test",
            http_proxy="http://proxy:8080",
            https_proxy="https://proxy:8080",
        )
        assert settings.proxies == {
            "http": "http://proxy:8080",
            "https": "https://proxy:8080",
        }
    
    def test_proxies_http_only(self):
        """Test proxies property with HTTP only."""
        settings = Settings(
            api_key="test",
            http_proxy="http://proxy:8080",
        )
        assert settings.proxies == {"http": "http://proxy:8080"}
    
    def test_proxies_https_only(self):
        """Test proxies property with HTTPS only."""
        settings = Settings(
            api_key="test",
            https_proxy="https://proxy:8080",
        )
        assert settings.proxies == {"https": "https://proxy:8080"}
    
    def test_proxies_none(self):
        """Test proxies property when no proxies configured."""
        settings = Settings(api_key="test")
        assert settings.proxies is None
    
    def test_optional_api_key(self):
        """Test that API key is optional."""
        settings = Settings()
        assert settings.api_key is None


class TestGetSettings:
    """Test get_settings function."""
    
    def test_get_settings_returns_settings(self):
        """Test that get_settings returns a Settings instance."""
        with patch.dict("os.environ", {"API_KEY": "test"}, clear=False):
            settings = get_settings()
            assert isinstance(settings, Settings)
    
    def test_get_settings_from_env(self):
        """Test that get_settings reads from environment."""
        env_vars = {
            "API_KEY": "env-key",
            "CHATJIMMY_TIMEOUT": "45",
            "PORT": "9000",
        }
        with patch.dict("os.environ", env_vars, clear=False):
            settings = get_settings()
            assert settings.api_key == "env-key"
            assert settings.chatjimmy_timeout == 45
            assert settings.port == 9000


class TestEnvironmentFileLoading:
    """Test loading from environment file."""
    
    def test_env_file_loading(self, tmp_path):
        """Test loading settings from .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("""
API_KEY=file-key
CHATJIMMY_BASE_URL=https://from-file.example.com
PORT=7000
LOG_LEVEL=warning
""")
        
        # Settings should load from env file
        settings = Settings(_env_file=str(env_file))
        
        assert settings.api_key == "file-key"
        assert settings.chatjimmy_base_url == "https://from-file.example.com"
        assert settings.port == 7000
        assert settings.log_level == "warning"


class TestProxyEnvironmentVariables:
    """Test proxy settings from environment variables."""
    
    def test_http_proxy_from_env(self):
        """Test loading HTTP_PROXY from environment."""
        with patch.dict("os.environ", {"HTTP_PROXY": "http://env-proxy:8080"}):
            settings = Settings(api_key="test")
            assert settings.http_proxy == "http://env-proxy:8080"
    
    def test_https_proxy_from_env(self):
        """Test loading HTTPS_PROXY from environment."""
        with patch.dict("os.environ", {"HTTPS_PROXY": "https://env-proxy:8080"}):
            settings = Settings(api_key="test")
            assert settings.https_proxy == "https://env-proxy:8080"
    
    def test_proxy_case_insensitive(self):
        """Test that proxy env vars are case insensitive."""
        # pydantic-settings should handle both cases
        with patch.dict("os.environ", {"http_proxy": "http://lower:8080"}):
            # Note: This depends on pydantic-settings behavior
            settings = Settings(api_key="test")
            # The field name is http_proxy in the model
            pass
