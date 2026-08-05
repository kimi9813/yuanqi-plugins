import json
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

SKILL_DIR = Path(os.environ.get("DATA_DIR", "data")) / "skills"
SKILL_DIR.mkdir(parents=True, exist_ok=True)


class SkillCreateRequest(BaseModel):
    name: str = Field(..., description="技能名称")
    description: str = Field("", description="技能描述")
    prompt_template: str = Field(..., description="技能提示词模板")
    parameters: dict = Field(default_factory=dict, description="参数 JSON Schema")


class SkillInvokeRequest(BaseModel):
    name: str = Field(..., description="技能名称")
    parameters: dict = Field(default_factory=dict, description="调用参数")


def _skill_path(name: str) -> Path:
    safe = "".join(c for c in name if c.isalnum() or c in "._-").strip()
    if not safe:
        raise HTTPException(status_code=400, detail="非法技能名称")
    return SKILL_DIR / f"{safe}.json"


@router.post("/create", operation_id="skill_create")
async def skill_create(req: SkillCreateRequest):
    """创建新技能"""
    path = _skill_path(req.name)
    skill = {
        "id": str(uuid.uuid4()),
        "name": req.name,
        "description": req.description,
        "prompt_template": req.prompt_template,
        "parameters": req.parameters,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    path.write_text(json.dumps(skill, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"success": True, "skill": skill}


@router.post("/invoke", operation_id="skill_invoke")
async def skill_invoke(req: SkillInvokeRequest):
    """调用已创建技能，返回按模板渲染后的提示词"""
    path = _skill_path(req.name)
    if not path.exists():
        raise HTTPException(status_code=404, detail="技能不存在")
    try:
        skill = json.loads(path.read_text(encoding="utf-8"))
        template = skill.get("prompt_template", "")
        try:
            rendered = template.format(**req.parameters)
        except KeyError as exc:
            rendered = template
        return {
            "success": True,
            "skill_name": req.name,
            "rendered_prompt": rendered,
            "parameters": req.parameters,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"技能调用失败: {exc}")


@router.get("/list", operation_id="skill_list")
async def skill_list():
    """列出所有技能"""
    skills = []
    for path in SKILL_DIR.glob("*.json"):
        try:
            skill = json.loads(path.read_text(encoding="utf-8"))
            skills.append({"name": skill.get("name"), "description": skill.get("description")})
        except Exception:
            continue
    return {"skills": skills}
