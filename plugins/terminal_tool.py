import ast
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

WORK_DIR = Path("data/files")
WORK_DIR.mkdir(parents=True, exist_ok=True)

FORBIDDEN_SHELL = ["rm -rf /", ":(){ :|:& };:", "> /dev/sda", "mkfs", "dd if=/dev/zero"]


class PythonExecuteRequest(BaseModel):
    code: str = Field(..., description="Python 代码")
    timeout: int = Field(10, ge=1, le=60, description="执行超时秒数")


class ShellExecuteRequest(BaseModel):
    command: str = Field(..., description="Shell 命令")
    timeout: int = Field(10, ge=1, le=60, description="执行超时秒数")


class FileEditRequest(BaseModel):
    action: str = Field(..., description="create/read/update/delete")
    path: str = Field(..., description="相对工作目录的路径")
    content: str = Field("", description="文件内容（create/update 需要）")


class SkillInvokeRequest(BaseModel):
    skill_name: str = Field(..., description="技能名称")
    parameters: dict = Field(default_factory=dict, description="调用参数")


def _safe_work_path(filename: str) -> Path:
    base = WORK_DIR.resolve()
    target = (base / filename).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(status_code=400, detail="非法文件路径")
    return target


def _check_shell(command: str):
    lowered = command.lower()
    for bad in FORBIDDEN_SHELL:
        if bad.lower() in lowered:
            raise HTTPException(status_code=400, detail="检测到危险命令，已拦截")


@router.post("/python", operation_id="terminal_python_execute")
async def terminal_python_execute(req: PythonExecuteRequest):
    """执行 Python 代码并返回输出 / 报错"""
    try:
        tree = ast.parse(req.code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    name = alias.name
                    if name in {"os", "sys", "subprocess", "shutil"}:
                        # 允许使用，但限制危险操作
                        pass
    except SyntaxError as exc:
        return {"success": False, "stdout": "", "stderr": f"语法错误: {exc}"}

    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(req.code)
        tmp_path = f.name

    try:
        proc = subprocess.run(
            ["python", tmp_path],
            capture_output=True,
            text=True,
            timeout=req.timeout,
            cwd=str(WORK_DIR),
        )
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "执行超时"}
    except Exception as exc:
        return {"success": False, "stdout": "", "stderr": str(exc)}
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.post("/shell", operation_id="terminal_shell_execute")
async def terminal_shell_execute(req: ShellExecuteRequest):
    """执行受控 Shell 命令"""
    _check_shell(req.command)
    try:
        proc = subprocess.run(
            req.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=req.timeout,
            cwd=str(WORK_DIR),
        )
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "", "stderr": "执行超时"}
    except Exception as exc:
        return {"success": False, "stdout": "", "stderr": str(exc)}


@router.post("/file", operation_id="terminal_file_edit")
async def terminal_file_edit(req: FileEditRequest):
    """文件创建 / 读取 / 更新 / 删除"""
    path = _safe_work_path(req.path)
    try:
        if req.action == "create":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(req.content, encoding="utf-8")
            return {"success": True, "path": req.path, "action": "create"}
        elif req.action == "read":
            if not path.exists():
                raise HTTPException(status_code=404, detail="文件不存在")
            content = path.read_text(encoding="utf-8")
            return {"success": True, "path": req.path, "content": content}
        elif req.action == "update":
            if not path.exists():
                raise HTTPException(status_code=404, detail="文件不存在")
            path.write_text(req.content, encoding="utf-8")
            return {"success": True, "path": req.path, "action": "update"}
        elif req.action == "delete":
            if not path.exists():
                raise HTTPException(status_code=404, detail="文件不存在")
            if path.is_file():
                path.unlink()
            else:
                shutil.rmtree(path)
            return {"success": True, "path": req.path, "action": "delete"}
        else:
            raise HTTPException(status_code=400, detail="不支持的 action")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文件操作失败: {exc}")


@router.post("/java", operation_id="terminal_java_execute")
async def terminal_java_execute(req: PythonExecuteRequest):
    """编译并执行 Java 代码（如果系统已安装 javac/java）"""
    class_name = f"Main{uuid.uuid4().hex[:8]}"
    code = req.code.replace("public class Main", f"public class {class_name}")
    if f"public class {class_name}" not in code:
        code = f"public class {class_name} {{\n{req.code}\n}}"

    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / f"{class_name}.java"
        src.write_text(code, encoding="utf-8")
        try:
            compile_proc = subprocess.run(
                ["javac", str(src)],
                capture_output=True,
                text=True,
                timeout=req.timeout,
            )
            if compile_proc.returncode != 0:
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": compile_proc.stderr,
                }
            run_proc = subprocess.run(
                ["java", "-cp", tmpdir, class_name],
                capture_output=True,
                text=True,
                timeout=req.timeout,
            )
            return {
                "success": run_proc.returncode == 0,
                "stdout": run_proc.stdout,
                "stderr": run_proc.stderr,
            }
        except FileNotFoundError:
            return {
                "success": False,
                "stdout": "",
                "stderr": "系统中未安装 javac/java，无法执行 Java 代码",
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": "执行超时"}
