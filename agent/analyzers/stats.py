# -*- coding: utf-8 -*-
"""统计检验：用假设检验验证业务假设，把分析从「描述」升级到「诊断」。

检验内容（依赖 scipy，可选）：
1. 复购 vs 单次购买用户的客单价差异（Welch t 检验）
2. 支付方式与客单价的关联（单因素方差分析 ANOVA）
3. 品类间评分差异（ANOVA，需 review_score，仅 Olist 数据可用）
4. 评分与订单金额的相关性（Pearson，需 review_score）
"""

import matplotlib.pyplot as plt
import numpy as np

from agent import viz
from agent.data import effective_orders
from .base import Analyzer, AnalysisResult, Chart, CUR


class StatsAnalyzer(Analyzer):
    name = "stats"
    keywords = ["检验", "显著性", "相关", "卡方", "t检验", "假设检验", "差异", "统计", "p值", "anova"]

    def run(self, data):
        try:
            from scipy import stats as st
        except ImportError:
            return AnalysisResult(
                "统计检验", [], [],
                ["未安装 scipy，无法进行统计检验。请 `pip install scipy` 后重试。"], []
            )

        eff = effective_orders(data["orders"])
        has_review = "review_score" in eff.columns and eff["review_score"].notna().sum() > 100
        findings = []

        # 1. 复购 vs 单次购买客单价（Welch t 检验）
        u = eff.groupby("user_id").agg(freq=("order_id", "count"), aov=("amount", "mean")).reset_index()
        repeat = u[u["freq"] >= 2]["aov"]
        once = u[u["freq"] == 1]["aov"]
        if len(repeat) > 30 and len(once) > 30:
            t_stat, p_val = st.ttest_ind(repeat, once, equal_var=False)
            findings.append({
                "name": "复购 vs 单次用户客单价",
                "method": "Welch t 检验",
                "stat": t_stat, "p": p_val, "sig": p_val < 0.05,
                "detail": f"复购均值 {CUR}{repeat.mean():.0f} vs 单次 {CUR}{once.mean():.0f}",
            })

        # 2. 支付方式与客单价（ANOVA）
        pay_groups = [
            g["amount"].values
            for _, g in eff.groupby("pay_method")
            if len(g) > 50
        ]
        if len(pay_groups) >= 3:
            f_stat, p_val = st.f_oneway(*pay_groups)
            findings.append({
                "name": "支付方式与客单价",
                "method": "单因素 ANOVA",
                "stat": f_stat, "p": p_val, "sig": p_val < 0.05,
                "detail": f"{len(pay_groups)} 种支付方式间客单价对比",
            })

        # 3. 品类评分差异（ANOVA，仅 Olist）
        if has_review:
            top_cats = eff.groupby("category")["order_id"].count().nlargest(6).index
            cat_scores = {
                c: eff.loc[eff["category"] == c, "review_score"].dropna().values
                for c in top_cats
            }
            cat_scores = {c: v for c, v in cat_scores.items() if len(v) > 50}
            if len(cat_scores) >= 3:
                f_stat, p_val = st.f_oneway(*list(cat_scores.values()))
                findings.append({
                    "name": "品类间评分差异",
                    "method": "单因素 ANOVA",
                    "stat": f_stat, "p": p_val, "sig": p_val < 0.05,
                    "detail": f"Top {len(cat_scores)} 品类评分对比",
                })

            # 4. 评分与金额相关性（Pearson）
            mask = eff["review_score"].notna()
            r, p_val = st.pearsonr(eff.loc[mask, "review_score"], eff.loc[mask, "amount"])
            findings.append({
                "name": "评分与订单金额相关性",
                "method": "Pearson 相关",
                "stat": r, "p": p_val, "sig": p_val < 0.05,
                "detail": f"r = {r:.3f}",
            })

        if not findings:
            return AnalysisResult("统计检验", [], [], ["数据不足以进行有意义的统计检验。"], [])

        sig_count = sum(1 for f in findings if f["sig"])
        kpis = [
            {"label": "检验项数", "value": f"{len(findings)}"},
            {"label": "显著项", "value": f"{sig_count}", "hint": "p < 0.05"},
        ]

        # 图：复购 vs 单次客单价箱线图
        fig, ax = plt.subplots(figsize=(7, 3.6))
        ax.boxplot([once, repeat], tick_labels=["单次购买", "复购用户"], widths=0.5)
        ax.set_ylabel("客单价（元）")
        ax.set_title("复购 vs 单次购买客单价分布")
        viz.apply_style(ax)
        c1 = Chart("复购 vs 单次客单价", viz.save_fig(fig, "stats_aov_box.png"), "箱线图对比两群体客单价分布。")

        insights = []
        for f in findings:
            verdict = "显著" if f["sig"] else "不显著"
            insights.append(
                f"【{f['name']}】{f['method']}：{f['detail']}，p = {f['p']:.4f}，差异{'显著' if f['sig'] else '不显著'}。"
            )
        insights.append(
            f"共 {len(findings)} 项检验，{sig_count} 项达到统计显著（p<0.05），为运营决策提供了可量化的依据。"
        )

        recommendations = [
            "对显著项落地对应策略（如复购客单价显著更高 → 加大首购转二购投入）。",
            "不显著项避免过度解读，可扩大样本或引入协变量后再验证。",
            "注意：统计显著 ≠ 因果成立，需结合业务机制与实验设计确认。",
        ]
        return AnalysisResult("统计检验与显著性分析", kpis, [c1], insights, recommendations)
