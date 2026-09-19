# -*- coding: utf-8 -*-
"""Agent 编排器：意图识别 → 双轨执行（工具轨 / ReAct 轨）→ 结果组装。

双轨架构：
- 工具轨：标准问题命中内置 Analyzer，直接调用（快 / 稳 / 可离线）。
- ReAct 轨：开放式问题由 LLM 生成 pandas 代码 + 沙箱执行 + 多轮迭代（真 Agent）。

agent_mode ∈ {"auto", "tool", "react"}：
- tool  ：始终走工具轨；
- react ：始终走 ReAct 轨（需 LLM key）；
- auto  ：有 LLM key 且问题偏开放式 → ReAct，否则工具轨。
"""

import os

from config import REPORT_DIR

from .analyzers import ALL_ANALYZERS, get_analyzer
from .analyzers.base import AnalysisResult, Chart
from .data import export_for_sandbox, load_all
from .intent import IntentRouter
from .llm import LLMClient
from .react import ReactLoop

ASSET_DIR = REPORT_DIR / "assets"

# 触发 ReAct 的开放式问题信号词
OPEN_SIGNALS = ["为什么", "原因", "对比", "怎么样", "如何", "哪些", "关系", "深入", "探索", "有什么", "帮我看看", "分析一下"]


class Agent:
    def __init__(self, agent_mode: str = "auto"):
        self.agent_mode = agent_mode
        self.router = IntentRouter()
        self.data = load_all()
        self.llm = LLMClient()
        self.react = ReactLoop(self.llm)

    @property
    def source(self) -> str:
        return self.data.get("source", "synthetic")

    @property
    def llm_available(self) -> bool:
        return self.llm.enabled

    def ask(self, question: str):
        """单次分析，返回 (intent, method, AnalysisResult) 三元组。"""
        if self._should_use_react(question):
            return self._react_ask(question)
        intent, method = self.router.resolve(question)
        analyzer = get_analyzer(intent)
        result = analyzer.run(self.data)
        return intent, method, result

    def analyze_all(self):
        """全量分析（用于演示报告），返回 [(name, AnalysisResult)]。"""
        out = []
        for a in ALL_ANALYZERS:
            try:
                out.append((a.name, a.run(self.data)))
            except Exception as e:  # noqa: BLE001
                out.append(
                    (a.name, AnalysisResult(a.name, [], [], [f"分析失败：{e}"], []))
                )
        return out

    # ------------------------------------------------------------------
    def _should_use_react(self, question: str) -> bool:
        if self.agent_mode == "tool":
            return False
        if self.agent_mode == "react":
            return self.llm.enabled
        if not self.llm.enabled:
            return False
        return any(k in question for k in OPEN_SIGNALS)

    def _react_ask(self, question: str):
        os.makedirs(ASSET_DIR, exist_ok=True)
        sandbox_data = export_for_sandbox()
        out = self.react.run(question, sandbox_data, str(ASSET_DIR))
        return "react", "react", self._react_to_result(out)

    @staticmethod
    def _react_to_result(out: dict) -> AnalysisResult:
        charts = []
        for f in out.get("figures", []):
            path = os.path.join(str(ASSET_DIR), f)
            if os.path.exists(path):
                charts.append(Chart(f, path, "Agent 自主生成"))
        final = out.get("final") or "（分析完成，详见执行过程。）"
        return AnalysisResult(
            title="Agent 自主分析（ReAct 代码生成）",
            kpis=[],
            charts=charts,
            insights=[final],
            recommendations=[],
        )
