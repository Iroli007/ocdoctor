# TCM Study App - 中医学习工具

一个面向中医学生的 Web/PWA 学习工具，帮助用户把教材划线内容、讲义内容或手工输入内容，自动转成可复习的知识卡片、比较题和小测题。

## 功能特性

- **文本导入**: 支持粘贴文本或上传图片进行 OCR 识别
- **智能卡片生成**: 自动从文本中提取方剂信息，生成结构化知识卡片
- **比较题生成**: 自动生成相似方剂的比较题
- **小测生成**: 自动生成选择题、判断题等测试题
- **复习记录**: 记录学习进度和错题

## 技术栈

- **后端**: FastAPI + SQLAlchemy + SQLite
- **依赖管理**: uv
- **AI**: OpenAI/Anthropic (可选，未配置时使用规则引擎)

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 初始化数据库

```bash
# 创建演示数据
PYTHONPATH=backend/src python scripts/seed_demo_data.py
```

### 3. 启动服务

```bash
# 方式1: 使用脚本
./scripts/dev.sh

# 方式2: 手动启动
PYTHONPATH=backend/src uv run uvicorn tcm_study_app.main:app --host 0.0.0.0 --port 8000
```

### 4. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构

```
tcm-study-app/
├── pyproject.toml          # 项目配置
├── uv.lock                # 依赖锁定文件
├── .python-version         # Python 版本
├── README.md               # 项目说明
├── backend/
│   └── src/
│       └── tcm_study_app/
│           ├── __init__.py
│           ├── main.py             # FastAPI 应用入口
│           ├── config.py           # 配置
│           ├── api/                # API 路由
│           │   ├── routes_health.py
│           │   ├── routes_import.py
│           │   ├── routes_cards.py
│           │   ├── routes_quiz.py
│           │   └── routes_review.py
│           ├── core/               # 核心模块
│           ├── models/             # 数据库模型
│           │   ├── user.py
│           │   ├── collection.py
│           │   ├── source_document.py
│           │   ├── knowledge_card.py
│           │   ├── formula_card.py
│           │   ├── comparison_item.py
│           │   ├── quiz.py
│           │   └── review_record.py
│           ├── schemas/            # Pydantic schemas
│           ├── services/           # 业务逻辑
│           │   ├── llm_service.py
│           │   ├── ocr_service.py
│           │   ├── card_generator.py
│           │   ├── comparison_generator.py
│           │   ├── quiz_generator.py
│           │   └── review_service.py
│           ├── db/                # 数据库
│           │   ├── base.py
│           │   └── session.py
│           └── tests/              # 测试
├── docs/                       # 项目文档
│   ├── 00-project-brief.md
│   ├── 01-product-requirements.md
│   ├── 02-architecture.md
│   ├── 03-data-model.md
│   ├── 04-api-contract.md
│   ├── 05-prompts.md
│   ├── 06-dev-setup.md
│   └── 07-roadmap.md
└── scripts/
    ├── dev.sh
    ├── format.sh
    └── seed_demo_data.py
```

## API 端点

### 健康检查
- `GET /health` - 健康检查

### 导入
- `POST /api/import/text` - 导入文本
- `POST /api/import/image` - 上传图片
- `POST /api/import/ocr/correct` - 修正 OCR 结果

### 卡片
- `GET /api/cards` - 获取卡片列表
- `GET /api/cards/{card_id}` - 获取单个卡片
- `POST /api/cards/generate` - 生成卡片

### 比较题
- `POST /api/comparisons/generate` - 生成比较题
- `GET /api/comparisons` - 获取比较题列表

### 小测
- `POST /api/quizzes/generate` - 生成小测题
- `GET /api/quizzes` - 获取小测题列表

### 复习
- `POST /api/reviews/submit` - 提交复习结果
- `GET /api/reviews/stats/{user_id}` - 获取复习统计
- `GET /api/reviews/due/{user_id}` - 获取待复习项目
- `GET /api/reviews/wrong/{user_id}` - 获取错题

## 环境变量

在项目根目录创建 `.env` 文件：

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

## 开发说明

### 代码风格
- 使用 ruff 进行代码检查和格式化
- 遵循 PEP 8 规范

### 运行测试
```bash
pytest
```

## Split Large PDFs

When a PDF is too large for the current web upload path, split it by chapter-like
page ranges first.

1. Create a JSON spec such as:

```json
{
  "parts": [
    { "title": "Warm Disease Overview", "start_page": 1, "end_page": 24 },
    { "title": "Wei-Qi-Ying-Xue", "start_page": 25, "end_page": 46 },
    { "title": "Triple Burner Differentiation", "start_page": 47, "end_page": 68 }
  ]
}
```

2. Run:

```bash
uv run python scripts/split_pdf.py \
  /path/to/source.pdf \
  --spec /path/to/split-spec.json \
  --output-dir /path/to/output \
  --overlap-pages 1
```

This will emit files like `01_Warm_Disease_Overview.pdf`, `02_Wei-Qi-Ying-Xue.pdf`.
Use `--dry-run` first if you want to inspect the plan without writing files.

## OCR Scanned PDFs Locally

For scanned textbook PDFs, run OCR locally and upload the extracted page text to the
hosted app instead of trying to OCR inside a serverless request.

1. The project now defaults to Python 3.13 so local PaddleOCR stays compatible.
2. Install the optional OCR group:

```bash
uv sync --group ocr
```

3. OCR one split PDF or a whole split directory and upload it:

```bash
uv run --group ocr python scripts/import_scanned_pdf.py \
  "/path/to/split-pdfs" \
  --collection-id 12 \
  --api-base https://iroli1.online
```

This uses local PaddleOCR for recognition and then sends the page text to
`POST /api/import/ocr-pages`, so the hosted app only receives plain OCR text and
can still keep page-aware chunk citations.
