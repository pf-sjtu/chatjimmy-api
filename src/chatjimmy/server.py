"""FastAPI server for OpenAI-compatible chatjimmy API."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from chatjimmy.client import ChatJimmy, Stats, get_proxy_config
from chatjimmy.config import get_settings
from chatjimmy.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionStreamResponse,
    Choice,
    ChoiceDelta,
    ChoiceMessage,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    ModelInfo,
    ModelList,
    StreamingChoice,
    ToolCall,
    ToolCallFunction,
    Usage,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)

# Global client instance
_chatjimmy_client: ChatJimmy | None = None


def get_chatjimmy_client() -> ChatJimmy:
    """Get or create the ChatJimmy client instance."""
    global _chatjimmy_client
    if _chatjimmy_client is None:
        settings = get_settings()
        # Use proxy configuration from environment if available
        proxies = settings.proxies or get_proxy_config()
        _chatjimmy_client = ChatJimmy(
            base_url=settings.chatjimmy_base_url,
            timeout=settings.chatjimmy_timeout,
            proxies=proxies,
        )
    return _chatjimmy_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    settings = get_settings()
    logger.info(f"Starting server with base URL: {settings.chatjimmy_base_url}")
    if settings.proxies or get_proxy_config():
        logger.info("Proxy configuration detected")
    
    # Log feature flags
    if settings.enable_tools:
        logger.warning("ENABLE_TOOLS is set to true. Tool use is experimental and uses prompt engineering.")
    if settings.enable_json_mode:
        logger.warning("ENABLE_JSON_MODE is set to true. JSON mode is experimental and output may not be valid JSON.")
    
    yield
    # Shutdown
    logger.info("Shutting down server")


# Create FastAPI app
settings = get_settings()
app = FastAPI(
    title="ChatJimmy OpenAI Compatible API",
    description="OpenAI-compatible API wrapper for chatjimmy.ai (Taalas HC1 inference). "
                "NOTE: Tool use and JSON mode are experimental features disabled by default.",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> str:
    """Verify the API key from Authorization header."""
    settings = get_settings()
    
    # Skip auth if no API key is configured (not recommended for production)
    if not settings.api_key:
        logger.warning("No API key configured. Running in open mode.")
        return "anonymous"
    
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Support "Bearer <token>" format
    token = credentials.credentials
    if token != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle generic exceptions."""
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error=ErrorDetail(
                message=str(exc),
                type="internal_error",
            )
        ).model_dump(),
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        client = get_chatjimmy_client()
        health = client.health()
        return HealthResponse(
            status="ok" if health.healthy else "error",
            healthy=health.healthy,
            backend=health.backend,
            timestamp=health.timestamp,
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="error",
            healthy=False,
            backend=None,
            timestamp=None,
        )


@app.get("/v1/models", response_model=ModelList)
async def list_models(api_key: str = Depends(verify_api_key)):
    """List available models."""
    try:
        client = get_chatjimmy_client()
        models = client.models()
        
        return ModelList(
            data=[
                ModelInfo(
                    id=m.id,
                    object=m.object,
                    created=m.created,
                    owned_by=m.owned_by,
                )
                for m in models
            ]
        )
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        # Return default model if API fails
        return ModelList(
            data=[
                ModelInfo(
                    id="llama3.1-8B",
                    object="model",
                    created=0,
                    owned_by="Taalas Inc.",
                )
            ]
        )


def convert_stats_to_usage(stats: Stats | None) -> Usage:
    """Convert Stats to Usage format."""
    if stats is None:
        return Usage()
    return Usage(
        prompt_tokens=stats.prefill_tokens,
        completion_tokens=stats.decode_tokens,
        total_tokens=stats.total_tokens,
    )


def map_temperature_to_top_k(temperature: float | None, top_k: int | None) -> int:
    """Map OpenAI temperature to chatjimmy top_k parameter."""
    if top_k is not None:
        return top_k
    if temperature is None:
        return 8
    # Rough mapping: temperature 0-2 -> top_k 1-40
    # Lower temperature = more deterministic (lower top_k)
    # Higher temperature = more random (higher top_k)
    return max(1, min(40, int(temperature * 20)))


def parse_tool_calls_from_response(text: str) -> tuple[str, list[ToolCall] | None]:
    """Attempt to parse tool calls from response text.
    
    WARNING: This is experimental and may not work reliably.
    Only used when ENABLE_TOOLS=true.
    """
    # Try to find JSON tool call in the response
    try:
        # Look for patterns like {"tool": "name", "arguments": {...}}
        text = text.strip()
        if text.startswith("{") and text.endswith("}"):
            data = json.loads(text)
            if "tool" in data and "arguments" in data:
                tool_name = data["tool"]
                arguments = json.dumps(data["arguments"])
                return "", [
                    ToolCall(
                        function=ToolCallFunction(
                            name=tool_name,
                            arguments=arguments,
                        )
                    )
                ]
    except (json.JSONDecodeError, TypeError):
        pass
    
    return text, None


