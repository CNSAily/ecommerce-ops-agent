# -*- coding: utf-8 -*-
"""客户终身价值（CLV）预测。

用 lifetimes 库拟合 BG/NBD（购买频次）+ Gamma-Gamma（客单价）概率模型，
预测每位复购客户未来 12 个月的终身价值，识别高价值客户、指导预算分配。

若未安装 lifetimes（可选依赖），自动降级为简化 CLV 估算（历史频率外推）。
"""

import contextlib
import io

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from agent import viz
from agent.data import effective_orders
from .base import Analyzer, AnalysisResult, Chart, CUR

HORIZON_MONTHS = 12


class ClvAnalyzer(Analyzer):
    name = "clv"
    keywords = ["clv", "终身价值", "客户价值", "lifetime", "ltv", "价值预测", "用户价值", "高价值客户"]

    def run(self, data):
        eff = effective_orders(data["orders"])
        now = eff["order_time"].max()

        try:
            from lifetimes import BetaGeoFitter, GammaGammaFitter
            from lifetimes.utils import summary_data_from_transaction_data
        except ImportError:
            return self._fallback(eff, now, "（未安装 lifetimes，采用简化估算）")

        try:
            obs_end = now + pd.Timedelta(days=1)
            rfm = summary_data_from_transaction_data(
                eff[["user_id", "order_time", "amount"]],
                customer_id_col="user_id",
                datetime_col="order_time",
                monetary_value_col="amount",
                observation_period_end=obs_end,
                freq="D",
            )

            with contextlib.redirect_stdout(io.StringIO()):
                bgf = BetaGeoFitter(penalizer_coef=0.01)
                bgf.fit(rfm["frequency"], rfm["recency"], rfm["T"])

                rfm_rep = rfm[rfm["frequency"] > 0].copy()
                if len(rfm_rep) < 50:
                    return self._fallback(eff, now, "（复购样本过少，采用简化估算）")

                ggf = GammaGammaFitter(penalizer_coef=0.01)
                ggf.fit(rfm_rep["frequency"], rfm_rep["monetary_value"])

                clv = ggf.customer_lifetime_value(
                    bgf,
                    rfm_rep["frequency"], rfm_rep["recency"], rfm_rep["T"],
                    rfm_rep["monetary_value"],
                    time=HORIZON_MONTHS, discount_rate=0.01,
                )

            return self._build_result(clv, len(rfm), len(rfm_rep), now, method="BG/NBD + Gamma-Gamma")
        except Exception:
            # 模型未收敛（如复购率异常高、样本分布不符合 BG/NBD 假设）时降级
            return self._fallback(eff, now, "（模型未收敛，采用简化估算）")

    # ------------------------------------------------------------------
    def _build_result(self, clv, n_all, n_rep, now, method):
        clv = clv.sort_values(ascending=False)
        total = clv.sum()
        top10 = clv.iloc[: max(1, int(len(clv) * 0.1))]
        top10_share = top10.sum() / total if total > 0 else 0
        mean_clv = clv.mean()
        median_clv = clv.median()

        kpis = [
            {"label": "可计算 CLV 客户", "value": f"{len(clv):,}", "hint": f"复购用户占比 {n_rep / n_all:.1%}"},
            {"label": "未来 12 月总 CLV", "value": self.fmt_money(total)},
            {"label": "人均 CLV", "value": f"{CUR}{mean_clv:.0f}", "hint": f"中位数 {CUR}{median_clv:.0f}"},
            {"label": "Top 10% 客户价值占比", "value": self.fmt_pct(top10_share)},
        ]

        # 图1：CLV 分布（对数刻度）
        fig1, ax1 = plt.subplots(figsize=(9, 3.4))
        ax1.hist(clv.values, bins=50, color=viz.PALETTE[0], alpha=0.85)
        ax1.set_xscale("log")
        ax1.set_xlabel("CLV（元，对数刻度）")
        ax1.set_ylabel("客户数")
        ax1.set_title("客户终身价值分布（未来 12 个月）")
        viz.apply_style(ax1)
        c1 = Chart("CLV 分布", viz.save_fig(fig1, "clv_distribution.png"), "长尾分布：少数客户贡献绝大部分价值。")

        # 图2：Top 20 客户（user_id 截断为前 8 位）
        top20 = clv.head(20)
        user_labels = [viz.pretty_label(u) for u in top20.index]
        fig2, ax2 = plt.subplots(figsize=(9, 4.0))
        y = list(range(len(top20)))[::-1]
        ax2.barh(y, top20.values, color=viz.PALETTE[2])
        ax2.set_yticks(y)
        ax2.set_yticklabels(user_labels, fontsize=9)
        ax2.set_xlabel("CLV（元）")
        ax2.set_title("Top 20 高价值客户")
        viz.apply_style(ax2)
        c2 = Chart("Top 20 高价值客户", viz.save_fig(fig2, "clv_top20.png"), "头部客户的终身价值显著高于均值。")

        insights = [
            f"采用 {method} 模型，{len(clv):,} 位复购客户的未来 12 个月总 CLV 约 {self.fmt_money(total)}。",
            f"客户价值呈强长尾分布：Top 10% 客户贡献 {top10_share:.1%} 的 CLV，人均 {CUR}{top10.sum()/len(top10):.0f}，是中位数的 {top10.sum()/max(len(top10),1)/median_clv:.0f} 倍。",
            f"仅 {n_rep/n_all:.1%} 的用户产生过复购，绝大多数用户为单次购买，拉低整体 LTV——提升「首购→二购」转化是价值增长的核心杠杆。",
        ]
        recommendations = [
            "对 CLV Top 10% 客户建立专属运营：VIP 客服、专属折扣、提前购，锁定其长期价值。",
            "对中腰部复购客户设计「阶梯式会员」，用成长权益提升购买频次，向高价值层迁移。",
            "把获客预算从「广撒网」转向「高 CLV 人群画像」定向投放，降低 CAC、提升 LTV/CAC 比值。",
        ]
        return AnalysisResult("客户终身价值（CLV）预测", kpis, [c1, c2], insights, recommendations)

    # ------------------------------------------------------------------
    def _fallback(self, eff, now, note=""):
        per_user = eff.groupby("user_id").agg(
            freq=("order_id", "count"),
            value=("amount", "sum"),
        )
        per_user["aov"] = per_user["value"] / per_user["freq"]
        repeat_rate = (per_user["freq"] >= 2).mean()
        # 预计未来 12 个月购买次数：复购用户按历史频率折半外推，单次用户给复购率基线
        per_user["pred_freq"] = np.where(
            per_user["freq"] >= 2, per_user["freq"] * 0.5, 0.1 + repeat_rate
        )
        per_user["clv"] = per_user["aov"] * per_user["pred_freq"]
        clv = per_user["clv"].sort_values(ascending=False)
        return self._build_result(clv, len(per_user), int((per_user["freq"] >= 2).sum()), now, "简化估算" + note)
