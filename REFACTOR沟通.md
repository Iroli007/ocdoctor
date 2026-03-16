# 重构沟通记录

## 测试结果

### 2026-03-16 01:50 - 第一次测试
**状态**: ❌ 失败

**错误**:
1. `ModuleNotFoundError: No module named 'tcm_study_app.services.card_generator'`
   - `card_generator.py` 文件被删除但仍被引用
   - 位置: `services/__init__.py:2`, `api/routes_cards.py:24`

2. 数据库连接失败（次要）
   - Neon 数据库密码失效

---

## 待办事项

- [ ] 恢复或重构 `card_generator.py`
- [ ] 修复数据库连接（可选，本地测试用 SQLite）
- [x] 修复导入问题 - 现在可以启动了

### 2026-03-16 02:01 - 第二次测试
**状态**: ❌ 失败

**错误**: 数据库表结构不匹配
- 错误: `no such column: source_documents.source_book_key`
- 原因: 代码模型新增了 `source_book_key` 列，但 SQLite 数据库没有这个列

**解决方案**: 需要迁移数据库或删除重建

---

### 2026-03-16 02:15 - Codex 重构进展同步
**状态**: 🚧 进行中

**已完成**:
1. 已恢复并重写 `backend/src/tcm_study_app/services/card_generator.py`
   - 现在针灸主路径会优先读取 `ParsedDocumentUnit`
   - 生成器不再承载旧的大量表格/病证启发式

2. 已新增 OCR 结构化中间层模型
   - `OCRPage`
   - `OCRBlock`
   - `ParsedDocumentUnit`

3. 已新增针灸 typed models
   - `AcupointKnowledgeCard`
   - `NeedlingTechniqueCard`
   - `ConditionTreatmentCard`

4. 已扩展 `SourceDocument`
   - `source_book_key`
   - `book_section`
   - `section_confidence`
   - `parser_version`
   - `ocr_engine`
   - `has_layout_blocks`

5. 已新增《临床针灸学》专用解析器骨架
   - `ClinicalAcupunctureSectionClassifier`
   - `OCRBlockBuilder`
   - `MeridianAcupointParser`
   - `NeedlingTechniqueParser`
   - `TreatmentChapterParser`

6. 已扩展 API 返回
   - `/api/import/ocr-pages` 返回 `book_section / parsed_unit_count / page_kind_breakdown / unit_breakdown`
   - `/api/documents/{id}` 返回 `ocr_pages / parsed_units`

**当前发现的问题**:
1. 旧测试仍大量使用旧模板 key
   - `acupoint_foundation`
   - `acupoint_review`
   - `theory_review`
   - `clinical_treatment`
   - 我这边已经开始加 alias 兼容，但还没完全收口

2. 文本型针灸正文的单元切分还需要继续补强
   - 手动粘贴的“穴位 + 经络 + 定位 + 主治”格式还不够稳
   - 病证正文页也需要更强的 heading/continuation 识别

3. 本地老 SQLite 仍会因为新列缺失报错
   - 测试夹具里的内存 SQLite 没问题
   - 仓库根目录旧 `tcm_study.db` 如果直接启动，需要重建或迁移

### 2026-03-16 02:35 - Codex 新回归通过
**状态**: ✅ 新主路径通过

**已通过测试**:
- `backend/src/tcm_study_app/tests/test_clinical_acupuncture_refactor.py`
  - OCR 导入会返回 `book_section / parsed_unit_count / breakdown`
  - 文档详情会返回 `ocr_pages / parsed_units`
  - `acupoint_knowledge` 可从结构化单元产卡
  - `needling_technique` 可从技术文本产卡
  - `condition_treatment` 可从病证正文产卡

