# yuanqi-plugins Dockerfile
# 基于 Python 3.11 轻量镜像
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（部分文件转换需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    default-jdk \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 创建数据目录
RUN mkdir -p data/files data/skills data/tasks

# 默认暴露 8000，可通过环境变量 PORT 修改
EXPOSE 8000
ENV PORT=8000

# 启动命令
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT}
