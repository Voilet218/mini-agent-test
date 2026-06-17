"""Agent 核心运行时 - 从零实现的 ReAct 循环

流程:
  接收用户输入
  → LLM 思考（直接回答 or 调用工具）
  → 如有工具调用 → 执行工具 → 结果反馈给 LLM → 继续
  → 直到 LLM 给出最终答案
"""

import json
import time
from typing import Optional

from agent.llm import LLMClient, LLMError
from agent.session import Session, SessionManager
from agent.tool_registry import ToolRegistry


class AgentRuntime:
    """最小 Agent 运行时"""

    def __init__(
        self,
        llm: LLMClient,
        tool_registry: ToolRegistry,
        session_manager: Optional[SessionManager] = None,
        max_steps: int = 10,
        system_prompt: Optional[str] = None,
    ):
        self.llm = llm
        self.tools = tool_registry
        self.sessions = session_manager or SessionManager()
        self.max_steps = max_steps
        self.system_prompt = system_prompt or self._default_system_prompt()

        # 运行时统计
        self.stats = {
            "total_sessions": 0,
            "total_tool_calls": 0,
            "total_steps": 0,
        }

    @staticmethod
    def _default_system_prompt() -> str:
        return """你是一个智能 AI 助手，可以使用工具帮助用户完成任务。

## 工具使用规则
1. 当用户的问题需要外部信息或操作时，请调用合适的工具
2. 工具调用结果会作为新的消息返回给你
3. 根据工具结果继续推理，直到给出最终答案
4. 如果一次需要多个信息，可以分步调用工具
5. 如果问题可以直接回答，不需要调用工具

## 回答规范
- 用中文回答用户问题（除非用户用其他语言提问）
- 给出清晰、结构化的回答
- 引用工具结果时说明信息来源
- 如果需要用户确认或补充信息，请礼貌地询问

## 状态保持
- 如果用户问之前讨论过的内容，可以参考对话历史
- 如果是跨轮次的任务（如创建任务后查询进度），请结合任务管理工具的状态回复"""

    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        verbose: bool = True,
    ) -> dict:
        """处理单轮用户输入，返回最终回答

        步数规则（关键！）：
          - step 仅统计「调用工具的轮次」= Agent 循环轮数
          - LLM 给出最终答案（无工具调用）不计入步数
          - 每轮循环：LLM 思考 → 决定调工具 → 执行工具 → 继续下一轮
          - 达到 max_steps 后不再执行新工具，直接终止
        """
        # 获取或创建会话
        session = self.sessions.get_or_create(session_id)
        is_new = session.is_empty()

        if is_new:
            # 新会话：注入 system prompt
            session.messages.append({
                "role": "system",
                "content": self.system_prompt,
            })
            self.stats["total_sessions"] += 1

        # 添加用户消息
        session.add_message("user", message)

        # 主循环
        step = 0            # Agent 循环轮数（工具调用轮次）
        reached_limit = False
        trace = []          # 工具调用追踪日志

        while True:
            # 1. 调用 LLM
            try:
                messages = session.messages
                tools_def = self.tools.to_openai_tools()

                choice = self.llm.chat(
                    messages=messages,
                    tools=tools_def if tools_def else None,
                )
            except LLMError as e:
                error_msg = f"⚠️ LLM 调用失败: {e}"
                trace.append({"step": step, "event": "error", "detail": error_msg})
                if verbose:
                    print(f"\n  {error_msg}")
                session.add_message("assistant", error_msg)
                break

            # 2. 提取 LLM 回复
            content = self.llm.extract_content(choice)
            tool_calls = self.llm.extract_tool_calls(choice)

            # 3. 如果没有工具调用 → 最终答案（不计入步数）
            if not tool_calls:
                if verbose:
                    preview = content[:200] + "..." if len(content) > 200 else content
                    print(f"\n{'─'*40}")
                    print(f"  🤖 最终答案: {preview}")
                    if step > 0:
                        print(f"  （共 {step} 轮工具调用）")
                session.add_message("assistant", content)
                trace.append({"step": step, "event": "final_answer", "content_preview": content[:100]})
                break

            # 4. 有工具调用 → 步数检查（在执行前检查是否已达到上限）
            if step >= self.max_steps:
                msg = f"⚠️ 已达到最大 Agent 循环轮数限制 ({self.max_steps})，不执行新工具"
                if verbose:
                    print(f"\n  {msg}")
                session.add_message("assistant", f"{msg}（LLM 尝试调用: {[tc.get('function',{}).get('name','') for tc in tool_calls]}）")
                trace.append({"step": step, "event": "max_steps_reached", "detail": msg})
                reached_limit = True
                break

            # 5. Agent 循环轮数 +1
            step += 1
            self.stats["total_steps"] += 1

            if verbose:
                print(f"\n{'='*50}")
                print(f"  🔄 Agent 循环第 {step}/{self.max_steps} 轮")
                print(f"{'='*50}")

            # 6. 记录助手消息（含工具调用）
            assistant_msg: dict = {"role": "assistant", "content": content}
            assistant_msg["tool_calls"] = tool_calls
            session.messages.append(assistant_msg)

            if verbose:
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    print(f"  🔧 调用: {fn.get('name')}({fn.get('arguments', {})})")

            # 7. 执行每个工具
            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                arguments = fn.get("arguments", "{}")
                tc_id = tc.get("id", "")

                start = time.time()
                result = self.tools.execute(name, arguments)
                elapsed = time.time() - start

                # 记录到会话
                session.add_tool_result(tc_id, name, result["output"])

                # 记录追踪日志
                trace.append({
                    "step": step,
                    "event": "tool_call",
                    "tool": name,
                    "input": result["input"],
                    "output_preview": result["output"][:150],
                    "duration_ms": round(elapsed * 1000),
                    "error": result["error"],
                })

                if verbose:
                    status = "❌" if result["error"] else "✅"
                    print(f"  {status} {name} 完成 ({elapsed*1000:.0f}ms)")
                    if result["error"]:
                        print(f"    错误: {result['output'][:200]}")

            # 8. 执行后检查：如果本轮已达到上限，不再继续下一轮
            if step >= self.max_steps:
                msg = f"⚠️ 已达到最大 Agent 循环轮数限制 ({self.max_steps})，终止执行"
                if verbose:
                    print(f"\n  {msg}")
                session.add_message("assistant", msg)
                trace.append({"step": step, "event": "max_steps_reached", "detail": msg})
                reached_limit = True
                break

        # 保存会话
        session.save()

        # 返回结果
        return {
            "session_id": session.session_id,
            "answer": session.messages[-1]["content"] if session.messages else "",
            "steps": step,                       # Agent 循环轮数（工具调用轮次）
            "max_steps": self.max_steps,
            "reached_limit": reached_limit,       # 是否因达到上限而终止
            "trace": trace,
            "session_info": session.to_dict(),
        }

    def list_sessions(self) -> list[dict]:
        return self.sessions.list_sessions()

    def get_session_detail(self, session_id: str) -> Optional[Session]:
        return self.sessions.get_session(session_id)
