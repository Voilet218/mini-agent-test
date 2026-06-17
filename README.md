
<img width="1500" height="1230" alt="image" src="https://github.com/user-attachments/assets/c56877a7-667c-4ef1-bec6-c601c4d3cfce" />

<img width="787" height="628" alt="image" src="https://github.com/user-attachments/assets/d4c15940-3b5c-478b-b81a-2efc8c2d05c0" />

# 🤖 Minimal Agent — 从零实现的最小可用 Agent

> 笔试题：不使用现成 Agent 框架，从零实现一个最小可用 Agent。
>
> **核心要求**: 多轮对话 + Session 维护 + 工具调用 + 跨轮次继续执行 + 真实 LLM API

---

## 🚀 快速开始

### 1. 配置 API 密钥

```bash
# 方式一：环境变量（推荐）
export LLM_API_KEY=sk-xxx
export LLM_BASE_URL=https://api.deepseek.com/v1   # 可选，默认 OpenAI
export LLM_MODEL=deepseek-chat                      # 可选，默认 gpt-4o-mini

# Windows CMD:
set LLM_API_KEY=sk-xxx
set LLM_BASE_URL=https://api.deepseek.com/v1
set LLM_MODEL=deepseek-chat

# Windows PowerShell:
$env:LLM_API_KEY="sk-xxx"
$env:LLM_BASE_URL="https://api.deepseek.com/v1"
$env:LLM_MODEL="deepseek-chat"
```

### 2. 运行

```bash
# 交互模式（推荐）
python main.py

# 单轮模式
python main.py --one-shot "1+1等于几？"

# 恢复历史会话
python main.py --session <session-id>

# 列出所有会话
python main.py --list-sessions
```

---

## 📦 内置工具

### 1. `calculator` — 计算器
安全数学表达式求值，支持四则运算和数学函数。

```python
calculator(expression="sqrt(144) + 3 * 7")
# → "sqrt(144) + 3 * 7 = 33.0"
```

### 2. `search` — 知识搜索
内置 Mock 知识库的搜索引擎，支持精确/模糊匹配。

```python
search(query="什么是agent")
# → "Agent（智能体）是一种能够感知环境并采取行动以实现目标的软件实体..."
```

### 3. `todo` — 待办管理
**跨轮次状态持久化的核心工具**。数据保存到 `todo_store.json`。

```python
todo(action="add", title="调研任务", description="Python异步框架")
# → ✅ 已创建任务 [12345678]: 调研任务

todo(action="list")
# → 📋 共 3 个任务

todo(action="update", id="12345678", status="in_progress")
# → ✅ 已更新任务 [12345678]: 调研任务 -> in_progress
```

### 4. `weather` — 天气查询
内置主要城市天气数据，未匹配时模拟生成。

```python
weather(city="北京")
# → "北京天气: 晴，25°C，湿度 40%，南风 2 级"
```

---

## 🏗️ 系统设计

### 整体架构

```
┌─────────────────────────────────────────────────────┐
│                    用户输入                           │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              AgentRuntime (ReAct 循环)                │
│                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────┐ │
│  │  LLM 推理 │──▶│ 判断决策 │──▶│ 直接回答 / 调用工具│ │
│  └──────────┘   └──────────┘   └────────┬─────────┘ │
│         ▲                                │           │
│         │                                ▼           │
│         │                       ┌──────────────────┐ │
│         │                       │  ToolRegistry     │ │
│         │                       │  ├ calculator     │ │
│         │                       │  ├ search         │ │
│         │                       │  ├ todo           │ │
│         │                       │  └ weather        │ │
│         │                       └────────┬─────────┘ │
│         │                                │           │
│         └────────────────────────────────┘           │
│                                                     │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              Session (持久化存储)                     │
│  ├ 消息历史 (messages)                               │
│  ├ 持久化上下文 (context)                             │
│  └ 元数据 (metadata)                                 │
└─────────────────────────────────────────────────────┘
```

### 核心循环 (ReAct)

Agent 的主循环实现在 `agent/runtime.py` 的 `chat()` 方法中：

