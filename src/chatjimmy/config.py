"""Configuration management for chatjimmy API server."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Key (optional for development, required for production)
    api_key: str | None = Field(
        default=None,
        description="API key for authenticating client requests. If not set, the API will be open (not recommended for production)",
    )

    # ChatJimmy API settings
    chatjimmy_base_url: str = Field(
        default="https://chatjimmy.ai",
        description="Base URL for chatjimmy.ai API",
    )
    chatjimmy_timeout: int = Field(
        default=30,
        description="Request timeout in seconds",
    )

    # Feature flags for experimental features
    # WARNING: These features use prompt engineering and do not guarantee reliable results
    enable_tools: bool = Field(
        default=False,
        description="Enable Tool Use / Function Calling via prompt engineering. WARNING: This is simulated and may not work reliably.",
    )
    enable_json_mode: bool = Field(
        default=False,
        description="Enable JSON Mode / Structured Outputs via prompt engineering. WARNING: This is simulated and output may not be valid JSON.",
    )

    # Server settings
    port: int = Field(default=8000, description="Port to run the server on")
    host: str = Field(default="0.0.0.0", description="Host to bind the server to")
    log_level: str = Field(default="info", description="Logging level")

    # CORS settings
    allowed_origins: str = Field(
        default="*",
        description="Comma-separated list of allowed CORS origins",
    )

    # Proxy settings (optional)
    http_proxy: str | None = Field(default=None, description="HTTP proxy URL")
    https_proxy: str | None = Field(default=None, description="HTTPS proxy URL")

    @property
    def cors_origins(self) -> list[str]:
        """Get list of allowed CORS origins."""
        if self.allowed_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def proxies(self) -> dict[str, str] | None:
        """Get proxy configuration for requests."""
        proxies = {}
        if self.http_proxy:
            proxies["http"] = self.http_proxy
        if self.https_proxy:
            proxies["https"] = self.https_proxy
        return proxies if proxies else None


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
