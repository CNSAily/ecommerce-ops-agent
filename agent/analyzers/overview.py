# -*- coding: utf-8 -*-
"""综合概览分析：一页看清公司整体经营盘面。"""

import matplotlib.pyplot as plt

from agent import viz
from agent.data import effective_orders
from .base import Analyzer, AnalysisResult, Chart, CUR


class OverviewAnalyzer(Analyzer):
    name = "overview"
    keywords = ["概览", "整体", "分析一下", "帮我分析", "全局", "总结", "情况", "综合", "经营"]

    def run(self, data):
        users, orders, _ = data["users"], data["orders"], data["events"]
        eff = effective_orders(orders)

        gmv = eff["amount"].sum()
        n_orders = len(eff)
        aov = gmv / n_orders
        n_buyers = eff["user_id"].nunique()
        repeat = (eff.groupby("user_id")["order_id"].count() >= 2).mean()
        if data.get("source") == "olist":
            return_rate = (orders["status"] == "取消").mean()
            rate_label = "取消率"
        else:
            return_rate = (orders["status"] == "退货").mean()
            rate_label = "退货率"
        top_cat = eff.groupby("category")["amount"].sum().idxmax()

        kpis = [
            {"label": "总 GMV（成功订单）", "value": self.fmt_money(gmv)},
            {"label": "订单量", "value": f"{n_orders:,}"},
            {"label": "客单价 AOV", "value": f"{CUR}{aov:.0f}"},
            {"label": "下单用户数", "value": f"{n_buyers:,}"},
            {"label": "复购用户占比", "value": self.fmt_pct(repeat)},
            {"label": rate_label, "value": self.fmt_pct(return_rate)},
        ]

        # 图1：月度 GMV 趋势
        eff["month"] = eff["order_time"].dt.to_period("M").astype(str)
        monthly = eff.groupby("month")["amount"].sum() / 1e4
        fig1, ax = plt.subplots(figsize=(9, 3.6))
        ax.plot(monthly.index, monthly.values, marker="o", color=viz.PALETTE[0], linewidth=2, markersize=4)
        ax.fill_between(monthly.index, monthly.values, alpha=0.12, color=viz.PALETTE[0])
        peak = monthly.idxmax()
        ax.axvline(peak, color=viz.PALETTE[3], linestyle="--", alpha=0.7)
        ax.annotate(f"峰值 {peak}\n{monthly.max():.0f}万", xy=(peak, monthly.max()),
                    xytext=(peak, monthly.max() * 0.72), ha="center",
                    arrowprops=dict(arrowstyle="->", color=viz.PALETTE[3]))
        ax.set_title("月度 GMV 趋势（万元）")
        ax.tick_params(axis="x", rotation=45)
        viz.apply_style(ax)
        c1 = Chart("月度 GMV 趋势", viz.save_fig(fig1, "overview_monthly_gmv.png"), "全年呈现明显节假日脉冲。")

        # 图2：品类 GMV 占比（Top 6 + 其他，中文标签）
        cat_gmv = eff.groupby("category")["amount"].sum()
        pie_labels, pie_vals = viz.top_n(cat_gmv, 6)
        pie_labels_cn = [viz.pretty_label(x) for x in pie_labels]
        fig2, ax2 = plt.subplots(figsize=(6.4, 3.6))
        ax2.pie(pie_vals, labels=pie_labels_cn, autopct="%1.1f%%",
                colors=viz.PALETTE + ["#B7C4D2"], startangle=90,
                wedgeprops=dict(width=0.42, edgecolor="white"))
        ax2.set_title("品类 GMV 占比（Top 6）")
        c2 = Chart("品类 GMV 占比", viz.save_fig(fig2, "overview_category_share.png"), "各品类贡献结构。")

        # 图3：渠道 / 支付方式 GMV 对比（中文标签）
        dim_label = "支付方式" if data.get("source") == "olist" else "渠道"
        ch_gmv = eff.groupby("channel")["amount"].sum().sort_values() / 1e4
        ch_labels = [viz.pretty_label(x) for x in ch_gmv.index]
        fig3, ax3 = plt.subplots(figsize=(9, max(2.8, 0.5 * len(ch_labels) + 1.0)))
        ax3.barh(range(len(ch_labels)), ch_gmv.values, color=viz.PALETTE[0])
        ax3.set_yticks(range(len(ch_labels)))
        ax3.set_yticklabels(ch_labels, fontsize=10)
        for i, v in enumerate(ch_gmv.values):
            ax3.text(v, i, f" {v:.0f}万", va="center", fontsize=9)
        ax3.set_title(f"各{dim_label} GMV（万元）")
        viz.apply_style(ax3)
        c3 = Chart(f"各{dim_label} GMV", viz.save_fig(fig3, "overview_channel_gmv.png"), "渠道贡献一览。")

        insights = [
            f"全年有效 GMV 约 {self.fmt_money(gmv)}，共 {n_orders:,} 笔订单，客单价 {CUR}{aov:.0f}，经营基本盘稳定。",
            f"销售额集中在 {peak}（促销大促拉动），全年走势呈明显的「节假日脉冲 + 平销期回落」特征。",
            f"「{viz.pretty_label(top_cat)}」为第一大品类，贡献 GMV {self.fmt_money(cat_gmv.max())}（占比 {cat_gmv.max()/cat_gmv.sum():.1%}）。",
            f"复购用户占比 {repeat:.1%}，{rate_label} {return_rate:.1%}，用户粘性与履约质量仍有优化空间。",
        ]
        recommendations = [
            "在大促前 1 个月启动预热蓄水，把脉冲峰值转化为更高的季度盘子。",
            "对复购用户占比偏低的问题，落地会员体系 + 品类关联推荐，拉升 LTV。",
            f"针对{rate_label}，重点排查高退货/高取消的品类与渠道，优化商品描述与售前引导。",
        ]
        brand = "Olist 电商" if data.get("source") == "olist" else "云启严选"
        return AnalysisResult(f"{brand} · 经营全景概览", kpis, [c1, c2, c3], insights, recommendations)
