"""工具注册与调度中心"""

import json
import traceback
from typing import Any, Callable


class Tool:
    """单个工具的描述与实现"""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        fn: Callable[..., str],
    ):
        self.name = name
        self.description = description
        self.parameters = parameters  # JSON Schema
        self.fn = fn

    def to_openai_tool(self) -> dict:
        """转换为 OpenAI 工具定义格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def execute(self, **kwargs) -> str:
        """执行工具，统一返回字符串结果"""
        try:
            result = self.fn(**kwargs)
            return str(result)
        except Exception as e:
            return f"[工具错误] {type(e).__name__}: {e}\n{traceback.format_exc()}"


class ToolRegistry:
    """全局工具注册中心"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        tool = self._tools.get(name)
        if not tool:
            raise KeyError(f"未知工具: {name}，可用工具: {list(self._tools.keys())}")
        return tool

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def to_openai_tools(self) -> list[dict]:
        return [t.to_openai_tool() for t in self._tools.values()]

    def execute(self, name: str, arguments: str | dict) -> dict[str, Any]:
        """执行工具调用，返回标准化的结果记录"""
        # 解析参数
        if isinstance(arguments, str):
            try:
                args = json.loads(arguments)
            except json.JSONDecodeError as e:
                return {
                    "tool": name,
                    "input": arguments,
                    "output": f"[参数解析失败] {e}",
                    "error": True,
                }
        else:
            args = arguments

        # 执行
        tool = self.get(name)
        output = tool.execute(**args)

        return {
            "tool": name,
            "input": json.dumps(args, ensure_ascii=False),
            "output": output,
            "error": output.startswith("[工具错误]"),
        }
