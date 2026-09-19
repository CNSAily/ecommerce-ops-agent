# -*- coding: utf-8 -*-
"""可视化工具：中文字体适配 + 通用绘图 / 保存。"""

import os
import re

import matplotlib

matplotlib.use("Agg")  # 无头后端，不弹窗

import matplotlib.pyplot as plt
from matplotlib import font_manager

from config import BASE_DIR, REPORT_DIR

ASSET_DIR = REPORT_DIR / "assets"
SVG_DIR = BASE_DIR / "docs" / "images"

# 中文字体候选（按优先级）
_CN_FONTS = [
    "Microsoft YaHei",
    "SimHei",
    "PingFang SC",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "WenQuanYi Zen Hei",
]

# 一套耐看的配色（深色主题友好，打印也清晰）
PALETTE = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2", "#B279A2"]

# Olist 品类名（英文下划线）→ 中文短名，解决图上长标签挤成一团的问题
CATEGORY_ZH = {
    "health_beauty": "健康美容", "watches_gifts": "手表礼品", "bed_bath_table": "床品卫浴",
    "sports_leisure": "运动休闲", "computers_accessories": "电脑配件", "furniture_decor": "家具装饰",
    "housewares": "家居用品", "cool_stuff": "潮流小物", "auto": "汽车用品", "garden_tools": "园艺工具",
    "toys": "玩具", "baby": "母婴用品", "perfumery": "香水", "telephony": "手机通讯",
    "office_furniture": "办公家具", "stationery": "文具", "pet_shop": "宠物用品", "computers": "电脑",
    "musical_instruments": "乐器", "electronics": "电子产品", "small_appliances": "小家电",
    "fashion_bags_accessories": "箱包配饰", "luggage_accessories": "旅行箱包", "consoles_games": "游戏主机",
    "construction_tools_construction": "建材工具", "home_appliances_2": "家用电器", "home_construction": "家装建材",
    "home_appliances": "大家电", "furniture_living_room": "客厅家具", "agro_industry_and_commerce": "农工商业",
    "home_confort": "家居舒适", "air_conditioning": "空调", "fixed_telephony": "固定电话",
    "kitchen_dining_laundry_garden_furniture": "厨餐花园家具", "audio": "音频设备",
    "books_general_interest": "大众图书", "small_appliances_home_oven_and_coffee": "烤箱咖啡小家电",
    "construction_tools_lights": "照明工具", "industry_commerce_and_business": "工商业务",
    "construction_tools_safety": "安全防护", "food": "食品", "market_place": "综合市场",
    "costruction_tools_garden": "园艺建材", "fashion_shoes": "鞋履", "signaling_and_security": "安防信号",
    "art": "艺术品", "drinks": "饮品", "furniture_bedroom": "卧室家具", "books_technical": "技术图书",
    "food_drink": "食品饮料", "costruction_tools_tools": "手动工具", "fashion_male_clothing": "男装",
    "christmas_supplies": "圣诞用品", "fashion_underwear_beach": "内衣沙滩装",
    "tablets_printing_image": "平板打印影像", "cine_photo": "影音摄影", "music": "音乐",
    "furniture_mattress_and_upholstery": "床垫软装", "dvds_blu_ray": "DVD蓝光", "party_supplies": "派对用品",
    "books_imported": "进口图书", "portateis_cozinha_e_preparadores_de_alimentos": "厨房料理",
    "fashio_female_clothing": "女装", "fashion_sport": "运动服饰", "la_cuisine": "厨房",
    "arts_and_craftmanship": "手工艺品", "diapers_and_hygiene": "尿裤卫生", "flowers": "鲜花",
    "pc_gamer": "游戏电脑", "home_comfort_2": "家居舒适", "cds_dvds_musicals": "CD音乐",
    "fashion_childrens_clothes": "童装", "security_and_services": "安全服务",
}

# Olist 支付方式 → 中文（渠道模块在 Olist 下降级为支付方式维度）
PAY_METHOD_ZH = {
    "credit_card": "信用卡", "boleto": "银行汇票", "voucher": "代金券", "debit_card": "借记卡",
}

# 32 位 hex 哈希（Olist 匿名化的 user_id / brand）
_HEX32 = re.compile(r"^[0-9a-f]{32}$")


def _has_cjk(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in s)


def pretty_label(s, maxlen: int = 12) -> str:
    """把内部编码值渲染成可读标签：
    中文映射 → 32 位 hash 截断 → 英文下划线转空格 + 截断 → 中文原样返回。"""
    if s is None:
        return "未知"
    s = str(s)
    if s in CATEGORY_ZH:
        return CATEGORY_ZH[s]
    if s in PAY_METHOD_ZH:
        return PAY_METHOD_ZH[s]
    if _HEX32.match(s):
        return s[:8] + "…"
    if "_" in s:
        s = s.replace("_", " ")
    if len(s) > maxlen and not _has_cjk(s):
        s = s[:maxlen] + "…"
    return s


def top_n(s, n: int, other_label: str = "其他"):
    """取降序 Series 的 Top N，其余聚合并归入「其他」。返回 (labels, values)。"""
    s = s.sort_values(ascending=False)
    if len(s) <= n:
        return list(s.index), list(s.values)
    head = s.head(n)
    rest = s.iloc[n:].sum()
    labels = list(head.index) + [other_label]
    values = list(head.values) + [rest]
    return labels, values


def _setup_font():
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in _CN_FONTS:
        if name in installed:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False


_setup_font()


def save_fig(fig, name: str) -> str:
    """保存图：PNG 到 reports/assets（用于 HTML 报告），
    同时导出一份轻量 SVG 到 docs/images（用于 GitHub README 展示）。"""
    os.makedirs(ASSET_DIR, exist_ok=True)
    path = ASSET_DIR / name
    fig.savefig(path, dpi=110, bbox_inches="tight", facecolor="white")
    try:
        SVG_DIR.mkdir(parents=True, exist_ok=True)
        matplotlib.rcParams["svg.fonttype"] = "none"
        fig.savefig(SVG_DIR / name.replace(".png", ".svg"), bbox_inches="tight", facecolor="white")
        matplotlib.rcParams["svg.fonttype"] = "path"
    except Exception:
        pass
    plt.close(fig)
    return str(path)


def apply_style(ax):
    """统一图表风格。"""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.set_axisbelow(True)