def create_chat_completion_response(
    request: ChatCompletionRequest,
    text: str,
    stats: Stats | None,
    enable_tools: bool = False,
) -> ChatCompletionResponse:
    """Create a chat completion response."""
    usage = convert_stats_to_usage(stats)
    
    # Check if response contains tool calls (only when tools are enabled)
    content, tool_calls = parse_tool_calls_from_response(text) if enable_tools else (text, None)
    
    # Determine finish reason
    finish_reason = "stop"
    if tool_calls:
        finish_reason = "tool_calls"
    elif stats and stats.done_reason == "length":
        finish_reason = "length"
    
    message = ChoiceMessage(
        role="assistant",
        content=content if content else None,
        tool_calls=tool_calls,
    )
    
    return ChatCompletionResponse(
        model=request.model,
        choices=[
            Choice(
                index=0,
                message=message,
                finish_reason=finish_reason,  # type: ignore
            )
        ],
        usage=usage,
    )


async def stream_chat_completion(
    request: ChatCompletionRequest,
    enable_tools: bool = False,
    enable_json_mode: bool = False,
) -> AsyncGenerator[str, None]:
    """Stream chat completion response."""
    client = get_chatjimmy_client()
    
    # Get system prompt with optional prompt engineering for enabled features
    system_prompt = request.build_system_prompt(
        enable_tools=enable_tools,
        enable_json_mode=enable_json_mode,
    )
    
    # Map parameters
    top_k = map_temperature_to_top_k(request.temperature, request.top_k)
    messages = request.get_chat_messages()
    
    try:
        # Collect full response first (chatjimmy doesn't truly stream)
        full_text = ""
        stats = None
        
        for chunk_text, chunk_stats in client._chat_stream(
            messages=messages,
            model=request.model,
            system_prompt=system_prompt,
            top_k=top_k,
            attachment=None,
        ):
            full_text += chunk_text
            if chunk_stats is not None:
                stats = chunk_stats
        
        # Simulate streaming by yielding word by word
        words = full_text.split(" ")
        response_id = f"chatcmpl-{hash(full_text) & 0xFFFFFF:06x}"
        created = int(time.time())
        
        # Yield initial chunk with role
        initial_chunk = ChatCompletionStreamResponse(
            id=response_id,
            model=request.model,
            created=created,
            choices=[
                StreamingChoice(
                    index=0,
                    delta=ChoiceDelta(role="assistant"),
                    finish_reason=None,
                )
            ],
        )
        yield f"data: {initial_chunk.model_dump_json(ensure_ascii=False)}\n\n"
        
        # Yield content chunks
        for i, word in enumerate(words):
            content = word + (" " if i < len(words) - 1 else "")
            chunk = ChatCompletionStreamResponse(
                id=response_id,
                model=request.model,
                created=created,
                choices=[
                    StreamingChoice(
                        index=0,
                        delta=ChoiceDelta(content=content),
                        finish_reason=None,
                    )
                ],
            )
            yield f"data: {chunk.model_dump_json(ensure_ascii=False)}\n\n"
            # Small delay to simulate streaming
            await asyncio.sleep(0.01)
        
        # Yield final chunk
        final_chunk = ChatCompletionStreamResponse(
            id=response_id,
            model=request.model,
            created=created,
            choices=[
                StreamingChoice(
                    index=0,
                    delta=ChoiceDelta(),
                    finish_reason="stop",
                )
            ],
        )
        yield f"data: {final_chunk.model_dump_json(ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "streaming_error",
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
async def create_chat_completion(
    request_data: dict,
    api_key: str = Depends(verify_api_key),
):
    """Create a chat completion."""
    settings = get_settings()
    
    try:
        # Create validation context with feature flags
        validation_context = {
            'enable_tools': settings.enable_tools,
            'enable_json_mode': settings.enable_json_mode,
        }
        
        # Validate and create request object with context
        request = ChatCompletionRequest.model_validate(
            request_data,
            context=validation_context,
        )
        
        if request.stream:
            # Return streaming response
            return StreamingResponse(
                stream_chat_completion(
                    request,
                    enable_tools=settings.enable_tools,
                    enable_json_mode=settings.enable_json_mode,
                ),
                media_type="text/event-stream",
            )
        else:
            # Return non-streaming response
            client = get_chatjimmy_client()
            
            # Get system prompt with optional prompt engineering for enabled features
            system_prompt = request.build_system_prompt(
                enable_tools=settings.enable_tools,
                enable_json_mode=settings.enable_json_mode,
            )
            
            # Map parameters
            top_k = map_temperature_to_top_k(request.temperature, request.top_k)
            messages = request.get_chat_messages()
            
            # Make the request
            response = client.chat(
                messages=messages,
                model=request.model,
                system_prompt=system_prompt,
                top_k=top_k,
                attachment=None,
            )
            
            return create_chat_completion_response(
                request=request,
                text=response.text,
                stats=response.stats,
                enable_tools=settings.enable_tools,
            )
    
    except HTTPException:
        raise
    except ValueError as e:
        # Handle validation errors (e.g., disabled features)
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Chat completion failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream API error: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "chatjimmy.server:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )
