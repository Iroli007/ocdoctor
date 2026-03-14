# API 契约文档

## 健康检查

### GET /health
健康检查

**响应:**
```json
{
  "status": "ok",
  "message": "TCM Study App is running"
}
```

## 导入 API

### POST /api/import/text
导入文本

**请求体:**
```json
{
  "collection_id": 1,
  "text": "桂枝汤：桂枝、芍药、生姜、大枣、甘草..."
}
```

**响应:**
```json
{
  "document_id": 1,
  "status": "pending"
}
```

### POST /api/import/image
上传图片并 OCR

**表单参数:**
- file: 图片文件
- collection_id: 集合ID

**响应:**
```json
{
  "document_id": 1,
  "ocr_text": "OCR结果...",
  "status": "pending"
}
```

### POST /api/import/ocr/correct
提交修正后的 OCR 结果

**请求体:**
```json
{
  "document_id": 1,
  "corrected_text": "修正后的文本..."
}
```

**响应:**
```json
{
  "status": "ok",
  "document_id": 1
}
```

## 卡片 API

### GET /api/cards
获取卡片列表

**查询参数:**
- collection_id: 集合ID (必填)

**响应:**
```json
[
  {
    "id": 1,
    "title": "桂枝汤",
    "category": "formula",
    "raw_excerpt": "组成：...",
    "formula_card": {
      "formula_name": "桂枝汤",
      "composition": "桂枝、芍药、生姜、大枣、甘草",
      "effect": "解肌发表，调和营卫",
      "indication": "外感风寒表虚证",
      "pathogenesis": "风寒外袭，营卫不和",
      "usage_notes": "服药后啜热粥以助药力",
      "memory_tip": "桂枝+芍药 = 调和营卫"
    },
    "created_at": "2026-03-14T10:00:00"
  }
]
```

### POST /api/cards/generate
生成知识卡片

**请求体:**
```json
{
  "document_id": 1
}
```

**响应:**
```json
{
  "cards": [...],
  "status": "generated"
}
```

## 比较题 API

### POST /api/comparisons/generate
生成比较题

**请求体:**
```json
{
  "collection_id": 1,
  "left_entity": "桂枝汤",
  "right_entity": "麻黄汤"
}
```

### GET /api/comparisons
获取比较题列表

**查询参数:**
- collection_id: 集合ID (必填)

## 小测 API

### POST /api/quizzes/generate
生成小测题

**请求体:**
```json
{
  "collection_id": 1,
  "count": 5,
  "difficulty": "medium"
}
```

### GET /api/quizzes
获取小测题列表

**查询参数:**
- collection_id: 集合ID (必填)
- limit: 限制数量，默认10

## 复习 API

### POST /api/reviews/submit
提交复习结果

**请求体:**
```json
{
  "user_id": 1,
  "target_type": "card",
  "target_id": 1,
  "result": "correct",
  "response": "A"
}
```

### GET /api/reviews/stats/{user_id}
获取复习统计

**响应:**
```json
{
  "total_reviews": 100,
  "correct_count": 80,
  "wrong_count": 15,
  "skipped_count": 5,
  "accuracy": 80.0
}
```

### GET /api/reviews/due/{user_id}
获取待复习项目

### GET /api/reviews/wrong/{user_id}
获取错题列表
