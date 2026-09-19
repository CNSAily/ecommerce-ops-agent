# -*- coding: utf-8 -*-
"""RFM 用户分层分析：识别高价值用户与流失风险。"""

import matplotlib.pyplot as plt

from agent import viz
from agent.data import effective_orders
from .base import Analyzer, AnalysisResult, Chart, CUR

SEGMENT_ORDER = ["重要价值", "潜力用户", "重要发展", "新用户", "流失风险", "低价值"]
SEGMENT_COLOR = {
    "重要价值": "#E45756", "潜力用户": "#F58518", "重要发展": "#72B7B2",
    "新用户": "#54A24B", "流失风险": "#B279A2", "低价值": "#9aa0a6",
}


class CustomerAnalyzer(Analyzer):
    name = "customer"
    keywords = ["用户", "客户", "分层", "rfm", "高价值", "会员", "人群", "画像", "细分"]

    def run(self, data):
        orders = data["orders"]
        eff = effective_orders(orders)
        now = eff["order_time"].max()

        rfm = eff.groupby("user_id").agg(
            last=("order_time", "max"),
            F=("order_id", "count"),
            M=("amount", "sum"),
        ).reset_index()
        rfm["R"] = (now - rfm["last"]).dt.days

        # R 用中位数切「近/远」，F、M 用 75 分位切「高/低」——
        # 避免 F 与 M 高度相关时中位数切分导致某些象限几乎为空
        r_med = rfm["R"].median()
        f_th = rfm["F"].quantile(0.75)
        m_th = rfm["M"].quantile(0.75)

        def seg(row):
            near = row["R"] <= r_med
            freq = row["F"] >= f_th
            rich = row["M"] >= m_th
            if near and freq and rich:
                return "重要价值"
            if near and freq and not rich:
                return "潜力用户"
            if near and not freq and rich:
                return "重要发展"
            if near and not freq and not rich:
                return "新用户"
            if not near and rich:
                return "流失风险"
            return "低价值"

        rfm["segment"] = rfm.apply(seg, axis=1)

        seg_stat = rfm.groupby("segment").agg(
            人数=("user_id", "count"),
            贡献GMV=("M", "sum"),
        ).reindex(SEGMENT_ORDER)
        total_gmv = rfm["M"].sum()
        seg_stat["GMV占比"] = seg_stat["贡献GMV"] / total_gmv
        seg_stat["人均贡献"] = seg_stat["贡献GMV"] / seg_stat["人数"]

        vip = seg_stat.loc["重要价值"]
        at_risk = seg_stat.loc["流失风险"]

        kpis = [
            {"label": "重要价值用户", "value": f"{int(vip['人数']):,}", "hint": f"贡献 GMV {self.fmt_pct(vip['GMV占比'])}"},
            {"label": "流失风险用户", "value": f"{int(at_risk['人数']):,}", "hint": f"贡献 GMV {self.fmt_pct(at_risk['GMV占比'])}"},
            {"label": "复购用户数", "value": f"{int((rfm['F'] >= 2).sum()):,}"},
            {"label": "人均客单价值", "value": f"{CUR}{rfm['M'].mean():.0f}"},
        ]

        # 图1：分层人数与 GMV 占比
        fig1, ax1 = plt.subplots(figsize=(9, 3.6))
        x = range(len(seg_stat))
        colors = [SEGMENT_COLOR[s] for s in seg_stat.index]
        ax1.bar(x, seg_stat["人数"].values, color=colors)
        ax1.set_xticks(list(x))
        ax1.set_xticklabels(seg_stat.index)
        ax1.set_ylabel("用户数")
        for i, (pct, cnt) in enumerate(zip(seg_stat["GMV占比"], seg_stat["人数"])):
            ax1.text(i, cnt, f"{pct:.0%}", ha="center", va="bottom", fontsize=8, color="#555")
        ax1.set_title("RFM 用户分层：人数与 GMV 占比")
        viz.apply_style(ax1)
        c1 = Chart("RFM 用户分层", viz.save_fig(fig1, "customer_segments.png"), "柱高=人数，柱顶=该层 GMV 占比。")

        # 图2：各层人均贡献
        fig2, ax2 = plt.subplots(figsize=(9, 3.0))
        ax2.bar(seg_stat.index, seg_stat["人均贡献"].values, color=[SEGMENT_COLOR[s] for s in seg_stat.index])
        ax2.set_title("各分层人均 GMV 贡献（元）")
        ax2.tick_params(axis="x", rotation=20)
        viz.apply_style(ax2)
        c2 = Chart("各层人均贡献", viz.save_fig(fig2, "customer_per_capita.png"), "头部层价值密度远高于长尾。")

        insights = [
            f"「重要价值」用户 {int(vip['人数']):,} 人（占 {vip['人数']/len(rfm):.1%}），却贡献了 {vip['GMV占比']:.1%} 的 GMV，是平台的绝对核心资产。",
            f"「流失风险」用户 {int(at_risk['人数']):,} 人、贡献 {at_risk['GMV占比']:.1%} GMV，历史上高价值但已长时间未复购，是最大挽回对象。",
            f"「低价值」用户数量最多但人均贡献仅 {CUR}{seg_stat.loc['低价值','人均贡献']:.0f}，属长尾，需控制触达成本。",
            f"用户价值呈典型的二八分化：约 {int((seg_stat.loc[['重要价值','潜力用户','重要发展']]['人数']).sum()/len(rfm)*100)}% 的核心层贡献了绝大部分营收。",
        ]
        recommendations = [
            "对「重要价值」用户建立专属客服 + 生日礼 + 提前购特权，防止流失。",
            "对「流失风险」用户启动定向召回：高价值券 + 短信/私域触达，设定 30 天召回窗口。",
            "对「潜力用户」用「凑单满减 + 会员日」提升其消费频次，向重要价值层转化。",
        ]
        return AnalysisResult("RFM 用户分层与价值分析", kpis, [c1, c2], insights, recommendations)
