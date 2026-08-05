import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# 优先使用打包在项目内的依赖（适用于 SCF 等不自动安装依赖的环境）
if os.environ.get("SKIP_VENDOR") != "1":
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


def _resolve_data_dir() -> str:
    """解析数据目录：优先环境变量，否则尝试当前目录，不可写则回退到 /tmp/data。"""
    if os.environ.get("DATA_DIR"):
        return os.environ["DATA_DIR"]
    candidate = Path("data")
    try:
        candidate.mkdir(parents=True, exist_ok=True)
        # 测试是否可写
        test_file = candidate / ".write_test"
        test_file.write_text("ok")
        test_file.unlink()
        return str(candidate)
    except OSError:
        return "/tmp/data"


os.environ.setdefault("DATA_DIR", _resolve_data_dir())


@asynccontextmanager
async def lifespan(app: FastAPI):
    data_dir = Path(os.environ["DATA_DIR"])
    os.makedirs(data_dir / "files", exist_ok=True)
    os.makedirs(data_dir / "skills", exist_ok=True)
    os.makedirs(data_dir / "tasks", exist_ok=True)
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