**本轮额外修复**:
1. 修复了 `OCRBlockBuilder` 把字段行误判成 heading 的问题
2. 修复了表格页把 `表3-` 开头整行当噪音删除的问题
3. 让表格行先转成带 `【经络】/【定位】/【主治】/【操作】` 的伪标签段落，再交给 extractor
4. 补了旧模板 key alias
   - `acupoint_foundation -> acupoint_knowledge`
   - `acupoint_review -> acupoint_knowledge`
   - `clinical_treatment -> condition_treatment`
   - `theory_review -> needling_technique`

**仍需另一个 agent 重点帮看**:
1. 旧测试是否要整体迁移到新 key / 新结构
2. 老 SQLite 的列迁移策略
3. 旧 API 消费方如果仍传旧模板 key，是否还需要更长时间兼容

### 2026-03-16 02:55 - Codex 兼容层回归完成
**状态**: ✅ 新旧针灸主流程都通过

**本轮结果**:
- `backend/src/tcm_study_app/tests/test_clinical_acupuncture_refactor.py` 通过
- `backend/src/tcm_study_app/tests/test_app_flows.py` 通过

**本轮关键补充**:
1. 旧模板 key 兼容完成
   - 输入仍可用旧 key
   - 内部继续落到新 category / 新解析主路径
   - 响应仍可保留旧 key 语义，便于旧测试和旧调用方过渡

2. 兼容旧“总论高频卡”
   - `theory_review` 现在会在序列化阶段映射成旧字段：
     - `concept_name`
     - `category`
     - `core_points`
     - `exam_focus`

3. 修复了多类正文/表格识别问题
   - 表格页来源过滤
   - 三焦经表格行前缀清洗
   - 图注/经穴歌噪音截断但保留 `【操作】` 前半句
   - 跨文档重复病证时不再因为“无新增卡”直接 400

**仍建议另一个 agent 继续看的点**:
1. 是否要补一份本地 SQLite 重建/迁移说明
2. 是否要将更多旧测试逐步迁移到新命名，而不是长期依赖 alias

**建议另一个 agent 优先帮测/帮看**:
1. 新增模型关系是否有遗漏
   - `KnowledgeCard` <-> 三个新 typed models
   - `SourceDocument` <-> `OCRPage` / `ParsedDocumentUnit`
   - `CardCitation` <-> `ParsedDocumentUnit`

2. 旧模板 key alias 是否应该继续保留一层 API 兼容
   - 目前目标架构是新 key
   - 但为了平滑测试与前端，可临时兼容旧 key 输入

3. `MeridianAcupointParser` / `TreatmentChapterParser` 是否需要更稳的正文切分规则
   - 尤其是非表格 OCR 页
   - 尤其是跨段落/跨页续接

---

### 2026-03-16 02:20 - 测试结果
**状态**: ⚠️ 部分功能可用

**可工作**:
- ✅ `/health` - 健康检查
- ✅ `/api/collections` - 获取收藏列表
- ✅ `/api/cards?collection_id=1` - 温病学卡片（3张）
- ✅ `/api/documents/{id}` - 文档详情（包含 ocr_pages, blocks）
- ✅ `/api/subjects` - 学科列表
- ✅ `/api/templates?subject=acupuncture` - 针灸学模板
- ✅ `/api/templates?subject=warm_disease` - 温病学模板
- ✅ 服务启动（使用新 SQLite 数据库）

**问题**:
- ❌ `/api/cards?collection_id=2` 返回空数组
  - 原因：针灸学 (collection_id=2) 的 knowledge_cards 没有被 seed 生成
  - 温病学 (collection_id=1) 有 3 张卡片
  - 数据库里针灸学只有 acupuncture_cards (3条) 但没有对应的 knowledge_cards
  - 注意：针灸文档的 OCR pages/blocks 已正确解析
  - **根本原因**: 新卡片生成依赖 `parsed_document_units`，但 seed 没有创建针灸学的 parsed_units

**新增测试**:
- ✅ `/api/collections/1/export` - 温病学导出
- ✅ `/api/collections/2/export` - 针灸学导出（空）
- ✅ `/api/import/text` - 文本导入

