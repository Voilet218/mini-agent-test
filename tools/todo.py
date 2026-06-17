"""待办事项工具 - 支持跨轮次的状态持久化"""

import json
import os
import time
from agent.tool_registry import Tool

_TODO_FILE = os.path.join(os.path.dirname(__file__), "..", "todo_store.json")


class TodoStore:
    """基于文件的待办存储，支持跨会话持久化"""

    def __init__(self, filepath: str = _TODO_FILE):
        self.filepath = filepath
        self._tasks: list[dict] = []
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self._tasks = json.load(f)
            except Exception:
                self._tasks = []
        else:
            self._tasks = []

    def _save(self):
        os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self._tasks, f, ensure_ascii=False, indent=2)

    def add(self, title: str, description: str = "") -> dict:
        task = {
            "id": str(int(time.time() * 1000))[-8:],
            "title": title,
            "description": description,
            "status": "pending",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._tasks.append(task)
        self._save()
        return task

    def list(self, status: str | None = None) -> list[dict]:
        if status:
            return [t for t in self._tasks if t["status"] == status]
        return self._tasks

    def update(self, task_id: str, **updates) -> dict | None:
        for task in self._tasks:
            if task["id"] == task_id:
                task.update(updates)
                task["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                self._save()
                return task
        return None

    def delete(self, task_id: str) -> bool:
        before = len(self._tasks)
        self._tasks = [t for t in self._tasks if t["id"] != task_id]
        if len(self._tasks) < before:
            self._save()
            return True
        return False

    def get_summary(self) -> str:
        total = len(self._tasks)
        pending = sum(1 for t in self._tasks if t["status"] == "pending")
        done = sum(1 for t in self._tasks if t["status"] == "done")
        in_progress = sum(1 for t in self._tasks if t["status"] == "in_progress")
        return f"共 {total} 个任务: 待处理 {pending}, 进行中 {in_progress}, 已完成 {done}"


# 全局单例
_store = TodoStore()


def todo_fn(action: str, **kwargs) -> str:
    """操作待办事项"""
    action = action.lower()

    if action == "add":
        task = _store.add(kwargs.get("title", "未命名任务"), kwargs.get("description", ""))
        return f"✅ 已创建任务 [{task['id']}]: {task['title']}\n状态: {task['status']}"

    elif action == "list":
        status = kwargs.get("status")
        tasks = _store.list(status)
        if not tasks:
            return "📭 暂无任务" + (f"（状态: {status}）" if status else "")
        lines = [f"📋 共 {len(tasks)} 个任务" + (f"（状态: {status}）" if status else "")]
        for t in tasks:
            flag = "✅" if t["status"] == "done" else "🔄" if t["status"] == "in_progress" else "📌"
            lines.append(f"  {flag} [{t['id']}] {t['title']} — {t['status']}")
        return "\n".join(lines)

    elif action == "update":
        task_id = kwargs.get("id", kwargs.get("task_id", ""))
        title = kwargs.get("title")
        desc = kwargs.get("description")
        status = kwargs.get("status")
        updates = {}
        if title:
            updates["title"] = title
        if desc:
            updates["description"] = desc
        if status:
            updates["status"] = status
        if not updates:
            return "请提供要更新的字段（title/description/status）"
        task = _store.update(task_id, **updates)
        if task:
            return f"✅ 已更新任务 [{task_id}]: {task['title']} -> {task['status']}"
        return f"❌ 未找到任务: {task_id}"

    elif action == "delete":
        task_id = kwargs.get("id", kwargs.get("task_id", ""))
        if _store.delete(task_id):
            return f"🗑️ 已删除任务: {task_id}"
        return f"❌ 未找到任务: {task_id}"

    elif action == "summary":
        return _store.get_summary()

    else:
        return (
            f"未知操作: {action}。支持的操作: add, list, update, delete, summary"
        )


TodoTool = Tool(
    name="todo",
    description=(
        "待办事项管理。支持创建、查看、更新、删除任务。"
        "数据持久化在文件中，跨会话保留。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "list", "update", "delete", "summary"],
                "description": "add=创建, list=列出, update=更新, delete=删除, summary=统计",
            },
            "title": {
                "type": "string",
                "description": "任务标题（创建/更新时用）",
            },
            "description": {
                "type": "string",
                "description": "任务描述（创建/更新时用）",
            },
            "status": {
                "type": "string",
                "enum": ["pending", "in_progress", "done"],
                "description": "任务状态（list过滤/更新时用）",
            },
            "id": {
                "type": "string",
                "description": "任务ID（更新/删除时用）",
            },
        },
        "required": ["action"],
    },
    fn=todo_fn,
)
