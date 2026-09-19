# -*- coding: utf-8 -*-
"""销售预测：月度 GMV 时间序列的趋势 + 季节分解外推。

不依赖重库（prophet/statsmodels），用「线性趋势 + 季节因子」做可解释的
短期预测，输出未来 N 个月 GMV 预测区间，供经营计划参考。
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from agent import viz
from agent.data import effective_orders
from .base import Analyzer, AnalysisResult, Chart

FORECAST_MONTHS = 3


class ForecastAnalyzer(Analyzer):
    name = "forecast"
    keywords = ["预测", "forecast", "未来", "趋势预测", "销量预测", "gmv预测", "预估", "走势"]

    def run(self, data):
        eff = effective_orders(data["orders"])

        monthly = eff.set_index("order_time")["amount"].resample("ME").sum()
        # 剔除首尾不完整月份（首月可能无满月数据，末月为进行中）
        monthly = monthly[(monthly.index > monthly.index.min()) & (monthly.index < monthly.index.max())]
        if len(monthly) < 6:
            return self._too_short()

        y = monthly.values.astype(float)
        x = np.arange(len(y))
        t = monthly.index

        # 线性趋势
        slope, intercept = np.polyfit(x, y, 1)
        trend_line = slope * x + intercept

        # 季节因子：各月均值 / 全年均值
        monthly_avg = monthly.groupby(monthly.index.month).mean()
        overall_avg = y.mean()
        seasonal = (monthly_avg / overall_avg).to_dict()

        # 拟合残差（用于估算预测区间）
        detrend = y - trend_line
        fitted_seasonal = np.array([seasonal[m.month] for m in t])
        resid = y - trend_line * fitted_seasonal
        resid_std = resid.std()

        # 预测未来 FORECAST_MONTHS 个月
        future_x = np.arange(len(y), len(y) + FORECAST_MONTHS)
        future_t = pd.date_range(t[-1] + pd.offsets.MonthEnd(1), periods=FORECAST_MONTHS, freq="ME")
        pred = (slope * future_x + intercept) * np.array([seasonal[m.month] for m in future_t])
        pred_lo = pred - 1.96 * resid_std
        pred_hi = pred + 1.96 * resid_std

        # 环比增速
        last_month = y[-1]
        growth = (pred[0] / last_month - 1) if last_month > 0 else 0
        avg_growth = (slope * 12 / overall_avg) if overall_avg > 0 else 0  # 年化趋势增速近似

        kpis = [
            {"label": f"未来 {FORECAST_MONTHS} 个月预测 GMV", "value": self.fmt_money(pred.sum())},
            {"label": "下月预测", "value": self.fmt_money(pred[0]), "hint": f"环比 {growth:+.1%}"},
            {"label": "月度趋势", "value": f"{slope:+,.0f} 元/月", "hint": f"年化约 {avg_growth:+.1%}"},
            {"label": "季节强度", "value": f"{max(seasonal.values()) / min(seasonal.values()):.1f} 倍", "hint": "峰谷月份差异"},
        ]

        # 图：历史 + 趋势 + 预测区间
        fig, ax = plt.subplots(figsize=(10, 4.0))
        ax.plot(t, y / 1e4, marker="o", color=viz.PALETTE[0], linewidth=2, label="实际 GMV")
        ax.plot(t, (trend_line * fitted_seasonal) / 1e4, color=viz.PALETTE[3], linestyle="--", alpha=0.7, label="拟合")
        ax.plot(future_t, pred / 1e4, marker="s", color=viz.PALETTE[2], linewidth=2, label="预测")
        ax.fill_between(future_t, pred_lo / 1e4, pred_hi / 1e4, color=viz.PALETTE[2], alpha=0.15, label="95% 区间")
        ax.set_title(f"月度 GMV 走势与未来 {FORECAST_MONTHS} 个月预测（万元）")
        ax.legend(loc="upper left")
        ax.tick_params(axis="x", rotation=45)
        viz.apply_style(ax)
        c1 = Chart("GMV 趋势与预测", viz.save_fig(fig, "forecast_gmv.png"), "实线=历史，方块=预测，阴影=95% 置信区间。")

        peak_m = max(seasonal, key=seasonal.get)
        trough_m = min(seasonal, key=seasonal.get)
        insights = [
            f"基于近 {len(y)} 个月的 GMV 序列，未来 {FORECAST_MONTHS} 个月预计累计 GMV {self.fmt_money(pred.sum())}，下月环比 {growth:+.1%}。",
            f"趋势项为 {slope:+,.0f} 元/月（年化约 {avg_growth:+.1%}），呈{'上升' if slope > 0 else '下滑'}态势。",
            f"季节性明显：{peak_m} 月为旺季（季节因子 {seasonal[peak_m]:.2f}），{trough_m} 月为淡季（{seasonal[trough_m]:.2f}），峰谷差 {max(seasonal.values()) / min(seasonal.values()):.1f} 倍。",
        ]
        recommendations = [
            f"在旺季（{peak_m} 月）前 1 个月完成备货与营销预热，承接季节性需求爆发。",
            "预测为「趋势 × 季节」的可解释外推，若有大促、政策或供给端变化，需叠加事件修正。",
            "把预测纳入月度经营会，滚动更新，偏差超 15% 时复盘趋势假设。",
        ]
        return AnalysisResult("销售趋势与预测", kpis, [c1], insights, recommendations)

    def _too_short(self):
        return AnalysisResult(
            "销售趋势与预测", [], [],
            ["月度数据样本过少（<6 个完整月），无法进行可靠的趋势与季节分解预测。"],
            ["建议积累至少 12 个月的数据后再启用预测模块。"],
        )
