# 开发环境设置

## 环境要求

- Python 3.11+
- uv (Python 包管理器)

## 安装步骤

### 1. 安装 uv

```bash
# macOS
brew install uv

# 其他系统
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 同步依赖

```bash
uv sync
```

### 3. 配置环境变量

创建 `.env` 文件：

```env
# App
APP_NAME="TCM Study App"
DEBUG=true

# Database
DATABASE_URL=sqlite:///./tcm_study.db

# API Keys (可选)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
```

### 4. 初始化数据库

```bash
PYTHONPATH=backend/src python scripts/seed_demo_data.py
```

如果你本地已经有旧版 `tcm_study.db`，这一步前建议先确认是否需要重建。

原因：
- 当前项目启动使用 `Base.metadata.create_all(...)`
- 这会创建缺失的表，但不会给旧表自动补新列
- 本轮针灸导入重构新增了 `source_documents.source_book_key`、`book_section` 等字段，以及多张新表

如果你看到类似错误：

```bash
no such column: source_documents.source_book_key
```

本地开发建议直接重建 SQLite：

```bash
rm -f tcm_study.db
PYTHONPATH=backend/src python scripts/seed_demo_data.py
```

如果你要保留旧数据，就需要手动做 SQLite 迁移。

### 5. 启动开发服务器

```bash
./scripts/dev.sh
# 或
PYTHONPATH=backend/src uv run uvicorn tcm_study_app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 常用命令

```bash
# 运行测试
pytest

# 代码检查
ruff check backend/src

# 代码格式化
ruff format backend/src

# 类型检查
mypy backend/src
```

## API 文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
