import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()

TASK_DIR = Path(os.environ.get("DATA_DIR", "data")) / "tasks"
TASK_DIR.mkdir(parents=True, exist_ok=True)


class TaskCreateRequest(BaseModel):
    title: str = Field(..., description="任务标题")
    description: str = Field("", description="任务描述")
    assignee: str = Field("", description="负责人")
    priority: str = Field("medium", description="优先级 low/medium/high")
    parent_id: Optional[str] = Field(None, description="父任务 ID")


class TaskUpdateRequest(BaseModel):
    status: Optional[str] = Field(None, description="状态 todo/in_progress/done/cancelled")
    assignee: Optional[str] = Field(None, description="负责人")
    priority: Optional[str] = Field(None, description="优先级")
    description: Optional[str] = Field(None, description="描述")
    title: Optional[str] = Field(None, description="标题")


class TaskActionRequest(BaseModel):
    action: str = Field(..., description="create/update/delete/get/list")
    task_id: Optional[str] = Field(None, description="任务 ID（非 create/list 时需要）")
    payload: dict = Field(default_factory=dict, description="操作载荷")


def _task_path(task_id: str) -> Path:
    safe = "".join(c for c in task_id if c.isalnum() or c in "-_").strip()
    return TASK_DIR / f"{safe}.json"


def _load_task(task_id: str) -> dict:
    path = _task_path(task_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="任务不存在")
    return json.loads(path.read_text(encoding="utf-8"))


def _save_task(task: dict):
    path = _task_path(task["id"])
    path.write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")


@router.post("/action", operation_id="agent_task_action")
async def agent_task_action(req: TaskActionRequest):
    """Agent 任务管理：创建、更新、删除、查询、列表"""
    action = req.action.lower()
    if action == "create":
        payload = req.payload
        task = {
            "id": str(uuid.uuid4()),
            "title": payload.get("title", "未命名任务"),
            "description": payload.get("description", ""),
            "assignee": payload.get("assignee", ""),
            "priority": payload.get("priority", "medium"),
            "status": "todo",
            "parent_id": payload.get("parent_id"),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        _save_task(task)
        return {"success": True, "task": task}

    elif action == "get":
        task = _load_task(req.task_id)
        return {"success": True, "task": task}

    elif action == "update":
        task = _load_task(req.task_id)
        payload = req.payload
        for key in ["title", "description", "assignee", "priority", "status", "parent_id"]:
            if key in payload:
                task[key] = payload[key]
        task["updated_at"] = datetime.utcnow().isoformat()
        _save_task(task)
        return {"success": True, "task": task}

    elif action == "delete":
        path = _task_path(req.task_id)
        if path.exists():
            path.unlink()
        return {"success": True, "deleted_id": req.task_id}

    elif action == "list":
        tasks = []
        status_filter = req.payload.get("status")
        assignee_filter = req.payload.get("assignee")
        for path in TASK_DIR.glob("*.json"):
            try:
                task = json.loads(path.read_text(encoding="utf-8"))
                if status_filter and task.get("status") != status_filter:
                    continue
                if assignee_filter and task.get("assignee") != assignee_filter:
                    continue
                tasks.append(task)
            except Exception:
                continue
        return {"success": True, "tasks": tasks}

    else:
        raise HTTPException(status_code=400, detail=f"不支持的操作: {action}")


@router.get("/status", operation_id="agent_task_status")
async def agent_task_status():
    """获取任务实时统计"""
    tasks = []
    for path in TASK_DIR.glob("*.json"):
        try:
            tasks.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    counts = {"todo": 0, "in_progress": 0, "done": 0, "cancelled": 0}
    for t in tasks:
        counts[t.get("status", "todo")] = counts.get(t.get("status", "todo"), 0) + 1
    return {"total": len(tasks), "counts": counts}
