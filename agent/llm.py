"""LLM API 封装 - 支持 OpenAI / DeepSeek 等兼容接口"""

import json
import os
from typing import Any, Optional
from urllib import request, error


class LLMError(Exception):
    """LLM 调用异常"""
    pass


class LLMClient:
    """轻量 LLM 客户端，无第三方依赖，仅用标准库实现"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        # 优先级：构造参数 > 环境变量 > 默认值
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = (base_url or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")

        if not self.api_key:
            raise LLMError(
                "未设置 API Key。请通过 LLM_API_KEY 环境变量或构造参数传入。\n"
                "  例如: export LLM_API_KEY=sk-xxx\n"
                "        export LLM_BASE_URL=https://api.deepseek.com/v1\n"
                "        export LLM_MODEL=deepseek-chat"
            )

    def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """调用 LLM 聊天补全接口"""
        url = f"{self.base_url}/chat/completions"

        body: dict = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            body["tools"] = tools

        data = json.dumps(body).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            resp = request.urlopen(req, timeout=60)
            result = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise LLMError(f"HTTP {e.code}: {detail}") from e
        except error.URLError as e:
            raise LLMError(f"网络错误: {e.reason}") from e
        except json.JSONDecodeError as e:
            raise LLMError(f"响应解析失败: {e}") from e

        # 验证响应结构
        choices = result.get("choices", [])
        if not choices:
            raise LLMError(f"LLM 返回空 choices: {json.dumps(result, ensure_ascii=False)}")

        return choices[0]

    @staticmethod
    def extract_content(choice: dict) -> str:
        """提取助手文本内容（可能为空，当有 tool_calls 时）"""
        msg = choice.get("message", {})
        return msg.get("content") or ""

    @staticmethod
    def extract_tool_calls(choice: dict) -> list[dict]:
        """提取工具调用列表"""
        msg = choice.get("message", {})
        return msg.get("tool_calls", [])
