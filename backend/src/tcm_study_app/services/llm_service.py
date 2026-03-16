"""LLM service for AI-powered content generation."""
import json
import re
from typing import Any

from tcm_study_app.config import settings
from tcm_study_app.services.clinical_card_cleanup import clean_clinical_card_payload


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

    def extract_acupuncture_card(self, text: str) -> dict[str, Any]:
        """Extract acupuncture card data from raw text."""
        system_prompt = """你是一个中医针灸学助手。请从文本中提取穴位信息，返回纯JSON格式。"""

        user_prompt = f"""从以下文本中提取针灸学卡片信息：

{text}

请返回以下格式的JSON（只返回JSON，不要其他内容）：
{{
  "acupoint_name": "穴位名称",
  "meridian": "所属经络",
  "location": "定位",
  "indication": "主治",
  "technique": "刺灸法",
  "caution": "禁忌或注意事项(如果没有则null)"
}}"""

        if self.anthropic_api_key:
            try:
                result = self._call_anthropic(system_prompt, user_prompt)
                json_match = re.search(r"\{.*\}", result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                print(f"Anthropic API error: {e}")

        return self._mock_extract_acupuncture(text)

    def extract_acupuncture_clinical_card(self, text: str) -> dict[str, Any]:
        """Extract clinical acupuncture treatment data from raw text."""
        system_prompt = """你是一个中医针灸学助手。请从文本中提取病证治疗信息，返回纯JSON格式。"""

        user_prompt = f"""从以下文本中提取针灸临床卡片信息：

{text}

请返回以下格式的JSON（只返回JSON，不要其他内容）：
{{
  "disease_name": "病证名称",
  "treatment_principle": "治法或治疗原则",
  "acupoint_prescription": "处方或取穴要点",
  "notes": "辨证、操作或加减说明(如果没有则null)"
}}"""

        if self.anthropic_api_key:
            try:
                result = self._call_anthropic(system_prompt, user_prompt)
                json_match = re.search(r"\{.*\}", result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                print(f"Anthropic API error: {e}")

        return self._mock_extract_acupuncture_clinical(text)

    def extract_acupuncture_theory_card(self, text: str) -> dict[str, Any]:
        """Extract acupuncture theory/high-frequency review card data from raw text."""
        system_prompt = """你是一个中医针灸学助手。请从总论教材文本中提取高频复习卡，返回纯JSON格式。"""

        user_prompt = f"""从以下文本中提取针灸学总论高频卡信息：

{text}

请返回以下格式的JSON（只返回JSON，不要其他内容）：
{{
  "concept_name": "概念或考点名称",
  "category": "所属类别，如腧穴总论/刺灸法总论/治疗总论",
  "core_points": "定义、原则、特点或核心内容",
  "exam_focus": "期末高频考点或易混点(如果没有则null)"
}}"""

        if self.anthropic_api_key:
            try:
                result = self._call_anthropic(system_prompt, user_prompt)
                json_match = re.search(r"\{.*\}", result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                print(f"Anthropic API error: {e}")

        return self._mock_extract_acupuncture_theory(text)

    def extract_warm_disease_card(self, text: str) -> dict[str, Any]:
        """Extract warm disease card data from raw text."""
        system_prompt = """你是一个温病学助手。请从文本中提取证候信息，返回纯JSON格式。"""

        user_prompt = f"""从以下文本中提取温病学卡片信息：

{text}

请返回以下格式的JSON（只返回JSON，不要其他内容）：
{{
  "pattern_name": "证候名称",
  "stage": "卫气营血或三焦阶段",
  "syndrome": "证候表现",
  "treatment": "治法",
  "formula": "方药",
  "differentiation": "鉴别要点(如果没有则null)"
}}"""

        if self.anthropic_api_key:
            try:
                result = self._call_anthropic(system_prompt, user_prompt)
                json_match = re.search(r"\{.*\}", result, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                print(f"Anthropic API error: {e}")

        return self._mock_extract_warm_disease(text)

    def generate_comparison(
        self,
        left_entity: str,
        right_entity: str,
        context: str | None = None,
        subject_name: str = "方剂学",
        entity_label: str = "方剂",
    ) -> dict[str, Any]:
        """Generate comparison between two entities."""
        system_prompt = (
            "你是一个中医助手。请比较两个同学科知识点的异同，返回纯JSON格式。"
        )

        user_prompt = f"""请比较以下两个{subject_name}{entity_label}的异同：

左{entity_label}：{left_entity}
右{entity_label}：{right_entity}
{f"上下文：{context}" if context else ""}

请返回以下格式的JSON：
{{
  "left_entity": "左侧{entity_label}名称",
  "right_entity": "右侧{entity_label}名称",
  "comparison_points": [
    {{"dimension": "比较维度", "left": "左侧特点", "right": "右侧特点"}}
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

        return self._mock_generate_comparison(left_entity, right_entity, entity_label)

    def generate_quiz(
        self,
        card_content: dict[str, Any],
        difficulty: str = "medium",
        subject_name: str = "方剂学",
        entity_label: str = "方剂",
    ) -> dict[str, Any]:
        """Generate quiz question from card content."""
        system_prompt = """你是一个中医助手。请根据知识卡片生成测试题，返回纯JSON格式。"""

        user_prompt = f"""根据以下{subject_name}{entity_label}知识卡片生成一道测试题：

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

        return self._mock_generate_quiz(card_content, difficulty, entity_label)

    def _mock_extract_formula(self, text: str) -> dict[str, Any]:
        """Mock extraction for MVP."""
        # Try to extract formula name from text
        name_match = re.search(r"([\u4e00-\u9fa5]{2,20}(?:汤|散|饮|丸|剂|方))", text)
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

    def _mock_extract_acupuncture(self, text: str) -> dict[str, Any]:
        """Mock acupuncture extraction for MVP."""
        compact_text = re.sub(r"\s+", " ", text)
        block_text = self._extract_first_acupoint_block(text)
        compact_block = re.sub(r"\s+", " ", block_text)

        labels = ("定位", "主治", "操作", "刺灸法", "注意", "禁忌", "解剖")
        name_match = re.search(r"(?:^|[。；;\s])\d+\.\s*([\u4e00-\u9fa5]{1,8})", compact_block)
        if not name_match:
            name_match = re.search(
                r"(?:^|[。；;\s])(?:\d+\.)?\s*([\u4e00-\u9fa5]{1,8})[^()\n]{0,12}\([^)]*[A-Za-z]{1,3}\s*\d+[^)]*\)",
                compact_block,
            )
        if not name_match:
            name_match = re.search(
                rf"^\s*(?!{'|'.join(labels)})([\u4e00-\u9fa5]{{1,8}}(?:穴|俞|募)?)",
                block_text,
            )

        meridian_match = re.search(r"(?:经络|归经|所属经脉)[：:]\s*([^\n。；;]+)", block_text)
        if not meridian_match:
            meridian_match = re.search(
                r"(手太阴肺经|手阳明大肠经|足阳明胃经|足太阴脾经|手少阴心经|手太阳小肠经|"
                r"足太阳膀胱经|足少阴肾经|手厥阴心包经|手少阳三焦经|足少阳胆经|足厥阴肝经|"
                r"督脉|任脉)",
                compact_block,
            )

        code_match = re.search(r"\((?:[^)]*,\s*)?([A-Za-z]{1,3})\s*\d+", compact_block)
        meridian = meridian_match.group(1) if meridian_match else None
        if not meridian and code_match:
            meridian = {
                "LU": "手太阴肺经",
                "LI": "手阳明大肠经",
                "ST": "足阳明胃经",
                "SP": "足太阴脾经",
                "HT": "手少阴心经",
                "SI": "手太阳小肠经",
                "BL": "足太阳膀胱经",
                "KI": "足少阴肾经",
                "PC": "手厥阴心包经",
                "SJ": "手少阳三焦经",
                "TE": "手少阳三焦经",
                "GB": "足少阳胆经",
                "LR": "足厥阴肝经",
                "GV": "督脉",
                "DU": "督脉",
                "CV": "任脉",
                "RN": "任脉",
            }.get(code_match.group(1).upper())

        location = self._extract_labeled_segment(block_text, ("定位",), field_key="location")
        indication = self._extract_labeled_segment(block_text, ("主治",), field_key="indication")
        technique = self._extract_labeled_segment(block_text, ("操作", "刺灸法"), field_key="technique")
        caution = self._extract_labeled_segment(block_text, ("注意", "禁忌"), field_key="caution")
        if not caution:
            fallback_caution_match = re.search(r"(孕妇[^。；;\n]{0,20}(?:不宜|慎用)[^。；;\n]*)", block_text)
            caution = fallback_caution_match.group(1) if fallback_caution_match else None

        return {
            "acupoint_name": name_match.group(1) if name_match else "未知穴位",
            "meridian": meridian,
            "location": location,
            "indication": indication,
            "technique": technique,
            "caution": caution,
        }

    def _extract_first_acupoint_block(self, text: str) -> str:
        """Trim OCR textbook text to the first acupoint block in the chunk."""
        compact_text = re.sub(r"\s+", " ", text).strip()
        starts = list(
            re.finditer(
                r"(?:^|[。；;\s])\d+\.\s*[\u4e00-\u9fa5]{1,8}(?:\*|\s)*\([^)]*[A-Za-z]{1,3}\s*\d+[^)]*\)",
                compact_text,
            )
        )
        if not starts:
            return compact_text

        start_index = starts[0].start()
        if compact_text[start_index].isspace():
            start_index += 1
        end_index = starts[1].start() if len(starts) > 1 else len(compact_text)
        return compact_text[start_index:end_index].strip()

    def _extract_labeled_segment(
        self,
        text: str,
        labels: tuple[str, ...],
        field_key: str | None = None,
    ) -> str | None:
        """Extract a field body and stop before the next section label or acupoint header."""
        escaped_labels = "|".join(re.escape(label) for label in labels)
        all_labels = "定位|主治|操作|刺灸法|注意|禁忌|解剖"
        pattern = re.compile(
            rf"(?:【(?:{escaped_labels})】|(?:{escaped_labels})[：:])\s*(.+?)(?=(?:【(?:{all_labels})】|(?:{all_labels})[：:]|\s+\d+\.\s*[\u4e00-\u9fa5]{{1,8}}(?:\*|\s)*\([^)]*[A-Za-z]{{1,3}}\s*\d+[^)]*\)|$))",
            re.DOTALL,
        )
        match = pattern.search(re.sub(r"\s+", " ", text))
        if not match:
            return None
        value = match.group(1).strip(" ；;。")
        value = self._clean_acupuncture_field(field_key, value)
        return value or None

    def _clean_acupuncture_field(self, field_key: str | None, value: str) -> str:
        """Drop OCR tail noise such as figure captions, songs, and chapter headings."""
        cleaned = re.sub(r"\s+", " ", value).strip()
        generic_stops = [
            r"。\s*第[一二三四五六七八九十]+节",
            r"。\s*[一二三四五六七八九十]+、",
            r"。\s*图\s*\d",
            r"。\s*[A-Z]{1,3}[一二三四五六七八九十0-9]+是",
        ]
        for stop in generic_stops:
            cleaned = re.split(stop, cleaned, maxsplit=1)[0]

        if field_key == "technique":
            cleaned = re.split(r"。", cleaned, maxsplit=1)[0]

        return cleaned.strip(" ；;。")

    def _mock_extract_warm_disease(self, text: str) -> dict[str, Any]:
        """Mock warm disease extraction for MVP."""
        name_match = re.search(r"([\u4e00-\u9fa5]{2,12}(?:证|证候|病))", text)
        stage_match = re.search(
            r"(卫分|气分|营分|血分|上焦|中焦|下焦)",
            text,
        )
        syndrome_match = re.search(r"(?:证候|表现)[：:]\s*([^\n]+)", text)
        treatment_match = re.search(r"(?:治法)[：:]\s*([^\n]+)", text)
        formula_match = re.search(r"(?:方药|代表方)[：:]\s*([^\n]+)", text)
        diff_match = re.search(r"(?:鉴别|辨证要点)[：:]\s*([^\n]+)", text)

        return {
            "pattern_name": name_match.group(1) if name_match else "未知证候",
            "stage": stage_match.group(1) if stage_match else None,
            "syndrome": syndrome_match.group(1) if syndrome_match else None,
            "treatment": treatment_match.group(1) if treatment_match else None,
            "formula": formula_match.group(1) if formula_match else None,
            "differentiation": diff_match.group(1) if diff_match else None,
        }

    def _mock_extract_acupuncture_clinical(self, text: str) -> dict[str, Any]:
        """Mock extraction for clinical acupuncture treatment cards."""
        compact_text = re.sub(r"\s+", " ", text).strip()
        first_line = text.splitlines()[0].strip() if text.splitlines() else compact_text[:24]
        numbered_heading_match = re.search(
            r"(?:^|[。；\s])(?:[一二三四五六七八九十百]+、)\s*([\u4e00-\u9fa5]{2,24}(?:病|证|症|综合征|痹|痛|瘫|聋|哮|痫|闭经|带下|遗尿|呕吐|泄泻))",
            compact_text,
        )
        focused_match = re.search(r"本节重点讨论([\u4e00-\u9fa5]{2,20}(?:病|证|症|综合征|痛|痹))", compact_text)
        disease_match = re.search(
            r"(?:^|[，。；\s])([\u4e00-\u9fa5]{2,20}(?:病|证|症|综合征|痹|痛|瘫|聋|哮|痫|闭经|带下|遗尿|呕吐|泄泻))",
            compact_text,
        )
        if numbered_heading_match:
            disease_match = numbered_heading_match
        if focused_match:
            disease_match = focused_match
        western_match = re.search(r"本病相当于西医学的([\u4e00-\u9fa5]{2,24}(?:病|证|症|综合征|痛|痹))", compact_text)
        if western_match:
            disease_match = western_match
        if not disease_match and first_line:
            disease_match = re.search(
                r"(第[一二三四五六七八九十百]+节\s*)?([\u4e00-\u9fa5]{2,20})",
                first_line,
            )

        treatment_principle = self._extract_generic_labeled_segment(
            text,
            ("治法", "治则", "治疗原则", "辨证论治"),
        )
        acupoint_prescription = self._extract_generic_labeled_segment(
            text,
            ("处方", "取穴", "主穴", "配穴", "选穴", "基本处方"),
        )
        notes = self._extract_generic_labeled_segment(
            text,
            ("操作", "方义", "加减", "按语", "经验"),
        )
        if not notes:
            notes = self._extract_first_sentence_after_label(
                compact_text,
                ("辨证", "加减"),
            )

        disease_name = None
        if disease_match:
            disease_name = disease_match.group(disease_match.lastindex or 1)
        return clean_clinical_card_payload(
            {
            "disease_name": disease_name or "未知病证",
            "treatment_principle": treatment_principle,
            "acupoint_prescription": acupoint_prescription,
            "notes": notes,
            },
            source_text=text,
        )

    def _mock_extract_acupuncture_theory(self, text: str) -> dict[str, Any]:
        """Mock extraction for acupuncture theory/general-review cards."""
        compact_text = re.sub(r"\s+", " ", text).strip()
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), compact_text[:24])

        concept_match = re.search(
            r"(?:^|[。；\s])((?:腧穴的)?定位法|骨度分寸定位法|手指同身寸定位法|自然标志定位法|"
            r"取穴原则|配穴原则|针灸治疗原则|针灸治疗作用|针灸处方|特定穴的临床应用|"
            r"五输穴|原穴|络穴|募穴|下合穴|八会穴|郄穴|八脉交会穴|交会穴|"
            r"毫针刺法|灸法|拔罐法|耳针法|头针法|电针法|针刺注意事项)",
            compact_text,
        )
        if not concept_match:
            concept_match = re.search(
                r"(第[一二三四五六七八九十]+章)?\s*([\u4e00-\u9fa5]{2,12}(?:定位法|原则|作用|特点|处方|应用|刺法|灸法|疗法|穴))",
                first_line,
            )

        category = None
        if any(token in compact_text for token in ("腧穴总论", "定位法", "取穴")):
            category = "腧穴总论"
        elif any(token in compact_text for token in ("刺灸法", "毫针", "灸法", "拔罐", "耳针", "头针", "电针")):
            category = "刺灸法总论"
        elif any(token in compact_text for token in ("治疗作用", "治疗原则", "针灸处方", "特定穴")):
            category = "治疗总论"

        core_points = self._extract_generic_labeled_segment(
            text,
            ("定义", "概念", "特点", "作用", "原则", "方法", "内容", "定位", "应用"),
        )
        if not core_points:
            core_points = self._extract_first_sentence_after_label(
                compact_text,
                ("定义", "概念", "特点", "作用", "原则", "方法", "内容", "定位", "应用"),
            )
        if not core_points:
            sentences = re.split(r"[。；;]", compact_text)
            informative = [sentence.strip() for sentence in sentences if len(sentence.strip()) >= 8]
            core_points = "；".join(informative[:2]) if informative else None

        exam_focus = self._extract_generic_labeled_segment(
            text,
            ("主治", "适应证", "临床应用", "注意事项", "记忆要点", "考试要点"),
        )
        if not exam_focus:
            exam_focus = self._extract_first_sentence_after_label(
                compact_text,
                ("适应证", "临床应用", "注意事项", "记忆要点", "考试要点"),
            )

        return {
            "concept_name": concept_match.group(concept_match.lastindex or 1) if concept_match else first_line[:12],
            "category": category,
            "core_points": core_points,
            "exam_focus": exam_focus,
        }

    def _mock_generate_comparison(
        self,
        left: str,
        right: str,
        entity_label: str,
    ) -> dict[str, Any]:
        """Mock comparison for MVP."""
        return {
            "left_entity": left,
            "right_entity": right,
            "comparison_points": [
                {"dimension": "共同点", "left": "同属解表剂", "right": "同属解表剂"},
                {"dimension": "表证类型", "left": "表虚证", "right": "表实证"},
            ],
            "question_text": f"请比较{left}与{right}两个{entity_label}的异同",
            "answer_text": f"{left}与{right}在适应场景、核心特点和辨析要点上各有差异。",
        }

    def _mock_generate_quiz(
        self,
        card: dict[str, Any],
        difficulty: str,
        entity_label: str,
    ) -> dict[str, Any]:
        """Mock quiz generation for MVP."""
        title = card.get("formula_name") or card.get("acupoint_name") or card.get("pattern_name") or "该知识点"
        return {
            "type": "choice",
            "question": f"以下哪项最符合{title}这个{entity_label}的核心信息？",
            "options": [
                {"key": "A", "value": "请结合原文继续补充结构化要点"},
                {"key": "B", "value": "只记标题，不看适应证"},
                {"key": "C", "value": "忽略主题差异，统一按方剂学处理"},
                {"key": "D", "value": "完全不需要复习"},
            ],
            "answer": "A",
            "explanation": f"{title}的测试题应围绕其结构化字段来复习。",
        }

    def _extract_generic_labeled_segment(
        self,
        text: str,
        labels: tuple[str, ...],
    ) -> str | None:
        """Extract text that follows one of the labels until the next label-like marker."""
        escaped_labels = "|".join(re.escape(label) for label in labels)
        next_markers = (
            "治法|治则|治疗原则|辨证论治|处方|取穴|主穴|配穴|选穴|基本处方|"
            "操作|方义|加减|按语|经验|治宜|病因病机"
        )
        pattern = re.compile(
            rf"(?:【(?:{escaped_labels})】|(?:{escaped_labels})(?:[：:]|\s{{0,2}}))\s*(.+?)(?=(?:【(?:{next_markers})】|(?:{next_markers})(?:[：:]|\s{{0,2}})|$))",
            re.DOTALL,
        )
        match = pattern.search(re.sub(r"\s+", " ", text))
        if not match:
            return None
        return match.group(1).strip(" ；;。") or None

    def _extract_first_sentence_after_label(
        self,
        text: str,
        labels: tuple[str, ...],
    ) -> str | None:
        """Fallback extractor for one short sentence after a fuzzy label."""
        escaped_labels = "|".join(re.escape(label) for label in labels)
        match = re.search(rf"(?:{escaped_labels})[：:]?\s*([^。；;\n]+)", text)
        if not match:
            return None
        return match.group(1).strip(" ；;。") or None


llm_service = LLMService()
