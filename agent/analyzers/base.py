# -*- coding: utf-8 -*-
"""分析器基类与结果结构。"""

from dataclasses import dataclass, field

from agent.data import source_name as _source_name

_RMB = "\u00a5"  # ¥


def currency() -> str:
    """当前数据源的货币符号（Olist 用雷亚尔 R$，合成数据用人民币 ¥）。"""
    return "R$" if _source_name() == "olist" else _RMB


CUR = currency()


@dataclass
class Chart:
    title: str
    path: str
    caption: str = ""


@dataclass
class AnalysisResult:
    title: str
    kpis: list = field(default_factory=list)       # [{"label","value","hint"}]
    charts: list = field(default_factory=list)      # [Chart]
    insights: list = field(default_factory=list)    # [str]
    recommendations: list = field(default_factory=list)  # [str]


class Analyzer:
    """分析器基类。子类需提供 name、keywords 并实现 run()。"""

    name = "base"
    keywords: list = []

    def run(self, data: dict) -> AnalysisResult:
        raise NotImplementedError

    @staticmethod
    def fmt_money(x: float) -> str:
        if x >= 1e8:
            return f"{CUR}{x / 1e8:.2f} 亿"
        if x >= 1e4:
            return f"{CUR}{x / 1e4:.1f} 万"
        return f"{CUR}{x:,.0f}"

    @staticmethod
    def fmt_pct(x: float) -> str:
        return f"{x * 100:.1f}%"
