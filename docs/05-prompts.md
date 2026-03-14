# Prompt 设计文档

## 卡片生成 Prompt

### 输入
- 原始文本
- 学科类型：方剂学

### 输出格式 (JSON)
```json
{
  "formula_name": "桂枝汤",
  "composition": "桂枝、芍药、生姜、大枣、甘草",
  "effect": "解肌发表，调和营卫",
  "indication": "外感风寒表虚证",
  "pathogenesis": "风寒外袭，营卫不和",
  "usage_notes": "服药后啜热粥以助药力",
  "memory_tip": "桂枝+芍药 = 调和营卫"
}
```

## 比较题 Prompt

### 输入
- 左方剂名称
- 右方剂名称
- 上下文（可选）

### 输出格式 (JSON)
```json
{
  "left_entity": "桂枝汤",
  "right_entity": "麻黄汤",
  "comparison_points": [
    {
      "dimension": "表证特点",
      "left": "表虚",
      "right": "表实"
    }
  ],
  "question_text": "请比较桂枝汤与麻黄汤的异同",
  "answer_text": "桂枝汤主治表虚证..."
}
```

## 小测题 Prompt

### 输入
- 知识卡片内容
- 难度级别：easy / medium / hard

### 输出格式 (JSON)
```json
{
  "type": "choice",
  "question": "以下哪项是桂枝汤的组成？",
  "options": [
    {"key": "A", "value": "桂枝、芍药、生姜、大枣、甘草"},
    {"key": "B", "value": "麻黄、桂枝、杏仁、甘草"},
    {"key": "C", "value": "人参、白术、茯苓、甘草"},
    {"key": "D", "value": "以上都不是"}
  ],
  "answer": "A",
  "explanation": "桂枝汤的组成是..."
}
```

## 错误兜底策略

1. 如果 LLM 无法解析，返回占位数据
2. 使用正则表达式做基础提取
3. 用户可以手动编辑结果
