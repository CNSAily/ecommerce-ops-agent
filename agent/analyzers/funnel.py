# -*- coding: utf-8 -*-
"""转化漏斗分析（数据源感知）。

- 合成数据（source=synthetic）：浏览 → 加购 → 下单 → 支付 行为漏斗。
- Olist（source=olist）：订单履约漏斗（下单 → 成功送达，含取消率）。
"""

import matplotlib.pyplot as plt

from agent import viz
from .base import Analyzer, AnalysisResult, Chart

STAGES = ["浏览", "加购", "下单", "支付"]
STAGE_COLORS = ["#4C78A8", "#72B7B2", "#F58518", "#54A24B"]


class FunnelAnalyzer(Analyzer):
    name = "funnel"
    keywords = ["漏斗", "转化", "转化率", "流失", "加购", "支付", "成交", "浏览", "送达", "履约"]

    def run(self, data):
        source = data.get("source", "synthetic")
        if source == "olist":
            return self._olist_fulfillment(data)
        return self._synthetic_funnel(data)

    # ------------------------------------------------------------------
    def _synthetic_funnel(self, data):
        events = data["events"]
        counts = events.groupby("event_type")["user_id"].nunique().reindex(STAGES)
        conv = {}
        for i, s in enumerate(STAGES):
            conv[s] = counts[s] / counts[STAGES[0]] if i == 0 else counts[s] / counts[STAGES[i - 1]]

        overall = counts[STAGES[-1]] / counts[STAGES[0]]
        view_to_cart = counts["加购"] / counts["浏览"]
        cart_to_pay = counts["支付"] / counts["加购"]

        kpis = [
            {"label": "整体转化率（浏览→支付）", "value": self.fmt_pct(overall)},
            {"label": "浏览→加购", "value": self.fmt_pct(view_to_cart)},
            {"label": "加购→支付", "value": self.fmt_pct(cart_to_pay)},
            {"label": "UV（浏览）", "value": f"{int(counts['浏览']):,}"},
        ]

        fig1, ax = plt.subplots(figsize=(8, 3.8))
        for i, s in enumerate(STAGES):
            width = counts[s] / counts[STAGES[0]]
            ax.barh(i, width, color=STAGE_COLORS[i], height=0.55, left=(1 - width) / 2)
            ax.text(width / 2 + (1 - width) / 2, i, f"{s}\n{int(counts[s]):,} ({conv[s]:.1%})",
                    ha="center", va="center", fontsize=9, color="white" if width > 0.5 else "#333")
        ax.set_yticks(range(len(STAGES)))
        ax.set_yticklabels([""] * len(STAGES))
        ax.set_xlim(0, 1)
        ax.set_xticks([])
        ax.set_title("转化漏斗（去重用户数）")
        for spine in ax.spines.values():
            spine.set_visible(False)
        c1 = Chart("整体转化漏斗", viz.save_fig(fig1, "funnel_overall.png"), "各环节去重用户数与环节转化率。")

        ch = events.groupby("channel").apply(
            lambda g: g[g["event_type"] == "支付"]["user_id"].nunique()
            / g[g["event_type"] == "浏览"]["user_id"].nunique()
        ).sort_values()
        fig2, ax2 = plt.subplots(figsize=(9, 3.0))
        ax2.barh(ch.index, ch.values * 100, color=viz.PALETTE[0])
        for i, v in enumerate(ch.values):
            ax2.text(v * 100, i, f" {v:.1%}", va="center", fontsize=9)
        ax2.set_title("各渠道整体转化率（浏览→支付）")
        ax2.set_xlabel("转化率")
        viz.apply_style(ax2)
        c2 = Chart("分渠道转化率", viz.save_fig(fig2, "funnel_channel.png"), "不同渠道转化效率差异明显。")

        worst, best = ch.idxmin(), ch.idxmax()
        insights = [
            f"整体转化率 {overall:.1%}，其中「浏览→加购」环节流失最重（仅 {view_to_cart:.1%}），是最大漏斗瓶颈。",
            f"「加购→支付」转化率 {cart_to_pay:.1%}，加购后放弃支付仍有明显比例，存在催付空间。",
            f"渠道层面「{best}」转化率最高（{ch.max():.1%}），「{worst}」最低（{ch.min():.1%}），流量质量分化显著。",
        ]
        recommendations = [
            "优化商品详情页与搜索推荐，提升「浏览→加购」转化。",
            "对加购未支付用户做限时催付，减少弃单。",
            "对低转化渠道复盘投放素材与人群包，向高转化渠道倾斜。",
        ]
        return AnalysisResult("转化漏斗分析", kpis, [c1, c2], insights, recommendations)

    # ------------------------------------------------------------------
    def _olist_fulfillment(self, data):
        orders = data["orders"]
        total = len(orders)
        delivered = int((orders["status"] == "成功").sum())
        canceled = int((orders["status"] == "取消").sum())
        in_progress = total - delivered - canceled
        fulfillment_rate = delivered / total if total else 0
        cancel_rate = canceled / total if total else 0

        kpis = [
            {"label": "下单总数", "value": f"{total:,}"},
            {"label": "成功送达", "value": f"{delivered:,}", "hint": f"履约率 {self.fmt_pct(fulfillment_rate)}"},
            {"label": "取消订单", "value": f"{canceled:,}", "hint": f"取消率 {self.fmt_pct(cancel_rate)}"},
            {"label": "进行中", "value": f"{in_progress:,}", "hint": "发货/在途等中间状态"},
        ]

        fig1, ax = plt.subplots(figsize=(7, 3.4))
        labels = ["成功送达", "取消", "进行中"]
        values = [delivered, canceled, in_progress]
        colors = ["#54A24B", "#E45756", "#B4B2A9"]
        ax.bar(labels, values, color=colors)
        for i, v in enumerate(values):
            ax.text(i, v, f"{v:,}\n({v / total:.1%})", ha="center", va="bottom", fontsize=9)
        ax.set_ylabel("订单数")
        ax.set_title("订单履约状态分布（下单 → 送达）")
        viz.apply_style(ax)
        c1 = Chart("订单履约漏斗", viz.save_fig(fig1, "funnel_fulfillment.png"), "Olist 无浏览/加购行为数据，此处以履约状态呈现。")

        insights = [
            f"Olist 数据不含浏览/加购行为，此处呈现「下单 → 送达」履约漏斗：送达率 {fulfillment_rate:.1%}，取消率 {cancel_rate:.1%}。",
            f"{delivered:,} 笔订单成功送达，物流履约质量整体{'健康' if fulfillment_rate > 0.9 else '需关注'}。",
            f"取消订单 {canceled:,} 笔（{cancel_rate:.1%}），是供给侧或库存问题的信号，值得与评分交叉分析。",
        ]
        recommendations = [
            "如需完整的「浏览→加购→下单→支付」行为漏斗，请切换到合成数据（云启严选）演示。",
            "对取消订单做归因：库存不足 / 价格波动 / 用户反悔，针对性降低取消率。",
        ]
        return AnalysisResult("订单履约漏斗分析", kpis, [c1], insights, recommendations)
