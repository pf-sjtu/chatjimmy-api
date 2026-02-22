"""Tests for chatjimmy models module."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from chatjimmy.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Choice,
    ChoiceDelta,
    ChoiceMessage,
    ErrorDetail,
    ErrorResponse,
    FunctionDefinition,
    HealthResponse,
    ModelInfo,
    ModelList,
    ResponseFormat,
    StreamingChoice,
    ToolCall,
    ToolCallFunction,
    ToolFunction,
    Usage,
)


class TestChatMessage:
    """Test ChatMessage model."""
    
    def test_valid_message(self):
        """Test creating a valid message."""
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
    
    def test_system_message(self):
        """Test creating a system message."""
        msg = ChatMessage(role="system", content="You are helpful.")
        assert msg.role == "system"
        assert msg.content == "You are helpful."
    
    def test_assistant_message(self):
        """Test creating an assistant message."""
        msg = ChatMessage(role="assistant", content="I can help!")
        assert msg.role == "assistant"
    
    def test_tool_message(self):
        """Test creating a tool message."""
        msg = ChatMessage(
            role="tool",
            content="Tool result",
            tool_call_id="call_123"
        )
        assert msg.role == "tool"
        assert msg.tool_call_id == "call_123"
    
    def test_invalid_role(self):
        """Test that invalid role is rejected."""
        with pytest.raises(ValidationError):
            ChatMessage(role="invalid", content="Hello")
    
    def test_message_with_tool_calls(self):
        """Test message with tool calls."""
        tool_call = ToolCall(
            function=ToolCallFunction(name="get_weather", arguments='{"location": "Paris"}')
        )
        msg = ChatMessage(
            role="assistant",
            content=None,
            tool_calls=[tool_call]
        )
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].function.name == "get_weather"


class TestChatCompletionRequest:
    """Test ChatCompletionRequest model."""
    
    def test_valid_request(self):
        """Test creating a valid request."""
        request = ChatCompletionRequest(
            model="llama3.1-8B",
            messages=[ChatMessage(role="user", content="Hello")],
        )
        assert request.model == "llama3.1-8B"
        assert len(request.messages) == 1
    
    def test_default_values(self):
        """Test default values."""
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
        )
        assert request.model == "llama3.1-8B"
        assert request.stream is False
        assert request.top_k == 8
    
    def test_temperature_validation(self):
        """Test temperature validation."""
        # Valid temperatures
        ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            temperature=0.5,
        )
        ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            temperature=2.0,
        )
        
        # Invalid temperatures
        with pytest.raises(ValidationError):
            ChatCompletionRequest(
                messages=[ChatMessage(role="user", content="Hello")],
                temperature=3.0,  # Too high
            )
        with pytest.raises(ValidationError):
            ChatCompletionRequest(
                messages=[ChatMessage(role="user", content="Hello")],
                temperature=-0.5,  # Negative
            )
    
    def test_tools_rejected(self):
        """Test that tools parameter is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChatCompletionRequest(
                model="llama3.1-8B",
                messages=[ChatMessage(role="user", content="Hello")],
                tools=[
                    ToolFunction(
                        function=FunctionDefinition(
                            name="get_weather",
                            description="Get weather",
                            parameters={}
                        )
                    )
                ]
            )
        assert "not supported" in str(exc_info.value).lower()
    
    def test_tool_choice_rejected(self):
        """Test that tool_choice parameter is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChatCompletionRequest(
                model="llama3.1-8B",
                messages=[ChatMessage(role="user", content="Hello")],
                tool_choice="auto"
            )
        assert "not supported" in str(exc_info.value).lower()
    
    def test_tool_choice_none_allowed(self):
        """Test that tool_choice='none' is allowed."""
        # This should not raise an error
        request = ChatCompletionRequest(
            model="llama3.1-8B",
            messages=[ChatMessage(role="user", content="Hello")],
            tool_choice="none"
        )
        assert request.tool_choice == "none"
    
    def test_response_format_json_object_rejected(self):
        """Test that json_object response format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChatCompletionRequest(
                model="llama3.1-8B",
                messages=[ChatMessage(role="user", content="Hello")],
                response_format=ResponseFormat(type="json_object")
            )
        assert "not supported" in str(exc_info.value).lower()
    
    def test_response_format_json_schema_rejected(self):
        """Test that json_schema response format is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ChatCompletionRequest(
                model="llama3.1-8B",
                messages=[ChatMessage(role="user", content="Hello")],
                response_format=ResponseFormat(
                    type="json_schema",
                    json_schema={"type": "object"}
                )
            )
        assert "not supported" in str(exc_info.value).lower()
    
    def test_response_format_text_allowed(self):
        """Test that text response format is allowed."""
        # This should not raise an error
        request = ChatCompletionRequest(
            model="llama3.1-8B",
            messages=[ChatMessage(role="user", content="Hello")],
            response_format=ResponseFormat(type="text")
        )
        assert request.response_format.type == "text"
    
    def test_get_system_prompt(self):
        """Test extracting system prompt."""
        request = ChatCompletionRequest(
            messages=[
                ChatMessage(role="system", content="You are helpful."),
                ChatMessage(role="user", content="Hello"),
            ]
        )
        assert request.get_system_prompt() == "You are helpful."
    
    def test_get_system_prompt_none(self):
        """Test extracting system prompt when none exists."""
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")]
        )
        assert request.get_system_prompt() == ""
    
    def test_get_chat_messages(self):
        """Test getting chat messages (excluding system)."""
        request = ChatCompletionRequest(
            messages=[
                ChatMessage(role="system", content="You are helpful."),
                ChatMessage(role="user", content="Hello"),
                ChatMessage(role="assistant", content="Hi!"),
            ]
        )
        chat_messages = request.get_chat_messages()
        assert len(chat_messages) == 2
        assert chat_messages[0]["role"] == "user"
        assert chat_messages[1]["role"] == "assistant"
    
    def test_build_system_prompt(self):
        """Test building system prompt."""
        request = ChatCompletionRequest(
            messages=[
                ChatMessage(role="system", content="You are helpful."),
                ChatMessage(role="user", content="Hello"),
            ]
        )
        assert request.build_system_prompt() == "You are helpful."
    
    def test_build_system_prompt_no_system(self):
        """Test building system prompt when none exists."""
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")]
        )
        assert request.build_system_prompt() == ""


class TestChatCompletionResponse:
    """Test ChatCompletionResponse model."""
    
    def test_response_creation(self):
        """Test creating a response."""
        response = ChatCompletionResponse(
            model="llama3.1-8B",
            choices=[
                Choice(
                    index=0,
                    message=ChoiceMessage(content="Hello!"),
                    finish_reason="stop",
                )
            ],
            usage=Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        )
        assert response.object == "chat.completion"
        assert response.model == "llama3.1-8B"
        assert len(response.choices) == 1
        assert response.choices[0].message.content == "Hello!"
    
    def test_auto_generated_id(self):
        """Test that ID is auto-generated."""
        response = ChatCompletionResponse(
            model="llama3.1-8B",
            choices=[],
            usage=Usage(),
        )
        assert response.id.startswith("chatcmpl-")
    
    def test_auto_generated_created(self):
        """Test that created timestamp is auto-generated."""
        import time
        before = int(time.time())
        response = ChatCompletionResponse(
            model="llama3.1-8B",
            choices=[],
            usage=Usage(),
        )
        after = int(time.time())
        assert before <= response.created <= after


class TestUsage:
    """Test Usage model."""
    
    def test_usage_creation(self):
        """Test creating usage stats."""
        usage = Usage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )
        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 20
        assert usage.total_tokens == 30
    
    def test_default_usage(self):
        """Test default usage values."""
        usage = Usage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0


class TestChoiceModels:
    """Test choice-related models."""
    
    def test_choice_message(self):
        """Test ChoiceMessage."""
        msg = ChoiceMessage(content="Hello", role="assistant")
        assert msg.content == "Hello"
        assert msg.role == "assistant"
    
    def test_choice(self):
        """Test Choice."""
        choice = Choice(
            index=0,
            message=ChoiceMessage(content="Hello"),
            finish_reason="stop",
        )
        assert choice.index == 0
        assert choice.finish_reason == "stop"
    
    def test_choice_delta(self):
        """Test ChoiceDelta."""
        delta = ChoiceDelta(content="Hello", role="assistant")
        assert delta.content == "Hello"
        assert delta.role == "assistant"
    
    def test_streaming_choice(self):
        """Test StreamingChoice."""
        choice = StreamingChoice(
            index=0,
            delta=ChoiceDelta(content="Hello"),
            finish_reason=None,
        )
        assert choice.index == 0
        assert choice.delta.content == "Hello"


class TestModelInfo:
    """Test ModelInfo model."""
    
    def test_model_info_creation(self):
        """Test creating model info."""
        model = ModelInfo(
            id="llama3.1-8B",
            created=0,
            owned_by="Taalas Inc.",
        )
        assert model.id == "llama3.1-8B"
        assert model.object == "model"
        assert model.owned_by == "Taalas Inc."
    
    def test_default_owned_by(self):
        """Test default owned_by value."""
        model = ModelInfo(id="test-model")
        assert model.owned_by == "Taalas Inc."


class TestModelList:
    """Test ModelList model."""
    
    def test_model_list_creation(self):
        """Test creating model list."""
        model_list = ModelList(
            data=[
                ModelInfo(id="llama3.1-8B"),
            ]
        )
        assert model_list.object == "list"
        assert len(model_list.data) == 1


class TestErrorModels:
    """Test error models."""
    
    def test_error_detail(self):
        """Test ErrorDetail."""
        error = ErrorDetail(
            message="An error occurred",
            type="invalid_request_error",
            param="model",
            code="model_not_found",
        )
        assert error.message == "An error occurred"
        assert error.type == "invalid_request_error"
        assert error.param == "model"
    
    def test_error_response(self):
        """Test ErrorResponse."""
        error_response = ErrorResponse(
            error=ErrorDetail(message="Error", type="test_error")
        )
        assert error_response.error.message == "Error"


class TestHealthResponse:
    """Test HealthResponse model."""
    
    def test_health_response(self):
        """Test creating health response."""
        health = HealthResponse(
            status="ok",
            healthy=True,
            backend="healthy",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert health.status == "ok"
        assert health.healthy is True
        assert health.backend == "healthy"


class TestToolModels:
    """Test tool-related models (for compatibility)."""
    
    def test_function_definition(self):
        """Test FunctionDefinition."""
        func = FunctionDefinition(
            name="get_weather",
            description="Get the weather",
            parameters={"type": "object", "properties": {}},
        )
        assert func.name == "get_weather"
        assert func.description == "Get the weather"
    
    def test_tool_function(self):
        """Test ToolFunction."""
        tool = ToolFunction(
            function=FunctionDefinition(
                name="get_weather",
                description="Get weather",
            )
        )
        assert tool.type == "function"
        assert tool.function.name == "get_weather"
    
    def test_tool_call(self):
        """Test ToolCall."""
        tool_call = ToolCall(
            function=ToolCallFunction(
                name="get_weather",
                arguments='{"location": "Paris"}',
            )
        )
        assert tool_call.type == "function"
        assert tool_call.function.name == "get_weather"
        assert tool_call.id.startswith("call_")


class TestResponseFormat:
    """Test ResponseFormat model."""
    
    def test_text_format(self):
        """Test text response format."""
        fmt = ResponseFormat(type="text")
        assert fmt.type == "text"
        assert fmt.json_schema is None
    
    def test_json_object_format(self):
        """Test json_object response format."""
        fmt = ResponseFormat(type="json_object")
        assert fmt.type == "json_object"
    
    def test_json_schema_format(self):
        """Test json_schema response format."""
        fmt = ResponseFormat(
            type="json_schema",
            json_schema={"type": "object", "properties": {}},
        )
        assert fmt.type == "json_schema"
        assert "properties" in fmt.json_schema
