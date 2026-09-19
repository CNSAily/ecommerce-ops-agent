#!/usr/bin/env python3
"""下载 Olist 巴西电商公开数据集到 data/raw/。

数据源：GitHub 公开镜像 mohamedyounis10/Olist-brazilian-ecommerce-analytics
（原数据集为 Kaggle 的 Brazilian E-Commerce Public Dataset by Olist，约 10 万订单、
2016-09 至 2018-08，覆盖订单/商品/客户/卖家/支付/评论等 8 张表）。

支持两种下载通道，自动降级：
  1. raw.githubusercontent.com 直连 —— 本地网络首选，速度快；
  2. GitHub git blob API —— 受限网络环境的兜底（走 api.github.com）。

用法：
    python scripts/download_olist.py
"""

import base64
import json
import os
import sys
import urllib.request

REPO_OWNER = "mohamedyounis10"
REPO_NAME = "Olist-brazilian-ecommerce-analytics"
BRANCH = "main"

# 核心分析表（跳过 geolocation：61MB 且对运营分析价值有限）
FILES = [
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]

HEADERS = {"User-Agent": "Mozilla/5.0"}

# 脚本位于 scripts/ 下，数据目录取项目根的 data/raw/
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw"
)


def fetch(url, timeout=240):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def download_via_raw(filename):
    url = (
        f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}"
        f"/{BRANCH}/Datasets/{filename}"
    )
    return fetch(url)


def download_via_blob(filename, sha):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/git/blobs/{sha}"
    payload = json.loads(fetch(url))
    return base64.b64decode(payload["content"])


def get_shas():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/Datasets"
    entries = json.loads(fetch(url))
    return {e["name"]: e["sha"] for e in entries}


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    shas = {}
    for name in FILES:
        dest = os.path.join(DATA_DIR, name)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            print(f"[skip] {name} 已存在")
            continue

        content = None
        try:
            content = download_via_raw(name)
            print(f"[raw ] {name} -> {len(content):,} bytes")
        except Exception as e:  # noqa: BLE001
            print(f"[raw ] {name} 失败({e.__class__.__name__})，改用 blob API ...")

        if content is None:
            if not shas:
                shas = get_shas()
            try:
                content = download_via_blob(name, shas[name])
                print(f"[blob] {name} -> {len(content):,} bytes")
            except Exception as e:  # noqa: BLE001
                print(f"[FAIL] {name}: {e}")
                continue

        with open(dest, "wb") as f:
            f.write(content)
        print(f"[ok  ] {name}")

    print("完成。数据目录：", DATA_DIR)


if __name__ == "__main__":
    main()
