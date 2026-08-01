"""
阿里云函数计算 FC 专用入口。

部署时函数配置：
- 函数类型：HTTP 函数
- 运行环境：Python 3.10 / Python 3.11
- 请求处理程序：serverless.fc_handler.handler
"""
from mangum import Mangum

from app import app

handler = Mangum(app, lifespan="off")
