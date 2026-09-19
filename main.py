# -*- coding: utf-8 -*-
"""电商运营数据分析 Agent（CLI 入口）。

支持双数据源：
- Olist 真实数据（python scripts/download_olist.py 下载）
- 云启严选合成数据（python scripts/generate_data.py 生成）

用法：
    python main.py "帮我整体分析一下经营情况"   # 单次分析（auto 模式）
    python main.py "为什么直播退货率高" --agent   # 强制 ReAct 自主分析
    python main.py --tool "哪个品类卖得最好"      # 强制工具轨
    python main.py --demo                         # 生成全景演示报告
    python main.py --list                         # 列出支持主题
    python main.py                                # 交互式对话
"""

import sys

from agent.orchestrator import Agent
from agent import report
from agent.data import source_name

EXAMPLES = {
    "综合概览": "帮我整体分析一下公司的经营情况",
    "销售趋势": "近一年各月 GMV 和客单价趋势如何",
    "品类品牌": "哪个品类卖得最好",
    "用户分层": "帮我做一下用户 RFM 分层，找高价值用户",
    "客户价值": "帮我预测客户终身价值 CLV",
    "复购留存": "用户的复购率和留存情况怎么样",
    "转化漏斗": "从浏览到支付的转化漏斗如何",
    "渠道分析": "各渠道的 GMV、转化率和退货率怎么样",
    "销售预测": "预测未来三个月 GMV",
    "异常检测": "检测 GMV 的异常波动",
    "统计检验": "做一下统计检验，看哪些差异显著",
}

BANNER = """\033[36m
  ┌──────────────────────────────────────────────┐
  │   电商运营数据分析 Agent                      │
  │   自然语言提问 → 自动分析 → 图表 → 洞察报告    │
  │   工具轨（内置 11 大模块）+ ReAct 轨（写代码） │
  └──────────────────────────────────────────────┘\033[0m
  输入问题开始分析；输入「主题」查看支持主题；输入「退出」结束。
"""


def print_topics():
    print("\n支持的分析主题（可直接提问）：")
    for label, q in EXAMPLES.items():
        print(f"  · {label}：{q}")
    print()


def run_once(agent: Agent, question: str):
    intent, method, result = agent.ask(question)
    path = report.render_html(question, intent, method, result)
    label = report.INTENT_LABELS.get(intent, intent)
    print(f"\n已识别主题：{label}（{report.METHOD_LABELS.get(method, method)}）")
    if result.kpis:
        print("关键指标：")
        for k in result.kpis:
            hint = f"（{k['hint']}）" if k.get("hint") else ""
            print(f"  - {k['label']}: {k['value']} {hint}")
    if intent == "react" and result.insights:
        print(f"\nAgent 结论：\n{result.insights[0]}\n")
    print(f"\n报告已生成：{path}\n")
    return path


def run_repl(agent: Agent):
    print(BANNER)
    while True:
        try:
            q = input("你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q in ("退出", "exit", "quit", "q"):
            break
        if q in ("主题", "帮助", "help", "list"):
            print_topics()
            continue
        run_once(agent, q)


def main():
    args = sys.argv[1:]

    if "--list" in args:
        print_topics()
        return

    mode = "auto"
    if "--agent" in args:
        mode = "react"
        args = [a for a in args if a != "--agent"]
    elif "--tool" in args:
        mode = "tool"
        args = [a for a in args if a != "--tool"]

    agent = Agent(agent_mode=mode)

    if "--demo" in args:
        src = "Olist 真实电商数据" if source_name() == "olist" else "云启严选模拟数据"
        print(f"正在生成全景演示报告（数据源：{src}，覆盖 11 大分析模块）...")
        results = agent.analyze_all()
        path = report.render_demo(results)
        print(f"演示报告已生成：{path}")
        return

    if args:
        question = " ".join(args)
        run_once(agent, question)
    else:
        run_repl(agent)


if __name__ == "__main__":
    main()
