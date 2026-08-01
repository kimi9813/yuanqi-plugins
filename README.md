# yuanqi-plugins

腾讯元器（Tencent Yuanqi）智能体插件集合，基于 FastAPI 实现，统一挂载在 `app.py` 中。

## 插件清单

| 插件 | 路由前缀 | 工具数 | 说明 |
|------|---------|-------|------|
| web_tool | `/web` | 2 | 网页搜索、网页内容提取与安全检测 |
| file_tool | `/file` | 2 | 文件上传/读取与多格式转换 |
| terminal_tool | `/terminal` | 4 | Python / Java / Shell 执行与文件编辑 |
| skill_tool | `/skill` | 2 | 技能创建与调用 |
| agent_task | `/agent` | 1 | Agent 任务管理 + 可视化小部件 |

## 快速开始

```bash
pip install -r requirements.txt
python app.py
```

服务默认运行在 `http://0.0.0.0:8000`。

## 运行方式

- 访问根路径查看插件列表：`GET /`
- 健康检查：`GET /health`
- Agent 任务小部件：`/widget/`
- API 文档：`/docs`

## 插件 OpenAPI 规范

每个插件的 OpenAPI 3.0 规范位于 `specs/` 目录，可用于注册到腾讯元器插件中心：

- `specs/web_tool_openapi.yaml`
- `specs/file_tool_openapi.yaml`
- `specs/terminal_tool_openapi.yaml`
- `specs/skill_tool_openapi.yaml`
- `specs/agent_task_openapi.yaml`

## 部署说明

详细部署方法见 [`docs/部署方法.docx`](docs/部署方法.docx)（Word 版）或 [`docs/手机部署教程.md`](docs/手机部署教程.md)（手机纯文本版），包含以下 5 种方式：

1. **GitHub Codespaces**：零配置、免费，适合测试
2. **Render**：免费 Web Service，24/7 运行（推荐）
3. **Railway**：按量计费，启动快
4. **Fly.io**：全球边缘节点，容器化部署
5. **VPS + Docker**：最稳定，适合生产

项目已内置对应配置文件：

- `Dockerfile` / `docker-compose.yml` / `.dockerignore`
- `render.yaml`
- `railway.json`
- `fly.toml`

### 通用步骤

1. 部署到公网，获取 HTTPS 地址，例如 `https://your-app.example.com`
2. 将 `specs/*.yaml` 中的 `servers.url` 替换为实际地址，例如：
   ```yaml
   servers:
     - url: https://your-app.example.com/web
   ```
3. 在腾讯元器插件中心上传对应 YAML 文件完成注册。

### Docker 快速部署

```bash
docker compose up -d --build
```

服务监听 `http://localhost:8000`。
