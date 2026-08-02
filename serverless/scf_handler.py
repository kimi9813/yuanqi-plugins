"""
腾讯云云函数 SCF 专用入口。

部署时函数配置（二选一）：
1. Web 函数：
   - 运行环境：Python 3.10 / Python 3.9
   - 执行方法：serverless.scf_handler.app
2. 事件函数 + API 网关触发：
   - 运行环境：Python 3.10 / Python 3.9
   - 执行方法：serverless.scf_handler.main_handler
   - 触发方式：API 网关触发
"""
from mangum import Mangum

from app import app

# Web 函数直接暴露 ASGI app
# 执行方法填：serverless.scf_handler.app

# 事件函数入口（API 网关触发）
handler = Mangum(app, lifespan="off")


def main_handler(event, context):
    """SCF 事件函数标准入口。"""
    return handler(event, context)
