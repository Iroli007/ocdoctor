# Review Task Template

把下面这段填好后直接发给 Codex，就能更快进入测试和修复。

```text
Review the current branch against the target baseline.

Focus on:
- correctness
- edge cases for import, card generation, quiz, and review flows
- schema and API contract mismatches
- missing error handling
- smallest safe patch only

Run:
- UV_CACHE_DIR=/tmp/uv-cache-ocdoctor PYTHONPATH=backend/src uv run pytest -q

Return:
1. findings ranked by severity
2. minimal patch plan
3. exact files to edit
4. tests run and remaining risks
```

如果本次只测局部模块，可以把 `Focus on` 换成更具体的范围，例如：
- `routes_import.py` + OCR related services
- card generation and formula extraction
- review statistics and due-item logic
