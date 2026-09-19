# -*- coding: utf-8 -*-
"""ReAct 循环：LLM 生成代码 → 沙箱执行 → 观察结果 → 多轮自我迭代。

这是「真 Agent」的核心 —— Agent 不是调用写死的分析函数，而是像分析师一样
自主编写 pandas 代码探索数据、绘图、得出结论，中间可多轮迭代修正。

协议：
- 每轮 LLM 输出一段 Python 代码（```python 代码块内），沙箱执行后把
  stdout（print 输出）作为「观察」回传给 LLM；
- LLM 认为分析完成时输出 `FINAL: <中文结论>` 结束循环；
- 达到最大轮数仍未结束，则根据探索过程强制总结。
"""

import re

from config import SANDBOX_MAX_ROUNDS, SANDBOX_TIMEOUT

from .llm import LLMClient
from .sandbox import run_code

SYSTEM_PROMPT = """你是电商数据分析 Agent，通过编写并执行 Python/pandas 代码完成数据分析任务。

【数据上下文】执行环境命名空间中已有以下对象：
- df（别名 orders）：订单事实表 DataFrame，列包括：
  order_id(订单ID) · user_id(唯一用户ID) · order_time(下单时间 datetime) ·
  amount(订单金额,元) · category(品类) · brand(卖家/品牌) · product_name(商品ID) ·
  channel(渠道) · pay_method(支付方式) · status(订单状态:成功/取消/进行中) ·
  region(地域) · review_score(评分1-5,可能为空)
- source：数据源标识（"olist" 或 "synthetic"）
- FIGURES_DIR：图表保存目录；调用 save_fig(fig, "英文名.png") 保存图并返回文件名
- pretty(x)：标签美化函数——英文品类名转中文短名（如 health_beauty→健康美容）、
  32位哈希ID截断；绘图时请用 pretty() 处理轴标签，避免长英文标签拥挤重叠

【硬性规则】
1. 每次只输出一段可执行 Python 代码（放在 ```python 代码块内），用 print() 输出关键数字与发现。
2. 需要图表时，用 matplotlib 绘图后调用 save_fig(fig, "英文名.png")。
3. 只有 status=="成功" 的订单才计入 GMV、客单价等经营指标。
4. 图表标题用中文（已适配中文字体）；轴标签用 pretty() 转换品类/品牌等长英文名，
   排名类图只画 Top 10~15，避免标签拥挤。
5. 分析充分后，输出一行以 `FINAL: ` 开头的最终结论（中文，含关键数字、业务洞察与建议）。

建议先观察数据（df.head()、df.info()、df.describe()），再逐步深入。"""


class ReactLoop:
    """ReAct 自主分析循环。"""

    def __init__(self, llm: LLMClient = None, timeout: int = None, max_rounds: int = None):
        self.llm = llm or LLMClient()
        self.timeout = timeout or SANDBOX_TIMEOUT
        self.max_rounds = max_rounds or SANDBOX_MAX_ROUNDS

    def run(self, question: str, data: dict, figures_dir: str) -> dict:
        """执行自主分析，返回 {"final","history","figures"}。"""
        history = []
        figures = []
        final = None

        for i in range(1, self.max_rounds + 1):
            user = self._build_prompt(question, history, i)
            resp = self.llm.chat(SYSTEM_PROMPT, user, max_tokens=1500)
            if not resp:
                break

            if resp.startswith("FINAL:"):
                final = resp[len("FINAL:"):].strip()
                break

            code = _extract_code(resp)
            if not code:
                history.append({"role": "assistant", "content": resp})
                history.append({"role": "observation", "content": "[无法解析为代码，请重新输出代码块]"})
                continue

            result = run_code(code, data, figures_dir, self.timeout)
            obs = result.stdout if result.ok else (result.error or "执行失败")
            for f in result.figures:
                if f not in figures:
                    figures.append(f)
            history.append({"role": "code", "content": code})
            history.append({"role": "observation", "content": obs[:3000]})

        if final is None:
            final = self._summarize(question, history)
        return {"final": final, "history": history, "figures": figures}

    def _build_prompt(self, question, history, round_i):
        parts = [f"用户问题：{question}", ""]
        if history:
            parts.append("—— 已执行的探索过程 ——")
            for h in history:
                if h["role"] == "code":
                    parts.append(f"[代码]\n{h['content']}")
                elif h["role"] == "observation":
                    parts.append(f"[输出]\n{h['content']}")
                else:
                    parts.append(h["content"])
            parts.append("")
        parts.append(
            f"【第 {round_i} 轮】请继续：需要进一步计算或绘图则输出代码块；"
            "已得出结论则输出 `FINAL: 结论`。"
        )
        return "\n".join(parts)

    def _summarize(self, question, history):
        obs = "\n".join(h["content"] for h in history if h["role"] == "observation")
        system = "你是数据分析总结助手。根据下面的探索输出，为问题写一段中文结论（含关键数字与建议）。"
        resp = self.llm.chat(system, f"问题：{question}\n\n探索输出：\n{obs[:4000]}", max_tokens=600)
        return resp or "（LLM 未返回结论，请查看执行过程。）"


def _extract_code(resp: str) -> str:
    m = re.search(r"```(?:python)?\s*\n(.*?)```", resp, re.S)
    if m:
        return m.group(1).strip()
    if any(k in resp for k in ("import ", "print(", "df", "=", "plt.")):
        return resp.strip()
    return ""
