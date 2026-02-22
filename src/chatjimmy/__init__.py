from chatjimmy.client import (
    Attachment,
    ChatJimmy,
    ChatResponse,
    HealthStatus,
    Message,
    Model,
    Stats,
)

# Server components (optional import)
try:
    from chatjimmy.config import Settings, get_settings
    from chatjimmy.models import (
        ChatCompletionRequest,
        ChatCompletionResponse,
        ChatMessage,
        ModelInfo,
        ModelList,
    )
    
    __server_imports__ = [
        "Settings",
        "get_settings",
        "ChatCompletionRequest",
        "ChatCompletionResponse",
        "ChatMessage",
        "ModelInfo",
        "ModelList",
    ]
except ImportError:
    __server_imports__ = []

__all__ = [
    "Attachment",
    "ChatJimmy",
    "ChatResponse",
    "HealthStatus",
    "Message",
    "Model",
    "Stats",
    *__server_imports__,
]
