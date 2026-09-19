# -*- coding: utf-8 -*-
"""
生成「云启严选 CloudPick」模拟电商运营数据。

产出三个数据表（data/raw/ 下，UTF-8-SIG 编码，Excel 可直接打开）：

- users.csv    用户维度表（20,000 行）
- orders.csv   订单事实表（100,000 行，核心分析对象）
- events.csv   用户行为事件表（300,000 行，漏斗 / 留存）

设计要点：
1. 确定性随机（seed 固定），任何人运行结果完全一致，可复现。
2. 数据里埋了「业务故事」，供 Agent 挖掘：
   - 节假日峰值（618 / 双11 / 双12）
   - 渠道差异（直播客单价高但退货率高；私域复购强）
   - 品类差异（食品饮料高频低客单，家居低频高客单）
   - 二八分化（约 20% 用户贡献 60% 订单）
   - 新老用户留存差距
"""

import os
import numpy as np
import pandas as pd

# ------------------------------------------------------------
# 全局参数
# ------------------------------------------------------------
SEED = 42
N_USERS = 20_000
N_ORDERS = 100_000
N_EVENTS = 300_000

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

# 品类及客单价参数（金额服从对数正态分布）
CATEGORIES = ["美妆个护", "家居生活", "数码配件", "食品饮料"]
CATEGORY_PROB = [0.30, 0.25, 0.20, 0.25]
CATEGORY_MEAN = {"美妆个护": 180.0, "家居生活": 260.0, "数码配件": 150.0, "食品饮料": 80.0}

# 品类下的品牌
CATEGORY_BRANDS = {
    "美妆个护": ["花西子", "完美日记", "薇诺娜", "珂拉琪"],
    "家居生活": ["无印良品", "网易严选", "名创优品", "京造"],
    "数码配件": ["小米", "绿联", "倍思", "Anker"],
    "食品饮料": ["三只松鼠", "良品铺子", "元气森林", "百草味"],
}

# 渠道
CHANNELS = ["自然搜索", "信息流广告", "社交裂变", "直播带货", "私域社群"]
CHANNEL_PROB = [0.30, 0.25, 0.20, 0.15, 0.10]

# 支付方式
PAY_METHODS = ["微信支付", "支付宝", "银联", "货到付款"]
PAY_METHOD_PROB = [0.45, 0.40, 0.10, 0.05]

# 订单状态：成功 / 取消 / 退货
STATUSES = ["成功", "取消", "退货"]
STATUS_PROB = [0.88, 0.05, 0.07]

# 事件类型
EVENT_TYPES = ["浏览", "加购", "下单", "支付"]

# 城市（模拟一二线城市集中分布，权重递减）
CITIES = [
    "上海", "北京", "深圳", "广州", "杭州", "成都", "武汉", "南京", "苏州", "西安",
    "重庆", "长沙", "郑州", "青岛", "东莞", "宁波", "天津", "合肥", "福州", "厦门",
]
CITY_PROB = np.array([0.11, 0.10, 0.08, 0.07, 0.07, 0.06, 0.05, 0.05, 0.05, 0.04,
                      0.04, 0.04, 0.03, 0.03, 0.03, 0.03, 0.03, 0.03, 0.02, 0.02])
CITY_PROB = CITY_PROB / CITY_PROB.sum()

rng = np.random.default_rng(SEED)


def _weighted_choice(values, prob, size, rnd):
    """按概率向量化采样。"""
    idx = rnd.choice(len(values), size=size, p=prob)
    return np.asarray(values)[idx]


def _round_amount(a):
    return np.round(a, 2)


def generate_users():
    """用户维度表：注册时间越早，用户价值权重越高（老用户更活跃）。"""
    n = N_USERS
    user_id = np.array([f"U{str(i).zfill(6)}" for i in range(1, n + 1)])

    # 注册日期：2024-01-01 ~ 2025-12-31（约 40% 老用户、60% 新用户）
    start = pd.Timestamp("2024-01-01")
    end = pd.Timestamp("2025-12-31")
    signup_days = rng.integers(0, (end - start).days + 1, size=n)
    signup_date = start + pd.to_timedelta(signup_days, unit="D")

    channel = _weighted_choice(CHANNELS, CHANNEL_PROB, n, rng)
    city = _weighted_choice(CITIES, CITY_PROB, n, rng)
    age = np.clip(rng.normal(32, 8, size=n).astype(int), 16, 65)
    gender = rng.choice(["男", "女"], size=n, p=[0.45, 0.55])

    df = pd.DataFrame({
        "user_id": user_id,
        "signup_date": signup_date,
        "channel": channel,
        "city": city,
        "age": age,
        "gender": gender,
    })
    return df


