"""跨轮次继续执行演示

演示 Agent 在多个对话轮次中保持状态的能力：
  第1轮: 用户创建任务，Agent 记录到 todo 中
  第2轮: 用户询问任务进度，Agent 读取 todo 状态并继续处理

运行方式:
  python examples/cross_turn_demo.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.llm import LLMClient
from agent.runtime import AgentRuntime
from agent.tool_registry import ToolRegistry
from tools import CalculatorTool, SearchTool, TodoTool, WeatherTool


def build_agent() -> AgentRuntime:
    """构造 Agent 实例（verbose=True 显示详细日志）"""
    llm = LLMClient()
    registry = ToolRegistry()
    registry.register(CalculatorTool)
    registry.register(SearchTool)
    registry.register(TodoTool)
    registry.register(WeatherTool)

    return AgentRuntime(
        llm=llm,
        tool_registry=registry,
        max_steps=10,
    )


def run_demo():
    print("=" * 60)
    print("  跨轮次继续执行演示")
    print("=" * 60)

    runtime = build_agent()
    session_id = None  # 第一次为 None，后续复用

    # ====== 第1轮：创建任务 ======
    print("\n" + "─" * 60)
    print("📌 第1轮: 用户创建一个调研任务")
    print("─" * 60)

    result1 = runtime.chat(
        message="帮我创建一个调研任务：调研 Python 异步编程框架，优先级高。",
        session_id=session_id,
        verbose=False,
    )
    session_id = result1["session_id"]
    print(f"\n🤖 助手: {result1['answer']}")
    print(f"\n📊 本轮信息:")
    print(f"  会话 ID: {session_id}")
    print(f"  Agent 循环轮数: {result1['steps']}/{result1['max_steps']}")
    print(f"  工具调用追踪:")
    for t in result1["trace"]:
        if t["event"] == "tool_call":
            print(f"    第 {t['step']} 轮: {t['tool']} → 耗时 {t.get('duration_ms', 0)}ms")

    # ====== 模拟用户离开，然后回来 ======
    print("\n" + "─" * 60)
    print("⏳ 用户离开一段时间...")
    print("  会话已保存，稍后可以继续。")
    print("─" * 60)

    # ====== 第2轮：用户回来询问进度 ======
    print("\n" + "─" * 60)
    print("📌 第2轮: 用户回来，追问任务进度")
    print("  （复用同一 session_id，体现跨轮次状态保持）")
    print("─" * 60)

    result2 = runtime.chat(
        message="我之前创建的任务完成了吗？帮我查一下进度。",
        session_id=session_id,
        verbose=False,
    )
    print(f"\n🤖 助手: {result2['answer']}")
    print(f"\n📊 本轮信息:")
    print(f"  会话 ID: {result2['session_id']} (同一会话)")
    print(f"  Agent 循环轮数: {result2['steps']}/{result2['max_steps']}")
    print(f"  工具调用追踪:")
    for t in result2["trace"]:
        if t["event"] == "tool_call":
            print(f"    第 {t['step']} 轮: {t['tool']} → 耗时 {t.get('duration_ms', 0)}ms")

    # ====== 第3轮：更新任务状态并查其他 ======
    print("\n" + "─" * 60)
    print("📌 第3轮: 更新任务状态 + 询问无关问题（验证上下文独立性）")
    print("─" * 60)

    result3 = runtime.chat(
        message="帮我查一下今天北京的天气怎么样？另外把那个调研任务标记为进行中。",
        session_id=session_id,
        verbose=False,
    )
    print(f"\n🤖 助手: {result3['answer']}")
    print(f"\n📊 本轮信息:")
    print(f"  Agent 循环轮数: {result3['steps']}/{result3['max_steps']}")
    for t in result3["trace"]:
        if t["event"] == "tool_call":
            print(f"    第 {t['step']} 轮: {t['tool']} → 耗时 {t.get('duration_ms', 0)}ms")

    # ====== 第4轮：清理 ======
    print("\n" + "─" * 60)
    print("📌 第4轮: 验证跨轮次记忆 — 询问之前的信息")
    print("─" * 60)

    result4 = runtime.chat(
        message="我刚才创建的那个任务现在是什么状态？",
        session_id=session_id,
        verbose=False,
    )
    print(f"\n🤖 助手: {result4['answer']}")
    print(f"\n📊 本轮信息:")
    print(f"  Agent 循环轮数: {result4['steps']}/{result4['max_steps']}")

    # ====== 总结 ======
    print("\n" + "=" * 60)
    print("  🎉 演示完成！")
    print("=" * 60)
    print(f"\n📋 会话摘要:")
    session = runtime.get_session_detail(session_id)
    if session:
        print(f"  会话 ID: {session.session_id}")
        print(f"  总轮次: {session.metadata['turn_count']}")
        print(f"  工具调用次数: {session.metadata['tool_call_count']}")
        print(f"  创建时间: {session.metadata['created_at']}")
        print(f"  最后更新: {session.metadata['updated_at']}")
        print(f"  持久化上下文 keys: {list(session.context.keys())}")
    print(f"\n💡 关键演示点:")
    print(f"  ✅ 第1轮创建任务 → 工具调用的结果持久化到 todo_store.json")
    print(f"  ✅ 第2轮查询进度 → Agent 从 todo 读取回之前创建的任务")
    print(f"  ✅ 第3轮同时处理天气查询 + 任务更新 → 多工具协作")
    print(f"  ✅ 第4轮跨轮次记忆 → 通过会话历史保持上下文")
    print(f"  ✅ 所有状态持久化在文件系统中 → 即使程序重启也能继续")


if __name__ == "__main__":
    run_demo()
