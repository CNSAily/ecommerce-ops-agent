# -*- coding: utf-8 -*-
"""HTML 报告生成：自包含单文件（图表 base64 内嵌），可直接分享/预览。"""

import base64
import html
import os
from datetime import datetime

from config import REPORT_DIR
from .analyzers import INTENT_LABELS
from .data import source_name


def _data_desc() -> str:
    return (
        "巴西 Olist 真实电商数据（约 10 万订单）"
        if source_name() == "olist"
        else "模拟电商运营数据（用户 2 万 / 订单 10 万 / 事件 30 万）"
    )

METHOD_LABELS = {"llm": "LLM 意图识别", "rule": "规则引擎", "default": "默认路由", "react": "ReAct 自主分析"}

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
       background: #f5f7fb; color: #1f2937; padding: 32px 16px; line-height: 1.6; }
.wrap { max-width: 980px; margin: 0 auto; }
header.hero { background: linear-gradient(135deg, #1e3a8a, #2563eb); color: #fff;
       border-radius: 14px; padding: 28px 32px; margin-bottom: 20px; }
header.hero h1 { font-size: 22px; margin-bottom: 6px; }
header.hero .q { font-size: 14px; opacity: .92; margin-top: 8px; }
header.hero .meta { margin-top: 12px; font-size: 12px; opacity: .85; }
.badge { display: inline-block; background: rgba(255,255,255,.2); padding: 2px 10px;
       border-radius: 999px; margin-right: 6px; }
section.block { background: #fff; border-radius: 12px; padding: 24px 28px; margin-bottom: 20px;
       box-shadow: 0 1px 3px rgba(16,24,40,.06); }
section.block h2 { font-size: 16px; color: #111827; margin-bottom: 16px;
       border-left: 4px solid #2563eb; padding-left: 10px; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
.kpi { background: #f8fafc; border: 1px solid #eef2f7; border-radius: 10px; padding: 14px 16px; }
.kpi .label { font-size: 12px; color: #6b7280; margin-bottom: 6px; }
.kpi .value { font-size: 20px; font-weight: 700; color: #1e3a8a; }
.kpi .hint { font-size: 11px; color: #9ca3af; margin-top: 4px; }
.chart { text-align: center; margin-bottom: 8px; }
.chart img { max-width: 100%; border-radius: 8px; border: 1px solid #eef2f7; }
.chart .cap { font-size: 12px; color: #6b7280; margin-top: 6px; text-align: left; }
ul.items { padding-left: 20px; }
ul.items li { margin-bottom: 8px; font-size: 14px; }
.insights li::marker { color: #2563eb; }
.recs li::marker { color: #16a34a; }
.rec { background: #f0fdf4; border: 1px solid #dcfce7; border-radius: 10px; padding: 4px 12px; margin-bottom: 8px; }
footer { text-align: center; font-size: 12px; color: #9ca3af; margin-top: 24px; }
"""


def _img_base64(path: str) -> str:
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{b64}"


def _kpi_cards(kpis) -> str:
    cards = []
    for k in kpis:
        hint = f'<div class="hint">{html.escape(k.get("hint", ""))}</div>' if k.get("hint") else ""
        cards.append(
            f'<div class="kpi"><div class="label">{html.escape(k["label"])}</div>'
            f'<div class="value">{html.escape(str(k["value"]))}</div>{hint}</div>'
        )
    return f'<div class="kpis">{"".join(cards)}</div>'


def _charts_html(charts) -> str:
    out = []
    for c in charts:
        if not c.path or not os.path.exists(c.path):
            continue
        cap = f'<div class="cap">{html.escape(c.caption)}</div>' if c.caption else ""
        out.append(
            f'<div class="chart"><div style="font-weight:600;margin-bottom:8px;text-align:left;">'
            f'{html.escape(c.title)}</div><img src="{_img_base64(c.path)}" />{cap}</div>'
        )
    return "".join(out)


def _block(title: str, result) -> str:
    parts = [f'<section class="block"><h2>{html.escape(title)}</h2>']
    if result.kpis:
        parts.append(_kpi_cards(result.kpis))
    if result.charts:
        parts.append(f'<div style="margin-top:16px;">{_charts_html(result.charts)}</div>')
    if result.insights:
        items = "".join(f"<li>{html.escape(x)}</li>" for x in result.insights)
        parts.append(f'<div style="margin-top:16px;"><b>核心发现</b><ul class="items insights">{items}</ul></div>')
    if result.recommendations:
        items = "".join(f'<li>{html.escape(x)}</li>' for x in result.recommendations)
        parts.append(f'<div style="margin-top:8px;"><b>运营建议</b><ul class="items recs">{items}</ul></div>')
    parts.append("</section>")
    return "".join(parts)


def _page(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"UTF-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
        f"<title>{html.escape(title)}</title><style>{_CSS}</style></head><body>"
        f'<div class="wrap">{body}'
        f'<footer>由 ecommerce-ops-agent 自动生成 · 数据：{_data_desc()}</footer></div></body></html>'
    )


def _out_path(prefix: str) -> str:
    os.makedirs(REPORT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return str(REPORT_DIR / f"{prefix}_{ts}.html")


def render_html(question: str, intent: str, method: str, result, out_path: str = None) -> str:
    """单主题分析报告。"""
    out_path = out_path or _out_path("report")
    label = INTENT_LABELS.get(intent, intent)
    meta = (
        f'<span class="badge">主题：{label}</span>'
        f'<span class="badge">路由：{METHOD_LABELS.get(method, method)}</span>'
    )
    brand = "Olist 电商" if source_name() == "olist" else "云启严选 · 电商运营"
    hero = (
        f'<header class="hero"><h1>{brand}数据分析</h1>'
        f'<div class="q">问题：{html.escape(question)}</div>'
        f'<div class="meta">{meta}</div></header>'
    )
    body = hero + _block(result.title, result)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(_page(result.title, body))
    return out_path


def render_demo(results: list, out_path: str = None) -> str:
    """全量演示报告（多个分析模块合并）。"""
    out_path = out_path or _out_path("demo_report")
    brand = "Olist 电商" if source_name() == "olist" else "云启严选 · 电商运营"
    hero = (
        f'<header class="hero"><h1>{brand}数据全景分析报告</h1>'
        '<div class="q">由 AI Agent 自动生成，覆盖 11 大分析模块</div>'
        f'<div class="meta"><span class="badge">数据：{_data_desc()}</span></div></header>'
    )
    body = hero + "".join(_block(INTENT_LABELS.get(n, n) + " · " + r.title, r) for n, r in results)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(_page("云启严选 · 电商运营数据全景分析报告", body))
    return out_path
