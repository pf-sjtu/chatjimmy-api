# ChatJimmy API 限制与兼容性说明

本文档详细说明了 ChatJimmy OpenAI 兼容 API 的功能支持情况和已知限制。

## 概述

ChatJimmy 是一个非官方的 OpenAI 兼容 API 封装，底层使用 [chatjimmy.ai](https://chatjimmy.ai)（Taalas HC1 芯片上的 Llama 3.1 8B 模型）。

## 支持的端点

| 端点 | 方法 | 支持状态 | 说明 |
|------|------|----------|------|
| `/v1/chat/completions` | POST | ✅ 完全支持 | 支持流式和非流式响应 |
| `/GET /v1/models` | GET | ✅ 完全支持 | 返回可用的模型列表 |
| `/health` | GET | ✅ 完全支持 | 健康检查端点 |

## 请求参数支持情况

### Chat Completions 参数

| 参数 | 支持状态 | 实现方式 | 限制 |
|------|----------|----------|------|
| `model` | ✅ | 直接传递 | 仅支持 `llama3.1-8B` |
| `messages` | ✅ | 直接传递 | 最大 ~6,064 tokens |
| `stream` | ✅ | 模拟流式 | 实际为先完整接收再分块发送 |
| `temperature` | ⚠️ | 映射到 `top_k` | 不支持真正的 temperature |
| `top_p` | ❌ | 忽略 | 底层 API 不支持 |
| `top_k` | ✅ | 直接传递 | 默认 8，范围 1-40 |
| `max_tokens` | ⚠️ | 提示工程 | 无法强制执行限制 |
| `stop` | ❌ | 忽略 | 底层 API 不支持 |
| `tools` | ⚠️ | **环境开关** | 需设置 `ENABLE_TOOLS=true` |
| `tool_choice` | ⚠️ | **环境开关** | 需设置 `ENABLE_TOOLS=true` |
| `response_format` | ⚠️ | **环境开关** | 需设置 `ENABLE_JSON_MODE=true` |
| `user` | ✅ | 忽略 | 用于追踪，不传递给模型 |

## 实验性功能（需手动启用）

以下功能默认**禁用**，需要通过环境变量启用：

### Tool Use / Function Calling

**状态**: ⚠️ **实验性** - 需设置 `ENABLE_TOOLS=true`

**警告**:
- 通过提示词工程模拟，不是原生支持
- 可靠性无法保证
- 模型可能不遵循格式要求

**启用方式**:
```bash
export ENABLE_TOOLS=true
```

**使用示例**:
```python
from openai import OpenAI

client = OpenAI(
    base_url="https://your-api.onrender.com/v1",
    api_key="your-api-key",
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                },
                "required": ["location"]
            }
        }
    }
]

response = client.chat.completions.create(
    model="llama3.1-8B",
    messages=[{"role": "user", "content": "What's the weather in Paris?"}],
    tools=tools,
    tool_choice="auto",
)

# Check if model wants to call a tool
if response.choices[0].finish_reason == "tool_calls":
    tool_call = response.choices[0].message.tool_calls[0]
    print(f"Tool: {tool_call.function.name}")
    print(f"Arguments: {tool_call.function.arguments}")
```

**限制**:
- **可靠性不如原生支持**：模型可能不遵循格式要求
- **单次调用**：当前实现仅支持单次工具调用
- **无自动执行**：后端不会自动执行工具，仅返回调用请求
- **格式敏感**：依赖模型输出正确的 JSON 格式

### JSON Mode / Structured Outputs

**状态**: ⚠️ **实验性** - 需设置 `ENABLE_JSON_MODE=true`

**警告**:
- 通过提示词工程模拟
- 不保证输出一定是有效 JSON
- 无 Schema 验证

**启用方式**:
```bash
export ENABLE_JSON_MODE=true
```

**使用示例**:
```python
response = client.chat.completions.create(
    model="llama3.1-8B",
    messages=[{
        "role": "user",
        "content": "List 3 planets in our solar system"
    }],
    response_format={"type": "json_object"},
)

import json
try:
    data = json.loads(response.choices[0].message.content)
    print(data)
except json.JSONDecodeError:
    # Handle invalid JSON
    print("Model did not return valid JSON")
```

**限制**:
- **无 Schema 验证**：后端不验证输出是否符合 schema
- **无保证格式**：模型可能输出非 JSON 内容
- **无重试机制**：如果输出无效，不会自动重试

## 参数映射说明

### Temperature → Top-K 映射

由于底层 API 不支持 `temperature`，我们使用以下映射关系：

```python
top_k = max(1, min(40, int(temperature * 20)))
```

| Temperature | Top-K | 行为 |
|-------------|-------|------|
| 0.0 | 1 | 最确定性 |
| 0.5 | 10 | 中等随机性 |
| 1.0 | 20 | 较高随机性 |
| 2.0 | 40 | 最高随机性 |

## 模型能力

### 可用模型

| 模型 ID | 提供商 | 上下文长度 | 特点 |
|---------|--------|------------|------|
| `llama3.1-8B` | Taalas Inc. | ~6K tokens | HC1 芯片，~17K tokens/sec |

### 已知限制

1. **上下文长度限制**
   - 最大输入：~6,064 tokens（prefill）
   - 超过限制会返回空响应（HTTP 200，无内容）

2. **输出长度**
   - 无硬性限制
   - 典型输出：1,200 - 2,400 tokens
   - 通过 EOS token 自然停止

3. **响应速度**
   - 预填充：取决于输入长度
   - 解码：~17,000 tokens/sec（官方数据）

4. **并发限制**
   - 未观察到明确的速率限制
   - 测试过 20 并发 + 30 顺序请求

## 流式响应

### 实现方式

⚠️ **模拟流式**，不是真正的 SSE 流式。

由于底层 API 不支持真正的流式传输，我们采用以下策略：

1. 先完整接收上游响应
2. 按词（word）分块发送给客户端
3. 每块间隔 10ms 模拟流式效果

### 与真实流式的差异

| 特性 | 真实流式 | ChatJimmy 模拟 |
|------|----------|----------------|
| 首字节时间 | 立即 | 等待完整响应 |
| 内存占用 | 低 | 需要缓冲完整响应 |
| 取消支持 | 可中途取消 | 必须等待完整响应 |
| 错误处理 | 流中可报错 | 只能在开头/结尾报错 |

## 错误处理

### HTTP 状态码

| 状态码 | 场景 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数验证失败（如使用了未启用的功能） |
| 401 | API Key 无效或缺失 |
| 422 | 请求格式验证失败 |
| 502 | 上游 API 错误 |
| 500 | 内部服务器错误 |

### 错误响应格式

遵循 OpenAI 错误格式：

```json
{
  "error": {
    "message": "Error description",
    "type": "error_type",
    "param": null,
    "code": null
  }
}
```

### 常见错误

#### 功能未启用

```json
{
  "error": {
    "message": "Tool use (tools parameter) is not enabled. Set ENABLE_TOOLS=true to enable experimental tool use via prompt engineering. WARNING: This is simulated and may not work reliably.",
    "type": "invalid_request_error",
    "param": "tools",
    "code": null
  }
}
```

#### 空响应

**症状**：返回 200 但内容为空

**原因**：输入超过 ~6,064 tokens

**解决**：截断或压缩输入文本

## 与 OpenAI API 的兼容性对比

### 完全兼容

- 基本的聊天完成功能
- 模型列表获取
- 请求/响应格式结构
- 流式响应格式（SSE）
- 标准 HTTP 错误码

### 部分兼容

- **参数**：temperature 映射到 top_k
- **统计信息**：tokens 统计来自上游 API

### 实验性（需环境变量启用）

- ⚠️ `tools` - 工具调用（`ENABLE_TOOLS=true`）
- ⚠️ `tool_choice` - 工具选择（`ENABLE_TOOLS=true`）
- ⚠️ `response_format` (json_object/json_schema) - JSON 模式（`ENABLE_JSON_MODE=true`）

### 不支持（忽略参数）

- ❌ `top_p` - 核采样
- ❌ `stop` - 停止序列
- ❌ `max_tokens` - 无法强制执行
- ❌ `logprobs` - 对数概率
- ❌ `n` (n > 1) - 多个选择
- ❌ `presence_penalty` - 存在惩罚
- ❌ `frequency_penalty` - 频率惩罚
- ❌ `seed` - 随机种子

## 使用建议

### 适用场景

✅ **推荐使用**：
- 简单的对话应用
- 快速原型开发
- 低成本的 LLM 接入
- 对延迟不敏感的场景
- 实验性场景（启用实验性功能）

❌ **不推荐**：
- 需要保证可靠性的生产环境（使用实验性功能时）
- 需要严格 JSON Schema 验证的应用
- 复杂的多轮工具调用（使用实验性功能时）

### 迁移建议

从 OpenAI 迁移时：

1. **测试实验性功能**：在使用 `ENABLE_TOOLS` 或 `ENABLE_JSON_MODE` 前，充分测试可靠性
2. **处理失败情况**：准备解析错误或无效输出的回退逻辑
3. **调整温度**：可能需要重新调优 temperature 值
4. **监控输入长度**：确保不超过 6K tokens

## 故障排查

### 工具调用失败

**症状**：模型不返回预期的 JSON 格式

**原因**：提示词工程限制，模型未遵循格式

**解决**：
- 在系统提示中增加更多示例
- 简化工具描述
- 在后端添加输出验证和重试

### JSON 解析错误

**症状**：设置了 JSON 模式但返回非 JSON

**原因**：模型未遵循格式要求

**解决**：
- 始终使用 try/except 处理 JSON 解析
- 准备回退逻辑
- 使用更明确的提示

### 功能未启用错误

**症状**：返回 400 错误，提示功能未启用

**原因**：使用了实验性功能但未设置环境变量

**解决**：
```bash
export ENABLE_TOOLS=true
# 或
export ENABLE_JSON_MODE=true
```

## 相关链接

- [OpenAI API 文档](https://platform.openai.com/docs/api-reference)
- [chatjimmy.ai](https://chatjimmy.ai)
- [Taalas](https://taalas.com)
- [Llama 3.1 模型卡片](https://ai.meta.com/blog/meta-llama-3-1/)
