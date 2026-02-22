# ChatJimmy API 限制与兼容性说明

本文档详细说明了 ChatJimmy OpenAI 兼容 API 的功能支持情况和已知限制。

## 概述

ChatJimmy 是一个非官方的 OpenAI 兼容 API 封装，底层使用 [chatjimmy.ai](https://chatjimmy.ai)（Taalas HC1 芯片上的 Llama 3.1 8B 模型）。

## 支持的端点

| 端点 | 方法 | 支持状态 | 说明 |
|------|------|----------|------|
| `/v1/chat/completions` | POST | ✅ 完全支持 | 支持流式和非流式响应 |
| `/v1/models` | GET | ✅ 完全支持 | 返回可用的模型列表 |
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
| `tools` | ⚠️ | 提示工程模拟 | 见下方 Tool Use 说明 |
| `tool_choice` | ⚠️ | 提示工程模拟 | 仅支持 `auto`/`none`/`required` |
| `response_format` | ⚠️ | 提示工程模拟 | 见下方 JSON Mode 说明 |
| `user` | ✅ | 忽略 | 用于追踪，不传递给模型 |

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

## Tool Use / Function Calling

### 支持状态

⚠️ **通过提示工程模拟**，不是原生支持。

### 实现原理

当提供 `tools` 参数时，我们会：

1. 将工具定义转换为系统提示的一部分
2. 指示模型在需要调用工具时返回特定格式的 JSON

示例转换后的系统提示：

```
You have access to the following tools:

## get_weather
Description: Get the current weather for a location
Parameters: {"type": "object", "properties": {"location": {"type": "string"}}}

When you need to call a tool, respond in this JSON format:
{"tool": "tool_name", "arguments": {...}}

Use a tool only if it helps answer the user's question.
```

### 期望的响应格式

模型应该返回：

```json
{
  "tool": "get_weather",
  "arguments": {
    "location": "Paris"
  }
}
```

后端会将其解析为 OpenAI 格式的 `tool_calls`。

### 限制

- **可靠性不如原生支持**：模型可能不遵循格式要求
- **单次调用**：当前实现仅支持单次工具调用
- **无自动执行**：后端不会自动执行工具，仅返回调用请求
- **格式敏感**：依赖模型输出正确的 JSON 格式

### 最佳实践

1. 在系统提示中明确说明工具的使用场景
2. 对复杂参数提供详细的 description
3. 在后端验证和清理模型输出的参数
4. 准备处理模型未按预期格式输出的情况

## JSON Mode / Structured Outputs

### 支持状态

⚠️ **通过提示工程模拟**，不是原生支持。

### 实现原理

当设置 `response_format={"type": "json_object"}` 时：

1. 在系统提示中添加 JSON 格式要求
2. 如果提供了 `json_schema`，将其包含在提示中

示例：

```
You must respond in valid JSON format.

Follow this JSON schema:
{"type": "object", "properties": {"name": {"type": "string"}}}

Do not include any text outside the JSON object.
```

### 限制

- **无 Schema 验证**：后端不验证输出是否符合 schema
- **无保证格式**：模型可能输出非 JSON 内容
- **无重试机制**：如果输出无效，不会自动重试
- **注释问题**：模型可能在 JSON 中包含注释

### 与 OpenAI 的差异

| 特性 | OpenAI | ChatJimmy |
|------|--------|-----------|
| Schema 验证 | ✅ 严格验证 | ❌ 无验证 |
| 格式保证 | ✅ 保证有效 JSON | ⚠️ 尽力而为 |
| 重试机制 | ✅ 自动重试 | ❌ 无 |
| 错误处理 | ✅ 结构化错误 | ⚠️ 通用错误 |

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
| 401 | API Key 无效或缺失 |
| 422 | 请求参数验证失败 |
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

## 与 OpenAI API 的兼容性对比

### 完全兼容

- 基本的聊天完成功能
- 模型列表获取
- 请求/响应格式结构
- 流式响应格式（SSE）

### 部分兼容

- **参数**：temperature、max_tokens、tools、response_format 等通过提示工程模拟
- **功能**：tool use、JSON mode 通过提示工程实现
- **统计信息**：tokens 统计来自上游 API

### 不兼容

- **logprobs**：不支持
- **多个 choices**（n > 1）：不支持
- **presence/frequency penalty**：不支持
- **seed**：不支持
- **function_call**（旧版）：不支持
- **audio**：不支持
- **vision/image 输入**：不支持

## 使用建议

### 适用场景

✅ **推荐使用**：
- 简单的对话应用
- 快速原型开发
- 低成本的 LLM 接入
- 对延迟不敏感的场景

❌ **不推荐**：
- 需要严格 JSON Schema 验证的应用
- 复杂的多轮工具调用
- 生产环境中关键业务逻辑
- 需要高可靠性的场景

### 迁移建议

从 OpenAI 迁移时：

1. **测试工具调用**：验证提示工程是否满足需求
2. **处理 JSON 失败**：准备解析错误的回退逻辑
3. **调整温度**：可能需要重新调优 temperature 值
4. **监控输入长度**：确保不超过 6K tokens

## 故障排查

### 空响应问题

**症状**：返回 200 但内容为空

**原因**：输入超过 ~6,064 tokens

**解决**：截断或压缩输入文本

### 工具调用失败

**症状**：模型不返回预期的 JSON 格式

**原因**：提示工程限制

**解决**：
- 简化工具描述
- 在系统提示中增加示例
- 在后端添加输出验证和重试

### JSON 解析错误

**症状**：response_format 为 json_object 但返回非 JSON

**原因**：模型未遵循格式要求

**解决**：
- 在 prompt 中明确说明 JSON 格式
- 使用更简单的 schema
- 在后端添加 JSON 修复逻辑

## 相关链接

- [OpenAI API 文档](https://platform.openai.com/docs/api-reference)
- [chatjimmy.ai](https://chatjimmy.ai)
- [Taalas](https://taalas.com)
- [Llama 3.1 模型卡片](https://ai.meta.com/blog/meta-llama-3-1/)