def generate_orders(users):
    """订单事实表：用户按价值权重采样（二八分化）+ 品类/渠道/节假日埋点。"""
    n = N_ORDERS

    # 用户价值权重：帕累托分布，让少数用户贡献多数订单
    weights = rng.pareto(a=1.8, size=N_USERS)
    weights = weights / weights.sum()
    user_idx = rng.choice(N_USERS, size=n, p=weights)
    user_id = users["user_id"].iloc[user_idx].values
    signup_date = users["signup_date"].iloc[user_idx].values

    # 下单时间：2025 全年，节假日（6/11/12 月）加权重
    month_weights = np.array([1.0, 0.9, 0.9, 0.9, 1.0, 1.5,  # 6月=618
                              0.9, 0.9, 0.9, 1.0, 2.2, 1.6])  # 11月=双11, 12月=双12
    month_weights = month_weights / month_weights.sum()
    month = rng.choice(np.arange(1, 13), size=n, p=month_weights)
    day = rng.integers(1, 29, size=n)
    hour = rng.integers(0, 24, size=n)
    minute = rng.integers(0, 60, size=n)
    order_time = pd.to_datetime({
        "year": 2025, "month": month, "day": day, "hour": hour, "minute": minute
    })

    # 品类 + 金额（对数正态，按品类均值）
    category = _weighted_choice(CATEGORIES, CATEGORY_PROB, n, rng)
    amount = np.zeros(n)
    for cat in CATEGORIES:
        mask = category == cat
        cnt = mask.sum()
        mean = CATEGORY_MEAN[cat]
        amount[mask] = rng.lognormal(mean=np.log(mean) - 0.25, sigma=0.6, size=cnt)

    # 品牌 + 商品名
    brand = np.empty(n, dtype=object)
    product_name = np.empty(n, dtype=object)
    for cat in CATEGORIES:
        mask = category == cat
        brands = CATEGORY_BRANDS[cat]
        b = _weighted_choice(brands, [0.4, 0.3, 0.2, 0.1], mask.sum(), rng)
        brand[mask] = b
        seq = rng.integers(1, 200, size=mask.sum())
        product_name[mask] = [f"{b[i]}·{cat}系列{seq[i]}号" for i in range(len(b))]

    # 渠道（直播客单价上浮、退货率高）
    channel = _weighted_choice(CHANNELS, CHANNEL_PROB, n, rng)
    live_mask = channel == "直播带货"
    amount = np.where(live_mask, amount * 1.25, amount)

    # 订单状态：直播渠道退货率更高
    status = np.empty(n, dtype=object)
    for i in range(n):
        if channel[i] == "直播带货":
            p = [0.80, 0.06, 0.14]
        else:
            p = STATUS_PROB
        status[i] = rng.choice(STATUSES, p=p)
    # 取消/退货的订单不计入有效 GMV，但保留记录用于运营分析
    amount = _round_amount(amount)

    # 支付方式
    pay_method = _weighted_choice(PAY_METHODS, PAY_METHOD_PROB, n, rng)

    order_id = np.array([f"O{str(i).zfill(7)}" for i in range(1, n + 1)])

    df = pd.DataFrame({
        "order_id": order_id,
        "user_id": user_id,
        "order_time": order_time,
        "amount": amount,
        "category": category,
        "brand": brand,
        "product_name": product_name,
        "channel": channel,
        "pay_method": pay_method,
        "status": status,
    })
    return df


def generate_events(users):
    """用户行为事件表：浏览 -> 加购 -> 下单 -> 支付，用于漏斗 / 留存。"""
    n = N_EVENTS
    user_idx = rng.integers(0, N_USERS, size=n)
    user_id = users["user_id"].iloc[user_idx].values

    # 事件时间：2025 全年（对齐订单时间范围）
    day_offset = rng.integers(0, 365, size=n)
    event_time = pd.Timestamp("2025-01-01") + pd.to_timedelta(day_offset, unit="D")
    event_time = event_time + pd.to_timedelta(rng.integers(0, 86400, size=n), unit="s")

    # 事件类型按漏斗递减分布
    event_type = rng.choice(EVENT_TYPES, size=n, p=[0.60, 0.20, 0.12, 0.08])
    category = _weighted_choice(CATEGORIES, CATEGORY_PROB, n, rng)
    channel = _weighted_choice(CHANNELS, CHANNEL_PROB, n, rng)

    df = pd.DataFrame({
        "user_id": user_id,
        "event_type": event_type,
        "event_time": event_time,
        "category": category,
        "channel": channel,
    })
    return df


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    print(f"数据目录：{DATA_DIR}\n")

    users = generate_users()
    orders = generate_orders(users)
    events = generate_events(users)

    users.to_csv(os.path.join(DATA_DIR, "users.csv"), index=False, encoding="utf-8-sig")
    orders.to_csv(os.path.join(DATA_DIR, "orders.csv"), index=False, encoding="utf-8-sig")
    events.to_csv(os.path.join(DATA_DIR, "events.csv"), index=False, encoding="utf-8-sig")

    print(f"[OK] users.csv  {len(users):,} 行")
    print(f"[OK] orders.csv {len(orders):,} 行")
    print(f"[OK] events.csv {len(events):,} 行")
    print("\n生成完成。可运行 `python main.py \"近一年各月GMV趋势如何\"` 开始分析。")


if __name__ == "__main__":
    main()
