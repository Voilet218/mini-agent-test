"""会话管理 - 支持多轮对话与跨轮次上下文维持"""

import json
import os
import time
import uuid
from typing import Optional

_SESSION_DIR = os.path.join(os.path.dirname(__file__), "..", "sessions")


def _ensure_session_dir():
    os.makedirs(_SESSION_DIR, exist_ok=True)


def _session_path(session_id: str) -> str:
    return os.path.join(_SESSION_DIR, f"{session_id}.json")


class Session:
    """单个会话：包含消息历史、元数据、持久化上下文"""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())[:12]
        self.messages: list[dict] = []
        self.context: dict = {}    # 持久化上下文（跨轮次保持）
        self.metadata: dict = {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "turn_count": 0,
            "tool_call_count": 0,
        }
        self._load()

    def _load(self):
        path = _session_path(self.session_id)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.messages = data.get("messages", [])
                    self.context = data.get("context", {})
                    self.metadata = data.get("metadata", self.metadata)
            except Exception as e:
                print(f"[Session] 加载会话失败: {e}")

    def save(self):
        _ensure_session_dir()
        self.metadata["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.metadata["turn_count"] = self._count_turns()
        data = {
            "session_id": self.session_id,
            "messages": self.messages,
            "context": self.context,
            "metadata": self.metadata,
        }
        path = _session_path(self.session_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _count_turns(self) -> int:
        """统计用户消息数作为轮次数"""
        return sum(1 for m in self.messages if m.get("role") == "user")

    def add_message(self, role: str, content: str, tool_calls: Optional[list] = None):
        msg = {"role": role, "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self.messages.append(msg)

    def add_tool_result(self, tool_call_id: str, tool_name: str, content: str):
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": content,
        })
        self.metadata["tool_call_count"] += 1

    def update_context(self, key: str, value):
        """更新持久化上下文（跨轮次保持）"""
        self.context[key] = value
        self.save()

    def get_context(self, key: str, default=None):
        return self.context.get(key, default)

    def get_recent_messages(self, n: int = 20) -> list[dict]:
        """获取最近的 N 条消息（用于控制 token 长度）"""
        return self.messages[-n:] if len(self.messages) > n else self.messages

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "turn_count": self.metadata["turn_count"],
            "tool_call_count": self.metadata["tool_call_count"],
            "context_keys": list(self.context.keys()),
            "created_at": self.metadata["created_at"],
            "updated_at": self.metadata["updated_at"],
        }

    def is_empty(self) -> bool:
        return len(self.messages) == 0

    def __repr__(self):
        return f"Session(id={self.session_id}, msgs={len(self.messages)})"


class SessionManager:
    """会话管理器，支持创建、恢复、列出会话"""

    def __init__(self, session_dir: str = _SESSION_DIR):
        self.session_dir = session_dir
        _ensure_session_dir()

    def create_session(self) -> Session:
        return Session()

    def get_session(self, session_id: str) -> Optional[Session]:
        path = _session_path(session_id)
        if os.path.exists(path):
            return Session(session_id)
        return None

    def get_or_create(self, session_id: Optional[str] = None) -> Session:
        if session_id and os.path.exists(_session_path(session_id)):
            return Session(session_id)
        return Session(session_id)

    def list_sessions(self) -> list[dict]:
        _ensure_session_dir()
        sessions = []
        for fname in os.listdir(self.session_dir):
            if fname.endswith(".json"):
                sid = fname[:-5]
                try:
                    s = Session(sid)
                    sessions.append(s.to_dict())
                except Exception:
                    continue
        # 按更新时间排序，最新的在前
        sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        path = _session_path(session_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
