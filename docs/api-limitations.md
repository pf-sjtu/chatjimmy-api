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
| `tools` | ❌ | **禁用** | 底层 API 不支持原生工具调用 |
| `tool_choice` | ❌ | **禁用** | 底层 API 不支持原生工具调用 |
| `response_format` | ❌ | **禁用** | 底层 API 不支持结构化输出 |
| `user` | ✅ | 忽略 | 用于追踪，不传递给模型 |

### ⚠️ 重要：不支持的功能

以下 OpenAI API 功能**明确禁用**，如果使用将返回 400 错误：

#### 1. Tool Use / Function Calling (`tools`, `tool_choice`)

**状态**: ❌ **不支持**

**原因**: 
- chatjimmy.ai API 底层模型（Llama 3.1 8B on Taalas HC1）不支持原生工具调用
- 通过提示词工程模拟工具调用不可靠，不符合 OpenAI API 标准行为
- 模型可能不遵循提示格式，导致不可预期的输出

**替代方案**:
```python
# 不要在请求中使用 tools 参数
# 而是在系统提示中描述工具，并在应用层解析响应

system_prompt = """You have access to a weather tool. 
If the user asks about weather, respond with:
TOOL_CALL: get_weather(location=<location>)

Otherwise respond normally."""

response = client.chat.completions.create(
    model="llama3.1-8B",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "What's the weather in Paris?"}
    ]
)

# 在应用层解析响应
if "TOOL_CALL:" in response.choices[0].message.content:
    # 解析工具调用并执行
    pass
```

#### 2. JSON Mode / Structured Outputs (`response_format`)

**状态**: ❌ **不支持**

**原因**:
- chatjimmy.ai API 不提供 JSON 模式保证
- 模型可能输出非 JSON 内容，即使要求 JSON 格式
- 没有内置的 JSON Schema 验证

**替代方案**:
```python
# 不要在请求中使用 response_format 参数
# 而是在提示中要求 JSON 格式，并在应用层解析和验证

system_prompt = """You must respond in valid JSON format only.
Do not include any text outside the JSON object."""

response = client.chat.completions.create(
    model="llama3.1-8B",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "List 3 planets"}
    ]
)

# 在应用层解析和验证 JSON
import json
try:
    data = json.loads(response.choices[0].message.content)
except json.JSONDecodeError:
    # 处理解析错误
    pass
```

### 参数映射说明

#### Temperature → Top-K 映射

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
| 400 | 请求参数验证失败（如使用了不支持的功能） |
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

#### 使用了不支持的功能

```json
{
  "error": {
    "message": "Tool use (tools parameter) is not supported by the chatjimmy.ai API. The underlying model (Llama 3.1 8B on Taalas HC1) does not support native function calling. Please implement tool calling logic in your application code instead.",
    "type": "invalid_request_error",
    "param": "tools",
    "code": null
  }
}
```

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

### 明确禁用（返回 400 错误）

- ❌ `tools` - 工具调用
- ❌ `tool_choice` - 工具选择
- ❌ `response_format` (json_object/json_schema) - JSON 模式

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
- 不需要工具调用的应用

❌ **不推荐**：
- 需要原生工具调用的应用
- 需要保证 JSON 输出的应用
- 生产环境中关键业务逻辑
- 需要高可靠性的场景

### 迁移建议

从 OpenAI 迁移时：

1. **移除工具调用代码**：
   ```python
   # 替换这样
   response = client.chat.completions.create(
       model="gpt-4",
       messages=messages,
       tools=tools,  # ❌ 不支持
   )
   
   # 改为这样
   response = client.chat.completions.create(
       model="llama3.1-8B",
       messages=messages_with_tool_description,  # ✅ 在提示中描述工具
   )
   # 然后在应用层解析响应
   ```

2. **处理 JSON 输出**：
   ```python
   # 替换这样
   response = client.chat.completions.create(
       model="gpt-4",
       messages=messages,
       response_format={"type": "json_object"},  # ❌ 不支持
   )
   
   # 改为这样
   response = client.chat.completions.create(
       model="llama3.1-8B",
       messages=messages_with_json_instruction,  # ✅ 在提示中要求 JSON
   )
   # 然后在应用层解析和验证 JSON
   ```

3. **调整温度**：可能需要重新调优 temperature 值
4. **监控输入长度**：确保不超过 6K tokens

## 故障排查

### 空响应问题

**症状**：返回 200 但内容为空

**原因**：输入超过 ~6,064 tokens

**解决**：截断或压缩输入文本

### 400 Bad Request - 不支持的功能

**症状**：请求返回 400 错误，提示功能不支持

**原因**：使用了 `tools`、`tool_choice` 或 `response_format` 参数

**解决**：从请求中移除这些参数，在应用层实现相应逻辑

### 502 Bad Gateway

**症状**：返回 502 错误

**原因**：上游 chatjimmy.ai 服务不可用或网络问题

**解决**：检查代理设置，稍后重试

## 相关链接

- [OpenAI API 文档](https://platform.openai.com/docs/api-reference)
- [chatjimmy.ai](https://chatjimmy.ai)
- [Taalas](https://taalas.com)
- [Llama 3.1 模型卡片](https://ai.meta.com/blog/meta-llama-3-1/)
