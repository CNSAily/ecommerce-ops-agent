# -*- coding: utf-8 -*-
"""异常检测：识别 GMV/订单量的异常波动点（突增 / 骤降）。"""

import matplotlib.pyplot as plt
import numpy as np

from agent import viz
from agent.data import effective_orders
from .base import Analyzer, AnalysisResult, Chart


class AnomalyAnalyzer(Analyzer):
    name = "anomaly"
    keywords = ["异常", "检测", "突变", "波动", "异动", "离群", "anomaly", "突增", "骤降", "异常值"]

    def run(self, data):
        eff = effective_orders(data["orders"])
        daily = eff.set_index("order_time")["amount"].resample("D").sum().fillna(0.0)

        if len(daily) < 30:
            return AnalysisResult("异常检测", [], [], ["数据天数过少（<30 天），无法可靠检测异常。"], [])

        mean, std = daily.mean(), daily.std()
        if std == 0:
            return AnalysisResult("异常检测", [], [], ["GMV 无波动，未检测到异常。"], [])

        z = (daily - mean) / std
        spike = daily[z > 3]   # 突增
        drop = daily[z < -3]   # 骤降

        kpis = [
            {"label": "异常日总数", "value": f"{len(spike) + len(drop):,}"},
            {"label": "突增日", "value": f"{len(spike):,}", "hint": "z-score > 3"},
            {"label": "骤降日", "value": f"{len(drop):,}", "hint": "z-score < -3"},
            {"label": "日均 GMV", "value": self.fmt_money(mean), "hint": f"波动系数 {std / mean:.1%}"},
        ]

        fig, ax = plt.subplots(figsize=(10, 3.8))
        ax.plot(daily.index, daily.values / 1e4, color=viz.PALETTE[0], linewidth=1, alpha=0.7, label="日 GMV（万元）")
        if len(spike):
            ax.scatter(spike.index, spike.values / 1e4, color=viz.PALETTE[2], s=45, zorder=5, label="突增")
        if len(drop):
            ax.scatter(drop.index, drop.values / 1e4, color=viz.PALETTE[3], s=45, zorder=5, label="骤降")
        ax.set_title("日 GMV 走势与异常点（|z|>3）")
        ax.legend(loc="upper left")
        ax.tick_params(axis="x", rotation=45)
        viz.apply_style(ax)
        c1 = Chart("GMV 异常检测", viz.save_fig(fig, "anomaly_gmv.png"), "红点=突增，绿点=骤降。")

        insights = []
        if len(spike):
            top_spike = spike.idxmax()
            insights.append(
                f"检测到 {len(spike)} 个突增日，最大单日 GMV {self.fmt_money(spike.max())}（{top_spike.date()}），"
                "可能对应大促或营销活动，需确认是否为可复制的增长动作。"
            )
        if len(drop):
            bottom = drop.idxmin()
            insights.append(
                f"检测到 {len(drop)} 个骤降日，最低 {self.fmt_money(drop.min())}（{bottom.date()}），"
                "需排查支付故障、库存断货或流量入口异常。"
            )
        if not spike.empty or not drop.empty:
            pass
        insights.append(
            f"整体日均 GMV {self.fmt_money(mean)}，波动系数 {std / mean:.1%}，"
            + ("波动较大，建议关注库存与履约弹性。" if std / mean > 0.5 else "波动处于正常区间。")
        )

        recommendations = [
            "对突增日复盘触发因素（大促/活动/爆品），沉淀可复用的爆发式增长打法。",
            "对骤降日建立自动告警：当日 GMV 偏离 7 日均值超 40% 即触发排查。",
        ]
        return AnalysisResult("GMV 异常检测", kpis, [c1], insights, recommendations)
