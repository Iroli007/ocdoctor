"""LLM service for AI-powered content generation."""
import json
import re
from typing import Any

from tcm_study_app.config import settings


class LLMService:
    """Service for calling LLM APIs."""

    def __init__(self):
        self.openai_api_key = settings.openai_api_key
        # 优先使用系统环境变量的 auth_token，否则用配置文件的 api_key
        self.anthropic_api_key = settings.anthropic_auth_token or settings.anthropic_api_key
        self.api_base = settings.anthropic_base_url

    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        """Call Anthropic API."""
        import httpx

        headers = {
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self.api_base}/v1/messages",
                headers=headers,
                json=data,
            )
            response.raise_for_status()
            result = response.json()
            return result["content"][0]["text"]

    def extract_formula_card(self, text: str) -> dict[str, Any]:
        """
        Extract formula card data from raw text using LLM.
        """
        system_prompt = """你是一个中医助手。请从文本中提取方剂信息，返回纯JSON格式。"""

        user_prompt = f"""从以下文本中提取方剂信息：

{text}

请返回以下格式的JSON（只返回JSON，不要其他内容）：
{{
  "formula_name": "方剂名称",
  "composition": "药物组成",
  "effect": "功效",
  "indication": "主治",
  "pathogenesis": "病机(如果没有则null)",
  "usage_notes": "用法要点(如果没有则null)",
  "memory_tip": "记忆提示(如果没有则null)"
}}"""

        # Use Anthropic API if key is available
        if self.anthropic_api_key:
            try:
                result = self._call_anthropic(system_prompt, user_prompt)
                # Extract JSON from response
                json_match = re.search(r"\{.*\}", result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                print(f"Anthropic API error: {e}")

        # Fallback to mock
        return self._mock_extract_formula(text)

    def generate_comparison(
        self, left_entity: str, right_entity: str, context: str | None = None
    ) -> dict[str, Any]:
        """Generate comparison between two entities."""
        system_prompt = """你是一个中医助手。请比较两个方剂的异同，返回纯JSON格式。"""

        user_prompt = f"""请比较以下两个方剂的异同：

左方剂：{left_entity}
右方剂：{right_entity}
{f"上下文：{context}" if context else ""}

请返回以下格式的JSON：
{{
  "left_entity": "左方剂名称",
  "right_entity": "右方剂名称",
  "comparison_points": [
    {{"dimension": "比较维度", "left": "左方剂特点", "right": "右方剂特点"}}
  ],
  "question_text": "比较题问题",
  "answer_text": "比较题答案"
}}"""

        if self.anthropic_api_key:
            try:
                result = self._call_anthropic(system_prompt, user_prompt)
                json_match = re.search(r"\{.*\}", result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                print(f"Anthropic API error: {e}")

        return self._mock_generate_comparison(left_entity, right_entity)

    def generate_quiz(
        self, card_content: dict[str, Any], difficulty: str = "medium"
    ) -> dict[str, Any]:
        """Generate quiz question from card content."""
        system_prompt = """你是一个中医助手。请根据知识卡片生成测试题，返回纯JSON格式。"""

        user_prompt = f"""根据以下知识卡片生成一道测试题：

{json.dumps(card_content, ensure_ascii=False)}

难度：{difficulty}

请返回以下格式的JSON：
{{
  "type": "choice",
  "question": "问题",
  "options": [{{"key": "A", "value": "选项1"}}, {{"key": "B", "value": "选项2"}}],
  "answer": "A",
  "explanation": "解释"
}}"""

        if self.anthropic_api_key:
            try:
                result = self._call_anthropic(system_prompt, user_prompt)
                json_match = re.search(r"\{.*\}", result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                print(f"Anthropic API error: {e}")

        return self._mock_generate_quiz(card_content, difficulty)

    def _mock_extract_formula(self, text: str) -> dict[str, Any]:
        """Mock extraction for MVP."""
        # Try to extract formula name from text
        name_match = re.search(r"([\u4e00-\u9fa5]+方)", text)
        formula_name = name_match.group(1) if name_match else "未知方剂"

        # Try to extract composition
        comp_match = re.search(r"组成[：:]([^\n。]+)", text)
        composition = comp_match.group(1) if comp_match else None

        # Try to extract effect
        effect_match = re.search(r"功效[：:]([^\n。]+)", text)
        effect = effect_match.group(1) if effect_match else None

        # Try to extract indication
        ind_match = re.search(r"主治[：:]([^\n。]+)", text)
        indication = ind_match.group(1) if ind_match else None

        return {
            "formula_name": formula_name,
            "composition": composition,
            "effect": effect,
            "indication": indication,
            "pathogenesis": None,
            "usage_notes": None,
            "memory_tip": None,
        }

    def _mock_generate_comparison(
        self, left: str, right: str
    ) -> dict[str, Any]:
        """Mock comparison for MVP."""
        return {
            "left_entity": left,
            "right_entity": right,
            "comparison_points": [
                {"dimension": "共同点", "left": "同属解表剂", "right": "同属解表剂"},
                {"dimension": "表证类型", "left": "表虚证", "right": "表实证"},
            ],
            "question_text": f"请比较{left}与{right}的异同",
            "answer_text": f"{left}主治表虚证，{right}主治表实证...",
        }

    def _mock_generate_quiz(
        self, card: dict[str, Any], difficulty: str
    ) -> dict[str, Any]:
        """Mock quiz generation for MVP."""
        return {
            "type": "choice",
            "question": f"以下哪项是{card.get('formula_name', '该方剂')}的组成？",
            "options": [
                {"key": "A", "value": "桂枝、芍药、生姜、大枣、甘草"},
                {"key": "B", "value": "麻黄、桂枝、杏仁、甘草"},
                {"key": "C", "value": "人参、白术、茯苓、甘草"},
                {"key": "D", "value": "以上都不是"},
            ],
            "answer": "A",
            "explanation": f"{card.get('formula_name', '该方剂')}的组成是...",
        }


llm_service = LLMService()
