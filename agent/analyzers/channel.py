# -*- coding: utf-8 -*-
"""渠道 / 维度分析（数据源感知）。

- 合成数据（source=synthetic）：营销渠道（自然搜索/直播/私域等）的量价质分析。
- Olist（source=olist）：无营销渠道字段，退化为「支付方式」维度分析。
"""

import matplotlib.pyplot as plt

from agent import viz
from agent.data import effective_orders
from .base import Analyzer, AnalysisResult, Chart, CUR


class ChannelAnalyzer(Analyzer):
    name = "channel"
    keywords = ["渠道", "来源", "投放", "广告", "推广", "营销", "roi", "直播", "私域", "流量", "支付方式"]

    def run(self, data):
        orders = data["orders"]
        eff = effective_orders(orders)
        source = data.get("source", "synthetic")
        if source == "olist":
            return self._olist_payment(orders, eff)
        return self._synthetic_channel(orders, eff)

    # ------------------------------------------------------------------
    def _synthetic_channel(self, orders, eff):
        g = eff.groupby("channel").agg(
            订单量=("order_id", "count"),
            GMV=("amount", "sum"),
        )
        g["客单价"] = g["GMV"] / g["订单量"]
        g["复购率"] = eff.groupby("channel").apply(
            lambda x: (x.groupby("user_id")["order_id"].count() >= 2).mean()
        )
        g["退货率"] = orders.groupby("channel").apply(
            lambda x: (x["status"] == "退货").mean()
        )
        g = g.sort_values("GMV", ascending=False)

        top_ch = g.index[0]
        live_return = g.loc["直播带货", "退货率"] if "直播带货" in g.index else 0

        kpis = [
            {"label": "GMV 第一渠道", "value": top_ch, "hint": self.fmt_money(g["GMV"].iloc[0])},
            {"label": "客单最高渠道", "value": g["客单价"].idxmax(), "hint": f"{CUR}{g['客单价'].max():.0f}"},
            {"label": "复购率最高渠道", "value": g["复购率"].idxmax(), "hint": self.fmt_pct(g["复购率"].max())},
            {"label": "退货率最高渠道", "value": g["退货率"].idxmax(), "hint": self.fmt_pct(g["退货率"].max())},
        ]

        fig1, ax1 = plt.subplots(figsize=(9, 3.4))
        x = range(len(g))
        ax1.bar(x, g["GMV"].values / 1e4, color=viz.PALETTE[0], label="GMV（万元）")
        ax2 = ax1.twinx()
        ax2.plot(x, g["客单价"].values, color=viz.PALETTE[3], marker="o", linewidth=2, label="客单价（元）")
        ax1.set_xticks(list(x))
        ax1.set_xticklabels([viz.pretty_label(x) for x in g.index], rotation=20)
        ax1.set_ylabel("GMV（万元）")
        ax2.set_ylabel("客单价（元）")
        ax1.set_title("各渠道 GMV 与客单价")
        ax1.legend(loc="upper left")
        ax2.legend(loc="upper right")
        viz.apply_style(ax1)
        c1 = Chart("渠道 GMV 与客单价", viz.save_fig(fig1, "channel_gmv_aov.png"), "量价组合看渠道定位。")

        fig2, ax3 = plt.subplots(figsize=(9, 3.2))
        x = list(range(len(g)))
        ax3.bar([i - 0.2 for i in x], g["退货率"].values * 100, width=0.4, color=viz.PALETTE[3], label="退货率%")
        ax3.bar([i + 0.2 for i in x], g["复购率"].values * 100, width=0.4, color=viz.PALETTE[2], label="复购率%")
        ax3.set_xticks(x)
        ax3.set_xticklabels([viz.pretty_label(x) for x in g.index], rotation=20)
        ax3.set_ylabel("百分比（%）")
        ax3.set_title("各渠道退货率与复购率")
        ax3.legend()
        viz.apply_style(ax3)
        c2 = Chart("渠道退货率与复购率", viz.save_fig(fig2, "channel_quality.png"), "质量指标对比。")

        insights = [
            f"「{top_ch}」是 GMV 第一渠道（{self.fmt_money(g['GMV'].iloc[0])}），占比 {g['GMV'].iloc[0]/g['GMV'].sum():.1%}。",
            f"「{g['客单价'].idxmax()}」客单价最高（{CUR}{g['客单价'].max():.0f}），但若叠加高退货率，实际净贡献需打折——直播渠道退货率高达 {live_return:.1%}。",
            f"「{g['复购率'].idxmax()}」复购率最高（{g['复购率'].max():.1%}），是忠诚用户的主要沉淀池。",
            "渠道呈现「规模渠道」与「价值渠道」分化：规模看 GMV，价值看复购与退货。",
        ]
        recommendations = [
            "对高客单、高退货的直播渠道，用「提前预售 + 真实测评 + 完善退换货说明」降低冲动退货。",
            "对高复购渠道加大精细化运营，沉淀会员资产。",
            "建立「渠道 ROI 看板」，把退货与履约成本计入，用净 GMV 评估渠道质量。",
        ]
        return AnalysisResult("渠道效率与质量分析", kpis, [c1, c2], insights, recommendations)

    # ------------------------------------------------------------------
    def _olist_payment(self, orders, eff):
        g = eff.groupby("pay_method").agg(
            订单量=("order_id", "count"),
            GMV=("amount", "sum"),
        )
        g["客单价"] = g["GMV"] / g["订单量"]
        g["复购率"] = eff.groupby("pay_method").apply(
            lambda x: (x.groupby("user_id")["order_id"].count() >= 2).mean()
        )
        g["取消率"] = orders.groupby("pay_method").apply(
            lambda x: (x["status"] == "取消").mean()
        )
        g = g.sort_values("GMV", ascending=False)

        top_p = g.index[0]
        kpis = [
            {"label": "GMV 第一支付方式", "value": viz.pretty_label(top_p), "hint": self.fmt_money(g["GMV"].iloc[0])},
            {"label": "客单最高", "value": viz.pretty_label(g["客单价"].idxmax()), "hint": f"{CUR}{g['客单价'].max():.0f}"},
            {"label": "复购率最高", "value": viz.pretty_label(g["复购率"].idxmax()), "hint": self.fmt_pct(g["复购率"].max())},
            {"label": "取消率最高", "value": viz.pretty_label(g["取消率"].idxmax()), "hint": self.fmt_pct(g["取消率"].max())},
        ]

        fig1, ax1 = plt.subplots(figsize=(9, 3.4))
        x = range(len(g))
        ax1.bar(x, g["GMV"].values / 1e6, color=viz.PALETTE[0], label="GMV（百万）")
        ax2 = ax1.twinx()
        ax2.plot(x, g["客单价"].values, color=viz.PALETTE[3], marker="o", linewidth=2, label="客单价（元）")
        ax1.set_xticks(list(x))
        ax1.set_xticklabels([viz.pretty_label(x) for x in g.index], rotation=20)
        ax1.set_ylabel("GMV（百万）")
        ax2.set_ylabel("客单价（元）")
        ax1.set_title("各支付方式 GMV 与客单价")
        ax1.legend(loc="upper left")
        ax2.legend(loc="upper right")
        viz.apply_style(ax1)
        c1 = Chart("支付方式 GMV 与客单价", viz.save_fig(fig1, "channel_gmv_aov.png"), "Olist 无营销渠道，以支付方式呈现。")

        fig2, ax3 = plt.subplots(figsize=(9, 3.2))
        x = list(range(len(g)))
        ax3.bar([i - 0.2 for i in x], g["取消率"].values * 100, width=0.4, color=viz.PALETTE[3], label="取消率%")
        ax3.bar([i + 0.2 for i in x], g["复购率"].values * 100, width=0.4, color=viz.PALETTE[2], label="复购率%")
        ax3.set_xticks(x)
        ax3.set_xticklabels([viz.pretty_label(x) for x in g.index], rotation=20)
        ax3.set_ylabel("百分比（%）")
        ax3.set_title("各支付方式取消率与复购率")
        ax3.legend()
        viz.apply_style(ax3)
        c2 = Chart("支付方式取消率与复购率", viz.save_fig(fig2, "channel_quality.png"), "质量指标对比。")

        insights = [
            f"Olist 无营销渠道字段，本模块退化为「支付方式」维度：GMV 第一支付方式为「{viz.pretty_label(top_p)}」（{self.fmt_money(g['GMV'].iloc[0])}）。",
            f"「{viz.pretty_label(g['客单价'].idxmax())}」客单价最高（{CUR}{g['客单价'].max():.0f}），「{viz.pretty_label(g['复购率'].idxmax())}」复购率最高（{g['复购率'].max():.1%}）。",
            f"取消率层面「{viz.pretty_label(g['取消率'].idxmax())}」最高（{g['取消率'].max():.1%}），可结合支付体验优化。",
        ]
        recommendations = [
            "如需营销渠道分析，请切换到合成数据（云启严选）演示。",
            "关注高取消率支付方式，排查支付成功率与风控拦截对转化的影响。",
        ]
        return AnalysisResult("支付方式维度分析", kpis, [c1, c2], insights, recommendations)