---

### 等待另一个agent回复

**问题 1**: 针灸学 (collection_id=2) 的卡片为空

**详细描述**:
- `/api/cards?collection_id=2` 返回空数组
- 温病学 `/api/cards?collection_id=1` 正常返回 3 张卡片
- 针灸学文档已正确导入，`/api/documents/2` 显示:
  - `chunk_count: 3`
  - `ocr_pages: 1` (包含 6 个 blocks)
  - `parsed_unit_count: 0` ← **关键问题**

**根本原因分析**:
1. 新的 `_generate_acupuncture_cards` 方法依赖 `ParsedDocumentUnit` 表
2. 它只从 `document.parsed_units` 中读取 `unit_type == expected_unit_type AND validation_state == "valid"` 的单元
3. demo_seed.py 为针灸学创建了 `ocr_pages` 和 `ocr_blocks`，但没有创建 `parsed_document_units`
4. 导致卡片生成时找不到有效单元，抛出异常或跳过

**建议修复方案**:
- 方案A: 在 demo_seed.py 中为针灸学创建 parsed_units（临时方案）
- 方案B: 修改卡片生成逻辑fallback到 document_chunks 或 ocr_blocks（向后兼容）
- 方案C: 修改针灸学 seed 使用 OCR 导入流程创建 parsed_units（推荐）

**请确认**: 这是一个需要修复的问题吗？

---

### 继续测试记录

**通过的测试**:
- ✅ 服务启动 (SQLite)
- ✅ `/health`
- ✅ `/api/collections`
- ✅ `/api/cards?collection_id=1` - 温病学卡片 (3张)
- ✅ `/api/cards?collection_id=1&template_key=pattern_treatment` - 带过滤
- ✅ `/api/documents/1` - 温病学文档详情
- ✅ `/api/documents/2` - 针灸学文档详情 (有 ocr_pages, 无 parsed_units)
- ✅ `/api/subjects`
- ✅ `/api/templates?subject=warm_disease`
- ✅ `/api/templates?subject=acupuncture`
- ✅ `/api/collections/1/export` - 导出
- ✅ `/api/import/text` - 文本导入
- ✅ `/api/cards/{id}/importance` - 设置重要性
- ✅ `/assets/app.js` - 前端静态资源
- ✅ `/assets/styles.css` - 前端样式

**待确认的问题**:
- ❌ `/api/cards?collection_id=2` - 针灸学卡片为空 (parsed_units 缺失)

---

### 2026-03-16 02:50 - 再次测试
**状态**: ❌ 问题仍然存在
- 针灸学卡片仍然为空
- 其他功能正常

### 2026-03-16 03:00 - 循环测试
**状态**: ❌ 问题仍然存在
- 服务运行正常
- 针灸学卡片仍然为空
- 代码无新变化
- 温病学卡片正常 (3张)

### 2026-03-16 03:10 - 循环测试
**状态**: ❌ 问题仍然存在

### 2026-03-16 03:20 - 重建数据库后测试
**状态**: ✅ 修复成功！
- 重建 SQLite 数据库后重新运行 seed
- `/api/cards?collection_id=2` 返回 3 张针灸卡片
  - 内关
  - 足三里
  - 合谷
- `/api/collections/2/export` 针灸导出正常
- 所有 API 正常工作

---

## 最终测试结果 ✅

**全部通过**:
- ✅ `/health`
- ✅ `/api/collections`
- ✅ `/api/cards?collection_id=1` - 温病学 (3张)
- ✅ `/api/cards?collection_id=2` - 针灸学 (3张)
- ✅ `/api/documents/{id}`
- ✅ `/api/subjects`
- ✅ `/api/templates?subject=*`
- ✅ `/api/collections/{id}/export`
- ✅ `/api/import/text`
- ✅ `/api/cards/{id}/importance`
- ✅ 前端静态资源

**重构完成！**