```
第1步: 接收用户输入 → 追加到会话消息列表
第2步: 调用 LLM，传入消息历史和工具定义
第3步: 解析 LLM 响应
   ├─ 有工具调用 → 执行工具 → 结果追加回消息 → Agent循环轮次+1 → 回到第2步
   └─ 无工具调用 → 作为最终答案输出（不计入轮数）
第4步: 累计轮数 >= max_steps → 强制终止（不再执行新工具）
```

**关键语义**：`step` 仅统计「调用工具的 Agent 循环轮次」，LLM 直接给出最终答案不计入步数。
例如：Agent 调用 2 次工具后给出答案 → steps=2；直接回答（0 次工具）→ steps=0。

### 模块说明

| 模块 | 文件 | 职责 |
|------|------|------|
| **LLM 封装** | `agent/llm.py` | 纯标准库实现的 HTTP 客户端，兼容 OpenAI/DeepSeek 等 API |
| **工具系统** | `agent/tool_registry.py` | 工具定义、注册、调用、错误处理 |
| **会话管理** | `agent/session.py` | 会话创建、持久化、恢复、上下文跨轮次保持 |
| **核心运行时** | `agent/runtime.py` | ReAct 主循环、步数控制、异常处理、调用追踪 |
| **入口** | `main.py` | CLI 交互界面、会话管理命令 |

### 关键设计决策

#### 1. 零第三方依赖
所有功能使用 Python 标准库实现：`urllib.request` 调用 LLM API，`json` 序列化，`os` 文件管理。无需安装任何 pip 包。

#### 2. Session 持久化与跨轮次继续执行

**Architecture:**
- 每个会话保存为 `sessions/<id>.json` 文件，包含完整消息历史、上下文和元数据
- Todo 数据独立保存在 `todo_store.json`，与对话历史互补
- 持久化上下文 (`session.context`) 用于存放 Agent 需要跨轮次记住的结构化信息

**Cross-turn continuation 实现方式:**
- 第1轮：用户创建任务 → Agent 调用 `todo(action="add")` → 结果写入 `todo_store.json` → 存入会话消息历史
- 第2轮：用户问"上次的任务怎样" → Agent 从消息历史中读到上下文 → 调用 `todo(action="list")` → 读取 `todo_store.json` → 返回最新状态

这体现了两种记忆机制：
- **显式记忆**: 通过消息历史（LLM 自身上下文窗口）
- **隐式记忆**: 通过工具读取持久化存储（todo_store.json）

#### 3. Agent 循环轮数限制与异常处理
```python
max_steps=10  # 最大 Agent 循环轮数（工具调用轮次），防止无限循环
```
- **轮数语义**：`step` 仅统计 LLM 调用工具的轮次。LLM 直接给出最终答案不计入步数
- **达到上限**：Agent 在第 N 轮调用工具后若已达上限，不再继续执行新工具，直接终止
- LLM 调用失败 → 捕获 `LLMError` → 返回友好错误信息
- 工具执行异常 → `try/except` 包裹 → 返回 `[工具错误]` 前缀
- 参数解析失败 → JSON 解析异常处理
- 超时控制 → `request.urlopen(timeout=60)`

---

## 💡 跨轮次继续执行演示

```
第1轮: 用户 → "帮我创建一个调研任务：调研 Python 异步编程框架"
       Agent → 调用 todo(action="add", title="调研...")
       Agent → "✅ 已创建任务 [12345678]"

第2轮: 用户 → "我之前创建的任务完成了吗？"
       Agent → 从历史中识别是任务查询
       Agent → 调用 todo(action="list")
       Agent → "你之前的任务 [12345678] 状态为 pending..."

第3轮: 用户 → "标记为进行中，另外北京天气怎么样？"
       Agent → 调用 todo(action="update", id="12345678", status="in_progress")
       Agent → 调用 weather(city="北京")
       Agent → "已更新任务状态，北京今天晴 25°C..."
```

运行演示：
```bash
python examples/cross_turn_demo.py
```

---

