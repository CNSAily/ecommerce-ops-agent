# -*- coding: utf-8 -*-
"""品类 / 品牌分析：谁是营收主力，谁有增长潜力。"""

import matplotlib.pyplot as plt

from agent import viz
from agent.data import effective_orders
from .base import Analyzer, AnalysisResult, Chart, CUR


class ProductAnalyzer(Analyzer):
    name = "product"
    keywords = ["品类", "类目", "商品", "品牌", "产品", "卖得", "畅销", "top", "sku"]

    def run(self, data):
        orders = data["orders"]
        eff = effective_orders(orders)

        cat_gmv = eff.groupby("category")["amount"].sum().sort_values(ascending=False)
        cat_aov = eff.groupby("category").apply(lambda g: g["amount"].sum() / len(g)).sort_values(ascending=False)
        brand_gmv = eff.groupby("brand")["amount"].sum().sort_values(ascending=False).head(10)

        top_cat = cat_gmv.idxmax()
        top_brand = brand_gmv.idxmax()
        tail_cat = cat_gmv.idxmin()

        kpis = [
            {"label": "第一品类", "value": viz.pretty_label(top_cat), "hint": self.fmt_money(cat_gmv.max())},
            {"label": "第一品牌", "value": viz.pretty_label(top_brand), "hint": self.fmt_money(brand_gmv.max())},
            {"label": "品类数", "value": str(len(cat_gmv))},
            {"label": "客单最高品类", "value": viz.pretty_label(cat_aov.idxmax()), "hint": f"{CUR}{cat_aov.max():.0f}"},
        ]

        # 图1：品类 GMV 排名（Top 12 + 其他，中文标签，动态高度）
        c_labels, c_vals = viz.top_n(cat_gmv, 12)
        labels_r = [viz.pretty_label(x) for x in c_labels][::-1]
        vals_r = c_vals[::-1]
        n = len(labels_r)
        fig1, ax = plt.subplots(figsize=(9, max(3.2, 0.38 * n + 1.0)))
        y = list(range(n))
        ax.barh(y, [v / 1e4 for v in vals_r], color=viz.PALETTE[0])
        ax.set_yticks(y)
        ax.set_yticklabels(labels_r, fontsize=10)
        for i, v in enumerate(vals_r):
            ax.text(v / 1e4, i, f" {v / 1e4:.0f}万", va="center", fontsize=9)
        ax.set_title("各品类 GMV（万元，Top 12）")
        viz.apply_style(ax)
        c1 = Chart("品类 GMV 排名", viz.save_fig(fig1, "product_category.png"), "头部品类贡献集中。")

        # 图2：Top10 品牌（hash 截断为前 8 位）
        brand_labels = [viz.pretty_label(b) for b in brand_gmv.index]
        fig2, ax2 = plt.subplots(figsize=(9, 3.2))
        ax2.bar(brand_labels, brand_gmv.values / 1e4, color=viz.PALETTE[3])
        ax2.set_title("Top10 品牌 GMV（万元）")
        ax2.tick_params(axis="x", rotation=45, labelsize=8)
        viz.apply_style(ax2)
        c2 = Chart("Top10 品牌 GMV", viz.save_fig(fig2, "product_brand.png"), "头部品牌表现（Olist 品牌已匿名化）。")

        # 图3：品类客单价（Top 12）
        a_labels, a_vals = viz.top_n(cat_aov, 12)
        a_labels_cn = [viz.pretty_label(x) for x in a_labels]
        fig3, ax3 = plt.subplots(figsize=(9, 3.4))
        ax3.bar(range(len(a_vals)), a_vals, color=viz.PALETTE[2])
        ax3.set_xticks(range(len(a_labels_cn)))
        ax3.set_xticklabels(a_labels_cn, rotation=45, ha="right", fontsize=9)
        for i, v in enumerate(a_vals):
            ax3.text(i, v, f"{CUR}{v:.0f}", ha="center", va="bottom", fontsize=8)
        ax3.set_title("各品类客单价（Top 12）")
        viz.apply_style(ax3)
        c3 = Chart("品类客单价", viz.save_fig(fig3, "product_aov.png"), "客单价反映品类消费属性。")

        cr = cat_gmv.max() / cat_gmv.sum()
        insights = [
            f"「{viz.pretty_label(top_cat)}」是绝对营收主力，贡献 GMV {self.fmt_money(cat_gmv.max())}，占比 {cr:.1%}。",
            f"品牌层面「{viz.pretty_label(top_brand)}」领先，Top10 品牌合计贡献 GMV 的 {brand_gmv.sum()/eff['amount'].sum():.1%}。",
            f"「{viz.pretty_label(cat_aov.idxmax())}」客单价最高（{CUR}{cat_aov.max():.0f}），适合做高客单、高毛利的主推；「{viz.pretty_label(tail_cat)}」盘子最小，属长尾。",
            "品类结构呈「一超多强」格局，营收对单一品类依赖度偏高。",
        ]
        recommendations = [
            f"守住「{viz.pretty_label(top_cat)}」基本盘的同时，把营销资源向客单价高、增速快的第二梯队品类倾斜，降低集中度风险。",
            "对客单价低但高频的品类，设计「组合购 + 满减」提升连带率和客单。",
        ]
        return AnalysisResult("品类与品牌结构分析", kpis, [c1, c2, c3], insights, recommendations)
