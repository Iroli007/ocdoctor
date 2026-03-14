"""LLM service for AI-powered content generation."""
import json
from typing import Any

from tcm_study_app.config import settings


class LLMService:
    """Service for calling LLM APIs."""

    def __init__(self):
        self.openai_api_key = settings.openai_api_key
        self.anthropic_api_key = settings.anthropic_api_key

    def extract_formula_card(self, text: str) -> dict[str, Any]:
        """
        Extract formula card data from raw text using LLM.

        Input: raw text about a TCM formula
        Output: structured formula card data
        """
        prompt = f"""你是一个中医助手。请从以下文本中提取方剂信息，结构化为JSON格式。

输入文本：
{text}

请提取以下字段：
- formula_name: 方剂名称
- composition: 药物组成
- effect: 功效
- indication: 主治
- pathogenesis: 病机(如果有)
- usage_notes: 用法要点(如果有)
- memory_tip: 记忆提示(如果有)

请返回纯JSON，不要其他内容。"""

        # For MVP, return mock data if no API key
        if not self.openai_api_key and not self.anthropic_api_key:
            return self._mock_extract_formula(text)

        # TODO: Implement actual LLM call
        return self._mock_extract_formula(text)

    def generate_comparison(
        self, left_entity: str, right_entity: str, context: str | None = None
    ) -> dict[str, Any]:
        """Generate comparison between two entities."""
        prompt = f"""你是一个中医助手。请比较以下两个方剂的异同。

左方剂：{left_entity}
右方剂：{right_entity}
{"上下文：" + context if context else ""}

请返回JSON格式，包含：
- left_entity: 左方剂名称
- right_entity: 右方剂名称
- comparison_points: 比较点数组，每个包含dimension(比较维度)、left(左方剂特点)、right(右方剂特点)
- question_text: 比较题问题
- answer_text: 比较题答案

请返回纯JSON，不要其他内容。"""

        # For MVP, return mock data
        return self._mock_generate_comparison(left_entity, right_entity)

    def generate_quiz(
        self, card_content: dict[str, Any], difficulty: str = "medium"
    ) -> dict[str, Any]:
        """Generate quiz question from card content."""
        prompt = f"""你是一个中医助手。请根据以下知识卡片生成一道测试题。

知识卡片内容：
{json.dumps(card_content, ensure_ascii=False)}

难度：{difficulty}

请返回JSON格式，包含：
- type: 题目类型(choice/true_false/recall)
- question: 问题
- options: 选项数组(如果是选择题)
- answer: 答案
- explanation: 解释

请返回纯JSON，不要其他内容。"""

        # For MVP, return mock data
        return self._mock_generate_quiz(card_content, difficulty)

    def _mock_extract_formula(self, text: str) -> dict[str, Any]:
        """Mock extraction for MVP."""
        # Simple pattern matching for demo
        import re

        # Try to extract formula name from text
        name_match = re.search(r"([\u4e00-\u9fa5]+方)", text)
        formula_name = name_match.group(1) if name_match else "未知方剂"

        # Try to extract composition
        comp_match = re.search(
            r"组成[：:]([^\n。]+)", text
        ) or re.search(r"药物[：:]([^\n。]+)", text)
        composition = comp_match.group(1) if comp_match else None

        # Try to extract effect
        effect_match = re.search(
            r"功效[：:]([^\n。]+)", text
        ) or re.search(r"功能[：:]([^\n。]+)", text)
        effect = effect_match.group(1) if effect_match else None

        # Try to extract indication
        ind_match = re.search(
            r"主治[：:]([^\n。]+)", text
        ) or re.search(r"适应症[：:]([^\n。]+)", text)
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
                {
                    "dimension": "共同点",
                    "left": "同属解表剂",
                    "right": "同属解表剂",
                },
                {
                    "dimension": "表证类型",
                    "left": "表虚证",
                    "right": "表实证",
                },
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
