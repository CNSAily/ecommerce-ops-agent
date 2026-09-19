# ecommerce-ops-agent · 电商运营数据分析 Agent

> 用自然语言提问，Agent 自动完成「意图识别 → 数据分析 → 图表 → 洞察报告」，输出可分享的 HTML 报告。
> 内置 **11 大分析模块** + **双轨 Agent 架构**，支持 **真实数据（Olist）** 与 **可复现合成数据**。

![Python](https://img.shields.io/badge/Python-3.9+-blue) ![License](https://img.shields.io/badge/License-MIT-green) ![Status](https://img.shields.io/badge/Status-Active-brightgreen)

---

## ✨ 项目亮点

- **双轨 Agent 架构**（核心）
  - **工具轨**：11 大内置分析模块，意图识别 → 直接调用，快 / 稳 / **无需 API Key**；
  - **ReAct 轨**：LLM 自主生成 pandas 代码 → **沙箱隔离执行** → 观察结果 → 多轮迭代，是真 Agent 而非「写死的报表工具」。
- **沙箱执行**：LLM 生成的代码在隔离子进程运行（超时保护 + 固定数据上下文），崩溃不影响主程序。
- **双数据源**：巴西 Olist 真实电商数据（约 10 万订单）与云启严选合成数据（seed 固定、可复现），数据层自动适配。
- **深度分析**：除 RFM / 留存 / 漏斗外，新增 **CLV 预测（BG/NBD + Gamma-Gamma）**、**统计检验（t 检验 / ANOVA / 相关）**、**异常检测**、**销售预测**。
- **LLM 可选**：不配 API Key 也能完整跑（工具轨）；配置后自动升级为 ReAct 自主分析（兼容 DeepSeek / 豆包 / 通义 / OpenAI）。

## 🚀 快速开始

```bash
# 1. 克隆
git clone https://github.com/<your-name>/ecommerce-ops-agent.git
cd ecommerce-ops-agent

# 2. 安装依赖
python -m venv .venv
# Windows: .venv\Scripts\activate   |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# 3. 准备数据（二选一）
#    A. Olist 真实数据（推荐，约 65MB，从公开镜像下载）
python scripts/download_olist.py
#    B. 合成数据（无网络 / 快速体验，seed 固定可复现）
python scripts/generate_data.py

# 4. 开始提问
python main.py "帮我整体分析一下公司的经营情况"
```

运行后在 `reports/` 生成自包含 HTML 报告（图表 base64 内嵌）。

## 💬 使用示例

| 主题 | 你可以这样问 |
|------|-------------|
| 综合概览 | 帮我整体分析一下公司的经营情况 |
| 销售趋势 | 近一年各月 GMV 和客单价趋势如何 |
| 品类品牌 | 哪个品类卖得最好 |
| 用户分层 | 帮我做一下用户 RFM 分层，找高价值用户 |
| 客户价值 | 帮我预测客户终身价值 CLV |
| 复购留存 | 用户的复购率和留存情况怎么样 |
| 转化漏斗 | 从浏览到支付的转化漏斗如何 |
| 渠道分析 | 各渠道的 GMV、转化率和退货率怎么样 |
| 销售预测 | 预测未来三个月 GMV |
| 异常检测 | 检测 GMV 的异常波动 |
| 统计检验 | 做一下统计检验，看哪些差异显著 |

其他命令：

```bash
python main.py --demo        # 一次性生成覆盖 11 大模块的全景演示报告
python main.py --list        # 列出支持主题
python main.py               # 进入交互式对话
python main.py "为什么直播退货率高" --agent   # 强制 ReAct 自主分析（需 LLM key）
```

## 🤖 Agent 工作原理（双轨）

```
自然语言问题
      │
      ▼
┌─────────────┐   开放式/探索性问题 + 有 LLM key
│  意图识别    │──────────────────────────────┐
└─────────────┘                               │
      │ 标准问题                               ▼
      ▼                              ┌──────────────────┐
┌─────────────┐                      │  ReAct 轨（真 Agent）│
│  工具轨      │                      │  LLM 生成代码        │
│  11 大模块   │                      │  → 沙箱执行          │
│  (可离线)    │                      │  → 观察结果          │
└─────────────┘                      │  → 多轮迭代          │
      │                               └──────────────────┘
      └──────────────┬────────────────────┘
                     ▼
          ┌─────────────────┐
          │ 可视化 + HTML 报告 │
          └─────────────────┘
```

- **工具轨**：`agent/intent.py` 意图识别 → 调用 `agent/analyzers/` 下对应 Analyzer（接口统一、可插拔）。
- **ReAct 轨**：`agent/react.py` 驱动 `agent/sandbox.py` 在子进程执行 LLM 生成的代码，`stdout` 回传、多轮迭代直到 `FINAL:` 结论。

## 🔑 LLM 配置（可选）

复制 `.env.example` 为 `.env`，填入任意 OpenAI 兼容接口：

```bash
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=sk-your-key-here
LLM_MODEL=deepseek-chat
```

> 不配置也能完整运行（工具轨）；配置后开放式问题自动走 ReAct 自主分析。

## 📁 项目结构

```
ecommerce-ops-agent/
├── main.py                    # CLI 入口（单题 / 交互 / demo / --agent）
├── config.py                  # 路径 & LLM & 沙箱配置
├── requirements.txt
├── .env.example
├── agent/
│   ├── orchestrator.py        # 双轨编排：工具轨 + ReAct 轨
│   ├── intent.py              # 意图识别（LLM + 规则）
│   ├── llm.py                 # LLM 客户端（OpenAI 兼容）
│   ├── react.py               # ReAct 循环（代码生成 → 执行 → 迭代）
│   ├── sandbox.py             # 沙箱执行器（子进程隔离）
│   ├── tools.py               # 工具注册
│   ├── viz.py                 # 可视化（中文字体适配）
│   ├── report.py              # HTML 报告生成
│   ├── data.py                # 数据中枢 DataHub（Olist / 合成统一）
│   └── analyzers/             # 11 个分析模块
│       ├── overview.py        #   经营概览
│       ├── gmv.py             #   GMV 趋势
│       ├── product.py         #   品类品牌
│       ├── customer.py        #   RFM 用户分层
│       ├── retention.py       #   复购留存
│       ├── funnel.py          #   转化漏斗（数据源感知）
│       ├── channel.py         #   渠道分析（数据源感知）
│       ├── clv.py             #   CLV 预测（BG/NBD + Gamma-Gamma）
│       ├── forecast.py        #   销售预测（趋势 + 季节分解）
│       ├── anomaly.py         #   异常检测（z-score）
│       └── stats.py           #   统计检验（t / ANOVA / 相关）
├── scripts/
│   ├── download_olist.py      # Olist 真实数据下载（raw + blob API 双通道）
│   ├── generate_data.py       # 合成数据生成器（seed 固定）
│   └── _sandbox_runner.py     # 沙箱子进程脚本
├── data/
│   ├── raw/                   # 数据 CSV（不入库）
│   └── README.md              # 数据字典
├── examples/
│   └── demo_report.html       # 全景演示报告（--demo 生成后复制）
└── docs/
    └── images/                # 图表 SVG（README 展示用）
```

## 📊 数据说明

支持两套数据源，数据层统一字段名、自动适配：

- **Olist 真实数据**：巴西电商公开数据集（约 10 万订单、9.3 万客户、73 品类），由 `download_olist.py` 从公开镜像下载。真实数据带来真实洞察——例如复购率仅 2.2%、Top 10% 客户贡献 66.8% CLV、复购客单价反而更低（p<0.001）。
- **云启严选合成数据**：Faker 生成的模拟数据（seed 固定可复现），刻意埋入业务故事（大促脉冲、渠道分化、二八分布），支持完整的「浏览→加购→下单→支付」行为漏斗（Olist 无行为数据）。

详见 [data/README.md](data/README.md)。

## 🛠 技术栈

Python · Pandas · NumPy · Matplotlib · SciPy · Lifetimes · OpenAI SDK（可选）

## 📄 License

[MIT](LICENSE)
