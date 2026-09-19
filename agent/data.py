# -*- coding: utf-8 -*-
"""数据中枢 DataHub：统一 Olist 真实数据与「云启严选」合成数据的访问接口。

上层 Analyzer 通过统一字段名取数，不感知具体数据源。对外暴露：

- orders  : 订单事实表（核心分析对象）
    order_id / user_id / order_time / amount / category / brand /
    product_name / channel / pay_method / status / region / review_score
- users   : 用户维度表（user_id 等）
- events  : 行为事件表（仅合成数据有；Olist 为空，漏斗走降级）
- source  : "olist" 或 "synthetic"

字段映射（Olist → 统一名）：
    customer_unique_id            → user_id
    order_purchase_timestamp      → order_time
    price + freight_value         → amount
    product_category_name_english → category
    payment_type                  → pay_method / channel（Olist 无营销渠道，用支付方式兜底）
    order_status（delivered 等）   → status（归一化：成功 / 取消 / 进行中）
    customer_state                → region
    review_score                  → review_score
"""

import os

import numpy as np
import pandas as pd

from config import DATA_DIR, PROCESSED_DIR

_cache = {}


def source_name() -> str:
    """探测数据源：存在 Olist 订单表则视为 olist，否则 synthetic。"""
    return "olist" if (DATA_DIR / "olist_orders_dataset.csv").exists() else "synthetic"


def load_all() -> dict:
    """加载数据（进程内缓存），返回 {"orders","users","events","source"}。"""
    src = source_name()
    if src in _cache:
        return _cache[src]
    data = _load_olist() if src == "olist" else _load_synthetic()
    data["source"] = src
    _cache[src] = data
    return data


def effective_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """有效订单 = 状态为「成功」的订单（Olist 中即已送达 delivered）。"""
    return orders[orders["status"] == "成功"].copy()


def export_for_sandbox() -> dict:
    """把 orders 导出为可序列化字典，供沙箱子进程加载。

    Olist 单表体积较大，沙箱只注入 orders（含分析所需全部字段）与 source。
    """
    data = load_all()
    return {
        "orders": data["orders"],
        "source": data["source"],
    }


# ---------------------------------------------------------------------------
# 合成数据（云启严选 CloudPick）
# ---------------------------------------------------------------------------
def _load_synthetic() -> dict:
    users = pd.read_csv(DATA_DIR / "users.csv")
    orders = pd.read_csv(DATA_DIR / "orders.csv")
    events = pd.read_csv(DATA_DIR / "events.csv")

    users["signup_date"] = pd.to_datetime(users["signup_date"])
    orders["order_time"] = pd.to_datetime(orders["order_time"])
    events["event_time"] = pd.to_datetime(events["event_time"])

    # 补齐统一 schema 字段
    orders = orders.merge(users[["user_id", "city"]], on="user_id", how="left")
    orders["region"] = orders["city"]
    orders["review_score"] = np.nan

    return {"orders": orders, "users": users, "events": events}


# ---------------------------------------------------------------------------
# Olist 真实数据（巴西电商）
# ---------------------------------------------------------------------------
def _load_olist() -> dict:
    def read(name):
        return pd.read_csv(DATA_DIR / name)

    orders = read("olist_orders_dataset.csv")
    items = read("olist_order_items_dataset.csv")
    products = read("olist_products_dataset.csv")
    customers = read("olist_customers_dataset.csv")
    payments = read("olist_order_payments_dataset.csv")
    reviews = read("olist_order_reviews_dataset.csv")
    translation = read("product_category_name_translation.csv")

    # 品类翻译为英文
    products = products.merge(translation, on="product_category_name", how="left")
    products["category"] = (
        products["product_category_name_english"].fillna(products["product_category_name"])
    )

    # 主表 join：orders × items × products × customers
    df = orders.merge(items, on="order_id", how="inner")
    df = df.merge(products[["product_id", "category"]], on="product_id", how="left")
    df = df.merge(
        customers[["customer_id", "customer_unique_id", "customer_state"]],
        on="customer_id",
        how="left",
    )

    # 支付方式聚合（取众数）
    pay_mode = (
        payments.groupby("order_id")["payment_type"]
        .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else "not_defined")
        .rename("pay_method")
        .reset_index()
    )
    df = df.merge(pay_mode, on="order_id", how="left")

    # 评分聚合（均值）
    rev = reviews.groupby("order_id")["review_score"].mean().rename("review_score").reset_index()
    df = df.merge(rev, on="order_id", how="left")

    # 时间与金额
    df["order_time"] = pd.to_datetime(df["order_purchase_timestamp"])
    df["amount"] = df["price"] + df["freight_value"]

    # 统一字段
    df["user_id"] = df["customer_unique_id"]
    df["brand"] = df["seller_id"]
    df["product_name"] = df["product_id"]
    df["channel"] = df["pay_method"]          # 无营销渠道，用支付方式兜底
    df["region"] = df["customer_state"]

    # 状态归一化：delivered→成功；canceled/unavailable→取消；其余进行中
    df["status"] = (
        df["order_status"]
        .map({"delivered": "成功", "canceled": "取消", "unavailable": "取消"})
        .fillna("进行中")
    )

    orders_out = df[
        [
            "order_id", "user_id", "order_time", "amount", "category", "brand",
            "product_name", "channel", "pay_method", "status", "region", "review_score",
        ]
    ].copy()

    users_out = (
        customers[["customer_unique_id", "customer_city", "customer_state"]]
        .rename(
            columns={
                "customer_unique_id": "user_id",
                "customer_city": "city",
                "customer_state": "region",
            }
        )
        .drop_duplicates("user_id")
    )

    # Olist 无行为事件，返回空表（漏斗分析走降级分支）
    events_out = pd.DataFrame(columns=["user_id", "event_type", "event_time", "category", "channel"])

    return {"orders": orders_out, "users": users_out, "events": events_out}
