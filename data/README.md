# 数据字典

本目录 `raw/` 支持两套数据源（Agent 自动探测，优先 Olist）。

## 数据源一：Olist 真实电商数据（默认）

`python scripts/download_olist.py` 从公开 GitHub 镜像下载巴西 Olist 电商数据集
（约 10 万订单、2016-09 ~ 2018-08，来源为 Kaggle 的 Brazilian E-Commerce Public Dataset）。

原始表（8 张 CSV，约 65MB，跳过 geolocation）：

| 文件 | 说明 |
|------|------|
| olist_orders_dataset.csv | 订单主表（状态 / 时间 / 客户） |
| olist_order_items_dataset.csv | 订单明细（商品 / 卖家 / 价格 / 运费） |
| olist_order_payments_dataset.csv | 支付记录 |
| olist_order_reviews_dataset.csv | 评价（评分 1~5） |
| olist_customers_dataset.csv | 客户（城市 / 州） |
| olist_products_dataset.csv | 商品（品类） |
| olist_sellers_dataset.csv | 卖家 |
| product_category_name_translation.csv | 品类葡萄牙语 → 英文翻译 |

这些表在数据层被 join 成统一的分析宽表（orders），字段名与合成数据对齐。

## 数据源二：云启严选合成数据

`python scripts/generate_data.py` 生成完全模拟的电商数据（seed 固定，可复现）：

- users.csv（2 万用户）
- orders.csv（10 万订单）
- events.csv（30 万行为事件，用于漏斗 / 留存）

## 统一分析口径

数据层 `agent/data.py` 把两套数据源统一为同一字段名，Analyzer 不感知差异：

| 统一字段 | Olist 来源 | 合成来源 |
|---------|-----------|---------|
| user_id | customer_unique_id | user_id |
| order_time | order_purchase_timestamp | order_time |
| amount | price + freight_value | amount |
| category | product_category_name_english | category |
| status | delivered→成功 / canceled→取消 / 其余→进行中 | 成功 / 取消 / 退货 |
| channel | payment_type（支付方式兜底） | channel（营销渠道） |
| review_score | review_score | 无（NaN） |

> 有效订单口径：`status == "成功"`（Olist 中即已送达 delivered）。
> 注意：Olist 金额单位为巴西雷亚尔（R$），报告展示时自动切换货币符号。
