# 测试接入手册

这份文档用于后续把测试、审查或最小修复任务直接交给 Codex。

## 当前基线
- 项目类型：FastAPI 后端 MVP
- 当前学科：方剂学
- 关键流程：导入、OCR、卡片生成、比较题、小测、复习
- 已验证命令：

```bash
UV_CACHE_DIR=/tmp/uv-cache-ocdoctor PYTHONPATH=backend/src uv run pytest -q
```

当前结果：
- `2 passed`
- 有 `pytest testpaths` 警告
- 有 Pydantic v2 的 `class Config` 弃用警告
- 沙箱环境下 `.pytest_cache` 可能无法写入

## 交测试时最好一起提供
- 要测试的分支或提交范围
- 本次关注模块
- 是否允许修改测试文件
- 是否允许补最小修复 patch
- 是否有必须保留的数据库文件或演示数据
- 是否需要只测 API，不动模型层

## 建议的最小 Smoke 范围
1. 服务能启动，`/health` 和 `/` 正常返回。
2. 文本导入成功创建 `SourceDocument`。
3. 卡片生成能从文档生成 `KnowledgeCard` 和 `FormulaCard`。
4. 卡片列表接口返回结构与 schema 一致。
5. 比较题和 quiz 接口不会因为空数据或 JSON 解析异常直接崩溃。
6. 复习提交后，统计接口能反映结果。

## 本仓库最容易出问题的点
- 路由里直接抛 `ValueError`，可能导致非预期的 HTTP 500。
- OCR 图片流程依赖临时文件路径，环境变化时容易出错。
- schema、模型、API 文档三者可能逐步漂移。
- 目前测试覆盖很薄，改动 service 时容易漏掉回归。

## 如果后续加前端
等 Web 或移动端进入仓库后，新增测试时优先补：
- 导入到卡片生成的端到端 smoke
- 表单校验和错误态
- 响应式布局或移动端导航的最短路径回归
