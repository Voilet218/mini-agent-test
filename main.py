#!/usr/bin/env python3
"""Minimal Agent - 从零实现的最小可用 Agent

用法:
  python main.py                              # 交互模式（新会话）
  python main.py --session <id>               # 恢复指定会话
  python main.py --list-sessions              # 列出所有会话
  python main.py --one-shot "你的问题"         # 单轮模式
  python main.py --verbose false              # 简洁模式

环境变量:
  LLM_API_KEY    API 密钥（必需）
  LLM_BASE_URL   API 地址（默认: https://api.openai.com/v1）
  LLM_MODEL      模型名（默认: gpt-4o-mini）
"""

import argparse
import json
import os
import re
import sys

# 将项目根目录加入 path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


def load_env_file(env_path: str = ".env"):
    """加载 .env 文件到环境变量（纯标准库实现，不使用 python-dotenv）"""
    env_file = os.path.join(BASE_DIR, env_path)
    if not os.path.exists(env_file):
        return
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith("#"):
                continue
            # 只处理 KEY=VALUE 格式
            match = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$', line)
            if match:
                key, value = match.group(1), match.group(2)
                # 去掉引号
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                # 只设置尚未设置的环境变量（已有环境变量优先级更高）
                if key not in os.environ:
                    os.environ[key] = value


# 启动时自动加载 .env 文件
load_env_file()

from agent.llm import LLMClient, LLMError
from agent.runtime import AgentRuntime
from agent.tool_registry import ToolRegistry
from tools import CalculatorTool, SearchTool, TodoTool, WeatherTool


def build_agent(verbose: bool = True) -> AgentRuntime:
    """构造 Agent 实例"""
    # 1. LLM
    try:
        llm = LLMClient()
    except LLMError as e:
        print(f"❌ {e}")
        print("\n💡 请设置环境变量:")
        print('   set LLM_API_KEY=sk-xxx')
        print('   set LLM_BASE_URL=https://api.deepseek.com/v1')
        print('   set LLM_MODEL=deepseek-chat')
        sys.exit(1)

    # 2. 工具
    registry = ToolRegistry()
    registry.register(CalculatorTool)
    registry.register(SearchTool)
    registry.register(TodoTool)
    registry.register(WeatherTool)

    # 3. 运行时
    runtime = AgentRuntime(
        llm=llm,
        tool_registry=registry,
        max_steps=10,
    )
    return runtime


def print_welcome():
    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║        🤖  Minimal Agent - 最小可用 Agent        ║")
    print("╠══════════════════════════════════════════════════╣")
    print("║  命令:                                          ║")
    print("║    /new     — 新建会话                          ║")
    print("║    /list    — 显示所有会话                      ║")
    print("║    /switch <id> — 切换会话                      ║")
    print("║    /del <id>    — 删除会话                      ║")
    print("║    /tools   — 列出可用工具                      ║")
    print("║    /help    — 帮助                              ║")
    print("║    /quit    — 退出                              ║")
    print("╚══════════════════════════════════════════════════╝")
    print()


def print_tools(runtime: AgentRuntime):
    print("\n📦 可用工具:")
    for t in runtime.tools.list_tools():
        print(f"  🔧 {t.name}: {t.description}")
    print()


def format_trace(trace: list[dict]) -> str:
    """格式化工具调用追踪日志"""
    lines = []
    for t in trace:
        if t["event"] == "tool_call":
            status = "✅" if not t.get("error") else "❌"
            lines.append(
                f"  第 {t['step']} 轮: {status} {t['tool']} "
                f"({t.get('duration_ms', 0)}ms)"
            )
            lines.append(f"    输入: {t['input']}")
            lines.append(f"    输出: {t['output_preview']}")
        elif t["event"] == "final_answer":
            lines.append(f"  ✅ 最终输出")
        elif t["event"] == "error":
            lines.append(f"  ⚠️  错误: {t['detail']}")
        elif t["event"] == "max_steps_reached":
            lines.append(f"  ⚠️  {t['detail']}")
    return "\n".join(lines)


