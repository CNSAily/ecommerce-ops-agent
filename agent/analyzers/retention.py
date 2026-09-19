# -*- coding: utf-8 -*-
"""复购与留存分析：按月队列看新老用户黏性。"""

import matplotlib.pyplot as plt
import numpy as np

from agent import viz
from agent.data import effective_orders
from .base import Analyzer, AnalysisResult, Chart


class RetentionAnalyzer(Analyzer):
    name = "retention"
    keywords = ["复购", "留存", "回头客", "粘性", "忠诚", "回购", "老客", "新客"]

    def run(self, data):
        orders = data["orders"]
        eff = effective_orders(orders)

        per_user = eff.groupby("user_id")["order_id"].count()
        repeat_rate = (per_user >= 2).mean()
        avg_freq = per_user.mean()

        # 队列留存：按首次下单月份分群，看后续各月仍有下单的比例
        eff = eff.copy()
        eff["month"] = eff["order_time"].dt.to_period("M")
        first_month = eff.groupby("user_id")["month"].min().rename("first_month")
        eff = eff.merge(first_month, on="user_id")
        cohort_size = eff.groupby("first_month")["user_id"].nunique()

        cohorts = {}
        for cm, grp in eff.groupby("first_month"):
            months = sorted(grp["month"].unique())
            for m in months:
                idx = (m - cm).n
                if idx >= 0:
                    cohorts.setdefault(cm, {})[idx] = grp[grp["month"] == m]["user_id"].nunique()

        # 构建留存矩阵（保留前 6 个 cohort 展示）
        cm_list = sorted(cohort_size.index)[:6]
        if cm_list:
            max_idx = 7
            mat = np.full((len(cm_list), max_idx), np.nan)
            for i, cm in enumerate(cm_list):
                size = cohort_size[cm]
                for j in range(max_idx):
                    if cm in cohorts and j in cohorts[cm]:
                        mat[i, j] = cohorts[cm][j] / size
            fig1, ax = plt.subplots(figsize=(8, 3.8))
            im = ax.imshow(mat, cmap="YlGnBu", aspect="auto")
            ax.set_xticks(range(max_idx))
            ax.set_xticklabels([f"M{i}" for i in range(max_idx)])
            ax.set_yticks(range(len(cm_list)))
            ax.set_yticklabels([str(c) for c in cm_list])
            for i in range(mat.shape[0]):
                for j in range(max_idx):
                    if not np.isnan(mat[i, j]):
                        ax.text(j, i, f"{mat[i, j]:.0%}", ha="center", va="center", fontsize=8,
                                color="white" if mat[i, j] > 0.6 else "#333")
            ax.set_title("月度队列留存矩阵（行=首购月，列=第 N 月留存率）")
            fig1.colorbar(im, ax=ax, fraction=0.046)
            c1 = Chart("队列留存矩阵", viz.save_fig(fig1, "retention_cohort.png"), "颜色越深留存越高。")
        else:
            c1 = None

        kpis = [
            {"label": "复购率（≥2单）", "value": self.fmt_pct(repeat_rate)},
            {"label": "人均下单频次", "value": f"{avg_freq:.2f} 单"},
            {"label": "下单用户数", "value": f"{len(per_user):,}"},
        ]

        m1 = [cohorts[cm][1] / cohort_size[cm] for cm in cm_list if cm in cohorts and 1 in cohorts[cm]]
        if len(m1) >= 4:
            early, late = float(np.mean(m1[:2])), float(np.mean(m1[-2:]))
            drift = (
                f"早期 cohort（{cm_list[0]} 起）M1 留存率平均 {early:.0%}，最近 cohort 平均 {late:.0%}，"
                + ("老客沉淀优于新客承接，需关注新客质量。" if early > late else "新客留存质量在改善，运营动作见效。")
            )
        else:
            drift = "各月 cohort 的 M1 留存存在波动，建议持续观察新客承接质量。"

        insights = [
            f"整体复购率为 {repeat_rate:.1%}，人均下单 {avg_freq:.2f} 次，用户粘性属{'较高' if repeat_rate >= 0.5 else '中等' if 0.2 < repeat_rate < 0.5 else '偏弱'}水平。",
            "从留存矩阵看，首购后第 1 个月的留存下降最陡，说明「首购 → 二购」是关键流失漏斗，需要重点干预。",
            drift,
        ]
        recommendations = [
            "在首购完成后 7 天内推送「二单专享券 + 关联品类推荐」，把首购用户尽快转化为二购。",
            "建立新客 90 天 onboarding 计划（注册礼 → 首单礼 → 复购礼），系统性拉升前 3 个月留存。",
            "对沉默超 30 天的用户触发自动召回，而非等其彻底流失再挽回。",
        ]
        charts = [c1] if c1 else []
        return AnalysisResult("复购与留存分析", kpis, charts, insights, recommendations)
