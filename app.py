import os
import sys
from contextlib import asynccontextmanager

# 优先使用打包在项目内的依赖（适用于 SCF 等不自动安装依赖的环境）
vendor_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
if os.path.isdir(vendor_path) and vendor_path not in sys.path:
    sys.path.insert(0, vendor_path)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from plugins import (
    agent_task_router,
    file_tool_router,
    skill_tool_router,
    terminal_tool_router,
    web_tool_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("data/files", exist_ok=True)
    os.makedirs("data/skills", exist_ok=True)
    os.makedirs("data/tasks", exist_ok=True)
    yield


app = FastAPI(
    title="Yuanqi Plugins",
    description="Tencent Yuanqi Agent Plugins - web, file, terminal, skill, agent task",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(web_tool_router, prefix="/web", tags=["web_tool"])
app.include_router(file_tool_router, prefix="/file", tags=["file_tool"])
app.include_router(terminal_tool_router, prefix="/terminal", tags=["terminal_tool"])
app.include_router(skill_tool_router, prefix="/skill", tags=["skill_tool"])
app.include_router(agent_task_router, prefix="/agent", tags=["agent_task"])

app.mount("/widget", StaticFiles(directory="static/widget", html=True), name="widget")


@app.get("/")
async def root():
    return {
        "name": "yuanqi-plugins",
        "version": "1.0.0",
        "plugins": [
            {"name": "web_tool", "prefix": "/web", "tools": 2},
            {"name": "file_tool", "prefix": "/file", "tools": 2},
            {"name": "terminal_tool", "prefix": "/terminal", "tools": 4},
            {"name": "skill_tool", "prefix": "/skill", "tools": 2},
            {"name": "agent_task", "prefix": "/agent", "tools": 1},
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
