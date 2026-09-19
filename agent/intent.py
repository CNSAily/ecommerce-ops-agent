# -*- coding: utf-8 -*-
"""意图识别：把自然语言问题路由到具体分析模块。

优先级：LLM（若配置）→ 规则关键词 → 默认综合概览。
"""

from .analyzers import ALL_ANALYZERS, get_analyzer, INTENT_LABELS
from .llm import LLMClient


class IntentRouter:
    def __init__(self, llm: LLMClient = None):
        self.llm = llm or LLMClient()

    def resolve(self, question: str):
        """返回 (intent_name, method)。method ∈ {llm, rule, default}"""
        q = question.lower()

        # 1. LLM 分类
        if self.llm.enabled:
            name = self._llm_classify(question)
            if name and get_analyzer(name):
                return name, "llm"

        # 2. 规则关键词（具体分析器优先，overview 作兜底）
        overview = get_analyzer("overview")
        for a in ALL_ANALYZERS:
            if a.name == "overview":
                continue
            for kw in a.keywords:
                if kw.lower() in q:
                    return a.name, "rule"

        for kw in overview.keywords:
            if kw.lower() in q:
                return "overview", "rule"

        # 3. 默认综合概览
        return "overview", "default"

    def _llm_classify(self, question: str):
        names = "、".join(INTENT_LABELS.values())
        system = (
            "你是电商数据分析助手「云启严选」的意图路由器。"
            f"请把用户问题分类到以下类别之一：{names}。"
            "只输出类别名，不要任何解释或标点。"
        )
        resp = self.llm.chat(system, question, max_tokens=20).strip()
        # 中文标签反查 name
        rev = {v: k for k, v in INTENT_LABELS.items()}
        return rev.get(resp, resp.lower())
