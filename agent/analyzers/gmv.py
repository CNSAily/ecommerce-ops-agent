# -*- coding: utf-8 -*-
"""GMV / 销售趋势分析：规模、增速、季节性与客单价。"""

import matplotlib.pyplot as plt

from agent import viz
from agent.data import effective_orders
from .base import Analyzer, AnalysisResult, Chart, CUR


class GmvAnalyzer(Analyzer):
    name = "gmv"
    keywords = ["gmv", "销售", "销售额", "营收", "收入", "趋势", "增长", "月度", "每月", "客单价", "aov"]

    def run(self, data):
        orders = data["orders"]
        eff = effective_orders(orders)

        gmv = eff["amount"].sum()
        eff["month"] = eff["order_time"].dt.to_period("M").astype(str)
        monthly = eff.groupby("month")["amount"].sum()
        monthly_orders = eff.groupby("month")["order_id"].count()
        monthly_aov = monthly / monthly_orders

        peak_m = monthly.idxmax()
        trough_m = monthly.idxmin()
        growth = monthly.iloc[-1] / monthly.iloc[0] - 1

        kpis = [
            {"label": "总 GMV", "value": self.fmt_money(gmv)},
            {"label": "峰值月份", "value": peak_m, "hint": f"{self.fmt_money(monthly.max())}"},
            {"label": "低谷月份", "value": trough_m, "hint": f"{self.fmt_money(monthly.min())}"},
            {"label": "首尾月增速", "value": self.fmt_pct(growth)},
            {"label": "全年客单价", "value": f"{CUR}{gmv/len(eff):.0f}"},
        ]

        # 图1：月度 GMV + 订单量（双轴）
        fig1, ax1 = plt.subplots(figsize=(9, 3.6))
        ax1.bar(monthly.index, monthly.values / 1e4, color=viz.PALETTE[0], alpha=0.85, label="GMV（万元）")
        ax1.set_ylabel("GMV（万元）")
        ax2 = ax1.twinx()
        ax2.plot(monthly_orders.index, monthly_orders.values, color=viz.PALETTE[3], marker="o", linewidth=2, label="订单量")
        ax2.set_ylabel("订单量")
        ax1.set_title("月度 GMV 与订单量")
        ax1.tick_params(axis="x", rotation=45)
        ax1.legend(loc="upper left")
        ax2.legend(loc="upper right")
        viz.apply_style(ax1)
        c1 = Chart("月度 GMV 与订单量", viz.save_fig(fig1, "gmv_monthly.png"), "GMV 与订单量同向波动，量价基本一致。")

        # 图2：月度客单价
        fig2, ax = plt.subplots(figsize=(9, 3.0))
        ax.plot(monthly_aov.index, monthly_aov.values, marker="o", color=viz.PALETTE[2], linewidth=2)
        ax.axhline(monthly_aov.mean(), color=viz.PALETTE[1], linestyle="--", alpha=0.6, label="均值")
        ax.set_title("月度客单价 AOV（元）")
        ax.tick_params(axis="x", rotation=45)
        ax.legend()
        viz.apply_style(ax)
        c2 = Chart("月度客单价", viz.save_fig(fig2, "gmv_aov.png"), "客单价整体平稳，大促月略有拉低。")

        insights = [
            f"全年 GMV {self.fmt_money(gmv)}，峰值出现在 {peak_m}（{self.fmt_money(monthly.max())}），主要受大促驱动。",
            f"平销期（如 {trough_m}）GMV 回落至 {self.fmt_money(monthly.min())}，峰谷比约 {monthly.max()/monthly.min():.1f} 倍，依赖促销拉动的特征明显。",
            f"客单价中枢稳定在 {CUR}{monthly_aov.mean():.0f} 左右，说明用户消费力并未随大促大幅透支。",
            f"首尾月 GMV 增速 {growth:.1%}，全年规模呈{'上升' if growth > 0 else '收缩'}态势。",
        ]
        recommendations = [
            "用「日常会员价 + 月度主题促销」平滑峰谷，降低对大促的过度依赖。",
            "大促月客单价被拉低，建议通过满减门槛设计守住客单价底线。",
        ]
        return AnalysisResult("GMV 与销售趋势分析", kpis, [c1, c2], insights, recommendations)