## 📝 Memory 机制说明

### 召回时机

| 场景 | 召回方式 | 触发点 |
|------|---------|--------|
| 同一轮多次工具调用 | 消息历史 (messages) | LLM 收到上一步的工具执行结果 |
| 同会话多轮对话 | 消息历史 (messages) | 用户在同一 Session 中继续对话 |
| 跨轮次状态查询 | 工具读取 + 消息历史 | 用户提及"上次/之前创建的任务" |
| 程序重启后继续 | Session 文件 + Todo 文件 | 通过 `--session <id>` 恢复 |

### 放置方式

1. **消息历史 (`session.messages`)**:
   - 结构：`[system, user, assistant, tool, user, assistant, ...]`
   - 每次 LLM 调用传入完整历史（有截断保护）
   - 用于维持对话上下文和推理链条

2. **持久化上下文 (`session.context`)**:
   - `dict` 类型，保存在 `sessions/<id>.json` 中
   - 用于存放 Agent 需要跨轮保持的结构化数据
   - 通过 `session.update_context(key, value)` 写入

3. **工具数据存储 (`todo_store.json`)**:
   - 独立于对话的文件存储
   - Agent 通过工具调用读写，不直接访问
   - 体现"工具是 Agent 与外部世界的接口"的设计原则

---

## 📊 项目结构

```
minimal-agent/
├── main.py                     # CLI 入口
├── README.md                   # 本文件
├── requirements.txt            # 依赖（空）
├── .env.example                # 配置示例
│
├── agent/
│   ├── __init__.py
│   ├── llm.py                  # LLM API 封装（纯标准库）
│   ├── session.py              # 会话管理 + 持久化
│   ├── runtime.py              # Agent 核心 ReAct 循环
│   └── tool_registry.py        # 工具注册与调度
│
├── tools/
│   ├── __init__.py
│   ├── calculator.py           # 计算器工具
│   ├── search.py               # Mock 搜索工具
│   ├── todo.py                 # 待办管理（跨轮次持久化）
│   └── weather.py              # 天气查询工具
│
├── examples/
│   └── cross_turn_demo.py      # 跨轮次继续执行演示
│
├── sessions/                    # 会话持久化文件（运行时生成）
│   └── <session-id>.json
│
├── todo_store.json              # 待办数据（运行时生成）
└── knowledge_base.json          # 可选的自定义知识库
```

---

## ⚙️ 配置选项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `LLM_API_KEY` | — | **必需** API 密钥 |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | API 地址 |
| `LLM_MODEL` | `gpt-4o-mini` | 模型名称 |

支持的 API 提供商：
- **OpenAI**: `https://api.openai.com/v1`
- **DeepSeek**: `https://api.deepseek.com/v1`
- **月之暗面**: `https://api.moonshot.cn/v1`
- **智谱**: `https://open.bigmodel.cn/api/paas/v4`
- 任何兼容 OpenAI API 格式的服务

---

## 📐 技术要点总结

| 要求 | 实现 |
|------|------|
| 多轮对话 | Session 持久化消息历史，支持 `/switch` 切换 |
| 不依赖现成框架 | 纯标准库实现，零第三方依赖 |
| Agent 基本循环 | ReAct: 思考 → 行动 → 观察 → 继续 |
| 3+ 工具 | calculator, search, todo, weather |
| 最大 Agent 循环轮数 | `max_steps=10`。仅统计「调用工具」的轮次，最终答案不计入 |
| 异常处理 | LLM 错误 / 工具错误 / 参数错误 / 超时 |
| 调用追踪 | `trace` 数组记录每步工具名、参数、耗时、结果 |
| 跨轮次继续 | 会话持久化 + 工具状态持久化 |
| 真实 LLM API | OpenAI 兼容接口，标准 HTTP 请求 |

---

## 🔗 提交内容清单

- [x] 📦 代码: 本仓库完整源码
- [x] 📹 README: 包含运行方式、系统设计、Memory 机制说明
- [x] 📝 本 README 作为设计文档
- [x] 💡 示例演示脚本可用
