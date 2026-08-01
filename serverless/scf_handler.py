"""
腾讯云云函数 SCF 专用入口。

部署时函数配置：
- 运行环境：Python 3.10 / Python 3.11
- 执行方法：serverless.scf_handler.main_handler
- 触发方式：API 网关触发
"""
from mangum import Mangum

from app import app

handler = Mangum(app, lifespan="off")


def main_handler(event, context):
    """SCF 标准入口函数。"""
    return handler(event, context)