def interactive_mode():
    """交互式多轮对话"""
    runtime = build_agent(verbose=True)
    current_session_id = None

    print_welcome()
    print_tools(runtime)

    while True:
        try:
            user_input = input("\n🧑 你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 再见！")
            break

        if not user_input:
            continue

        # 处理命令
        if user_input.startswith("/"):
            cmd = user_input.lower().split()
            command = cmd[0] if cmd else ""

            if command == "/quit" or command == "/exit":
                print("👋 再见！")
                break

            elif command == "/new":
                current_session_id = None
                print("🆕 已创建新会话")
                continue

            elif command == "/list":
                sessions = runtime.list_sessions()
                if not sessions:
                    print("📭 暂无历史会话")
                else:
                    print(f"\n📋 共 {len(sessions)} 个会话:")
                    for s in sessions:
                        sid = s.get("session_id", "?")
                        ctx = s.get("updated_at", "?")
                        msgs = s.get("turn_count", 0)
                        print(f"  [{sid}] {msgs} 轮, 最后: {ctx}")
                continue

            elif command == "/switch" and len(cmd) > 1:
                current_session_id = cmd[1]
                s = runtime.get_session_detail(current_session_id)
                if s:
                    turns = s.metadata.get("turn_count", 0)
                    print(f"🔄 已切换到会话 [{current_session_id}] ({turns} 轮)")
                else:
                    print(f"❌ 未找到会话: {current_session_id}")
                    current_session_id = None
                continue

            elif command == "/del" and len(cmd) > 1:
                if runtime.sessions.delete_session(cmd[1]):
                    print(f"🗑️ 已删除会话: {cmd[1]}")
                    if current_session_id == cmd[1]:
                        current_session_id = None
                else:
                    print(f"❌ 未找到会话: {cmd[1]}")
                continue

            elif command == "/tools":
                print_tools(runtime)
                continue

            elif command == "/help":
                print_welcome()
                continue

            else:
                print(f"未知命令: {command}，输入 /help 查看帮助")
                continue

        # 处理用户消息
        if current_session_id:
            prefix = f"[会话 {current_session_id[:8]}...] "
        else:
            prefix = "[新会话] "

        print(f"\n{prefix}思考中...")

        try:
            result = runtime.chat(
                message=user_input,
                session_id=current_session_id,
                verbose=True,
            )
            current_session_id = result["session_id"]

            # 输出最终答案
            answer = result.get("answer", "")
            if answer:
                print(f"\n🤖 助手: {answer}")

            # 输出统计
            print(f"\n📊 [{result['steps']} 轮工具调用, "
                  f"会话 {result['session_info']['turn_count']} 轮]")

        except Exception as e:
            print(f"\n❌ 运行时错误: {e}")
            import traceback
            traceback.print_exc()


def one_shot_mode(query: str, verbose: bool = True):
    """单轮模式"""
    runtime = build_agent(verbose=verbose)
    result = runtime.chat(message=query, verbose=verbose)

    print(f"\n{'='*50}")
    print(f"🤖 最终答案:")
    print(f"{'='*50}")
    print(result.get("answer", ""))

    if verbose:
        print(f"\n{'='*50}")
        print(f"📊 执行统计:")
        print(f"{'='*50}")
        print(f"  会话 ID: {result['session_id']}")
        print(f"  Agent 循环轮数: {result['steps']}/{result.get('max_steps', '?')}")
        print(f"  追踪日志:")
        print(format_trace(result["trace"]))


def main():
    parser = argparse.ArgumentParser(description="Minimal Agent - 最小可用 Agent")
    parser.add_argument("--session", "-s", help="恢复指定会话 ID")
    parser.add_argument("--list-sessions", action="store_true", help="列出所有会话")
    parser.add_argument("--one-shot", "-1", help="单轮模式，直接提问")
    parser.add_argument("--verbose", default="true", choices=["true", "false"],
                        help="是否显示详细日志")
    args = parser.parse_args()

    verbose = args.verbose.lower() == "true"

    if args.list_sessions:
        runtime = build_agent(verbose=False)
        sessions = runtime.list_sessions()
        if not sessions:
            print("📭 暂无历史会话")
        else:
            print(f"📋 共 {len(sessions)} 个会话:")
            for s in sessions:
                print(f"  [{s['session_id']}] {s['turn_count']} 轮, "
                      f"工具调用 {s['tool_call_count']} 次, "
                      f"更新于 {s['updated_at']}")
        return

    if args.one_shot:
        one_shot_mode(args.one_shot, verbose=verbose)
        return

    # 恢复会话
    if args.session:
        runtime = build_agent(verbose=verbose)
        s = runtime.get_session_detail(args.session)
        if s:
            print(f"🔄 恢复会话 [{args.session}] ({s.metadata.get('turn_count', 0)} 轮)")
        else:
            print(f"⚠️  未找到会话 [{args.session}]，将创建新会话")

    # 默认为交互模式
    interactive_mode()


if __name__ == "__main__":
    main()
