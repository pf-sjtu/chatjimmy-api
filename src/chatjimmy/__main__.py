"""Entry point for running the chatjimmy server."""

from __future__ import annotations

import sys

def main():
    """Run the chatjimmy API server."""
    try:
        import uvicorn
    except ImportError:
        print(
            "Error: Server dependencies not installed.\n"
            "Install with: pip install chatjimmy[server]",
            file=sys.stderr,
        )
        sys.exit(1)
    
    from chatjimmy.config import get_settings
    
    settings = get_settings()
    
    print(f"Starting ChatJimmy API server on {settings.host}:{settings.port}")
    print(f"Base URL: {settings.chatjimmy_base_url}")
    print(f"Log level: {settings.log_level}")
    
    uvicorn.run(
        "chatjimmy.server:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=False,
    )


if __name__ == "__main__":
    main()
