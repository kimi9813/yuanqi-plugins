"""
函数计算入口（Serverless / FaaS）。

支持：
- 阿里云函数计算 FC（HTTP 函数）
- 腾讯云 SCF（API 网关触发器）
- AWS Lambda（API Gateway）
- 其他兼容 Lambda/ASGI 的事件入口

本地开发仍使用 `python app.py`，函数计算平台直接指定本文件中的 handler。
"""
from mangum import Mangum

from app import app

# 通用 ASGI handler，适用于阿里云 FC、AWS Lambda 等
handler = Mangum(app, lifespan="off")

# 阿里云函数计算 HTTP 函数默认入口
fc_handler = handler

# 腾讯云 SCF / API 网关触发器入口
def main_handler(event, context):
    """
    腾讯云 SCF 标准入口。
    事件结构参考：https://cloud.tencent.com/document/product/583/12513
    """
    return handler(event, context)
