# -*- coding: utf-8 -*-
"""分析器注册表。"""

from .base import Analyzer, AnalysisResult, Chart
from .overview import OverviewAnalyzer
from .gmv import GmvAnalyzer
from .product import ProductAnalyzer
from .customer import CustomerAnalyzer
from .retention import RetentionAnalyzer
from .funnel import FunnelAnalyzer
from .channel import ChannelAnalyzer
from .clv import ClvAnalyzer
from .forecast import ForecastAnalyzer
from .anomaly import AnomalyAnalyzer
from .stats import StatsAnalyzer

ALL_ANALYZERS = [
    OverviewAnalyzer(),
    GmvAnalyzer(),
    ProductAnalyzer(),
    CustomerAnalyzer(),
    RetentionAnalyzer(),
    FunnelAnalyzer(),
    ChannelAnalyzer(),
    ClvAnalyzer(),
    ForecastAnalyzer(),
    AnomalyAnalyzer(),
    StatsAnalyzer(),
]

# 意图中文标签（用于报告展示；react 非 Analyzer，仅作展示标签）
INTENT_LABELS = {
    "overview": "综合概览",
    "gmv": "销售趋势",
    "product": "品类品牌",
    "customer": "用户分层",
    "retention": "复购留存",
    "funnel": "转化漏斗",
    "channel": "渠道分析",
    "clv": "客户价值",
    "forecast": "销售预测",
    "anomaly": "异常检测",
    "stats": "统计检验",
    "react": "Agent 自主分析",
}


def get_analyzer(name: str):
    for a in ALL_ANALYZERS:
        if a.name == name:
            return a
    return None
