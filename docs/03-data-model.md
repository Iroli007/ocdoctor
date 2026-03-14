# 数据模型文档

## 核心实体

### User
用户表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| email | String(255) | 邮箱，唯一 |
| name | String(100) | 用户名 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### StudyCollection
学习集合，如"方剂学-解表剂"

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 外键 -> User |
| title | String(255) | 集合标题 |
| subject | String(100) | 学科，默认"方剂学" |
| description | Text | 描述 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### SourceDocument
导入来源

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| collection_id | Integer | 外键 -> StudyCollection |
| type | String(20) | 类型：text / image |
| raw_text | Text | 原始文本 |
| image_url | String(500) | 图片URL |
| ocr_text | Text | OCR识别文本 |
| status | String(20) | 状态：pending / processed / failed |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### KnowledgeCard
核心知识卡片

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| collection_id | Integer | 外键 -> StudyCollection |
| source_document_id | Integer | 外键 -> SourceDocument |
| title | String(255) | 卡片标题 |
| category | String(50) | 类别：formula / comparison / quiz_basis |
| raw_excerpt | Text | 原始摘录 |
| normalized_content_json | Text | 结构化内容JSON |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### FormulaCard
方剂学专用结构化表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| knowledge_card_id | Integer | 外键 -> KnowledgeCard，唯一 |
| formula_name | String(100) | 方剂名称 |
| composition | Text | 药物组成 |
| effect | Text | 功效 |
| indication | Text | 主治 |
| pathogenesis | Text | 病机 |
| usage_notes | Text | 用法要点 |
| memory_tip | Text | 记忆提示 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### ComparisonItem
比较题

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| collection_id | Integer | 外键 -> StudyCollection |
| left_entity | String(100) | 左边实体 |
| right_entity | String(100) | 右边实体 |
| comparison_points_json | Text | 比较点JSON |
| question_text | Text | 问题文本 |
| answer_text | Text | 答案文本 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### Quiz
小测题

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| collection_id | Integer | 外键 -> StudyCollection |
| type | String(20) | 类型：choice / true_false / recall |
| question | Text | 问题 |
| options_json | Text | 选项JSON |
| answer | String(10) | 答案 |
| explanation | Text | 解释 |
| difficulty | String(20) | 难度：easy / medium / hard |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### ReviewRecord
复习记录

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| user_id | Integer | 外键 -> User |
| target_type | String(20) | 目标类型：card / quiz / comparison |
| target_id | Integer | 目标ID |
| result | String(20) | 结果：correct / wrong / skipped |
| response | Text | 用户回答 |
| reviewed_at | DateTime | 复习时间 |
