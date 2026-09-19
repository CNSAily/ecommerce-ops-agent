# -*- coding: utf-8 -*-
"""工具注册：把内置分析模块包装为 Agent 可调用的工具。

双轨架构：
- 工具轨：意图识别命中标准问题 → 直接调用对应 Analyzer（快 / 稳 / 可离线）。
- ReAct 轨：开放式问题 → LLM 生成代码 + 沙箱执行（真 Agent，见 react.py）。

本模块提供工具轨执行入口，以及供 LLM 参考的工具能力清单。
"""

from .analyzers import ALL_ANALYZERS, get_analyzer, INTENT_LABELS


def tool_catalog() -> str:
    """生成工具能力清单（供 ReAct 的 LLM 或未来 function calling 参考）。"""
    lines = []
    for a in ALL_ANALYZERS:
        label = INTENT_LABELS.get(a.name, a.name)
        lines.append(f"- {a.name} / {label}：{'、'.join(a.keywords[:8])}")
    return "\n".join(lines)


def run_tool(name: str, data: dict):
    """执行指定工具，返回 AnalysisResult；未知工具返回 None。"""
    analyzer = get_analyzer(name)
    if analyzer is None:
        return None
    return analyzer.run(data)
