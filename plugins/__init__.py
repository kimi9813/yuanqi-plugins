from .web_tool import router as web_tool_router
from .file_tool import router as file_tool_router
from .terminal_tool import router as terminal_tool_router
from .skill_tool import router as skill_tool_router
from .agent_task import router as agent_task_router

__all__ = [
    "web_tool_router",
    "file_tool_router",
    "terminal_tool_router",
    "skill_tool_router",
    "agent_task_router",
]
