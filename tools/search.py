"""搜索工具 - Mock 实现"""

import json
import os
from agent.tool_registry import Tool

# Mock 知识库
_KNOWLEDGE_BASE: dict[str, str] = {
    "python": (
        "Python 是一种高级编程语言，由 Guido van Rossum 于 1991 年创建。"
        "它以简洁的语法和强大的标准库著称，广泛应用于 Web 开发、数据科学、AI 等领域。"
    ),
    "什么是 agent": (
        "Agent（智能体）是一种能够感知环境并采取行动以实现目标的软件实体。"
        "在 AI 领域，Agent 通常指能够使用 LLM 进行推理、调用工具、"
        "并与环境交互的自主系统。典型架构包括：感知 → 推理 → 行动 → 观察循环。"
    ),
    "capital of france": "The capital of France is Paris.",
    "中国的首都是": "中国的首都是北京。",
    "太阳系行星": (
        "太阳系有八大行星：水星、金星、地球、火星、木星、土星、天王星、海王星。"
        "曾经被认为是行星的冥王星在 2006 年被重新分类为矮行星。"
    ),
}

# 从文件加载扩展知识库（可选）
_KB_FILE = os.path.join(os.path.dirname(__file__), "..", "knowledge_base.json")
if os.path.exists(_KB_FILE):
    try:
        with open(_KB_FILE, "r", encoding="utf-8") as f:
            extra = json.load(f)
            if isinstance(extra, dict):
                _KNOWLEDGE_BASE.update(extra)
    except Exception:
        pass


def search_fn(query: str) -> str:
    """模拟搜索引擎，从内置知识库检索"""
    q = query.strip().lower()

    # 精确匹配
    for key, value in _KNOWLEDGE_BASE.items():
        if key.lower() == q:
            return value

    # 模糊匹配
    matches = []
    for key, value in _KNOWLEDGE_BASE.items():
        if q in key.lower() or key.lower() in q:
            matches.append((key, value))

    # 关键词匹配
    if not matches:
        keywords = q.split()
        for key, value in _KNOWLEDGE_BASE.items():
            key_lower = key.lower()
            for kw in keywords:
                if len(kw) > 1 and kw in key_lower:
                    matches.append((key, value))
                    break

    if matches:
        results = "\n\n".join([f"📖 {m[0]}: {m[1]}" for m in matches[:3]])
        return f"找到 {len(matches)} 个相关结果:\n{results}"

    return (
        f"未找到与「{query}」相关的信息。"
        f"提示：这是一个 Mock 搜索引擎，内置知识有限。"
        f"您可以在 knowledge_base.json 中添加自定义条目。"
    )


SearchTool = Tool(
    name="search",
    description="搜索知识库获取信息。支持精确查询和模糊匹配",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词，例如: python, 什么是agent, capital of france",
            }
        },
        "required": ["query"],
    },
    fn=search_fn,
)
