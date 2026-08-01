# Serverless / 函数计算部署

本项目已内置函数计算入口，可将 FastAPI 应用一键部署到常见 FaaS 平台。

## 入口文件

| 平台 | 入口文件 | 处理函数 |
|------|----------|----------|
| 阿里云 FC | `handler.py` | `handler` |
| 腾讯云 SCF | `handler.py` 或 `serverless/scf_handler.py` | `main_handler` |
| AWS Lambda | `handler.py` | `handler` |

## 依赖

函数计算平台安装依赖时统一使用根目录 `requirements.txt`，其中已包含 `mangum`。

## 注意事项

1. **持久化存储**：函数计算实例是无状态的，文件上传、技能、任务数据在实例回收后会丢失。
   - 阿里云 FC：建议挂载 NAS 或改用 OSS/Tablestore。
   - 腾讯云 SCF：建议挂载 CFS 或改用 COS。
   - 对于测试场景可直接使用，生产场景请替换为数据库存储。

2. **超时设置**：函数计算默认超时较短，建议在平台后台将超时时间设置为 30-60 秒以上。

3. **内存设置**：文件转换、网页抓取较耗内存，建议初始内存设置为 512MB 或 1GB。

4. **生命周期**：`handler.py` 中使用 `lifespan="off"`，因为函数计算实例通常不会长期保留 ASGI lifespan 状态。
