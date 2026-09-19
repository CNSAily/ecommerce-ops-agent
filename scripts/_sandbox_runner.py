#!/usr/bin/env python3
"""沙箱子进程：加载数据 → exec 用户代码 → 输出结构化结果。

由 agent/sandbox.py 的 run_code() 通过 subprocess 调用：
    python _sandbox_runner.py <data.pkl> <code.py> <figures_dir>

约定：
- 用户代码中可用变量：df / orders（订单 DataFrame）、pd、np、source、
  FIGURES_DIR（图表输出目录）、save_fig(fig, name)（保存图并返回文件名）。
- 用户代码用 print() 输出的内容会被捕获，作为「观察结果」回传给 ReAct 循环。
- 结果通过 stdout 最后一行的 __RESULT__{json} 标记返回给主进程。
"""

import contextlib
import io
import json
import os
import sys
import traceback

import matplotlib

matplotlib.use("Agg")  # 无 GUI 后端

import matplotlib.pyplot as plt
from matplotlib import font_manager

# 中文字体（子进程的 rcParams 独立于主进程，必须自行配置，否则中文渲染为方块；
# 字体候选与 agent/viz.py 保持一致）
_CN_FONTS = [
    "Microsoft YaHei", "SimHei", "PingFang SC",
    "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Zen Hei",
]
_installed = {f.name for f in font_manager.fontManager.ttflist}
for _name in _CN_FONTS:
    if _name in _installed:
        plt.rcParams["font.sans-serif"] = [_name]
        break
plt.rcParams["axes.unicode_minus"] = False

# 注入标签美化函数（品类中文映射 / hash 截断），供 LLM 生成的代码调用
try:
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _ROOT not in sys.path:
        sys.path.insert(0, _ROOT)
    from agent.viz import pretty_label as _pretty_label
except Exception:  # noqa: BLE001
    _pretty_label = None

import numpy as np
import pandas as pd

_RESULT_MARK = "__RESULT__"


def main():
    data_path, code_path, figures_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(figures_dir, exist_ok=True)

    # 记录执行前已存在的图，只返回本次新生成的
    pre_existing = set(os.listdir(figures_dir))

    with open(data_path, "rb") as f:
        data = __import__("pickle").load(f)

    orders = data.get("orders")
    source = data.get("source", "synthetic")

    def save_fig(fig, name):
        path = os.path.join(figures_dir, name)
        fig.savefig(path, dpi=110, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return name

    ns = {
        "pd": pd,
        "np": np,
        "df": orders,
        "orders": orders,
        "source": source,
        "FIGURES_DIR": figures_dir,
        "save_fig": save_fig,
        "pretty": _pretty_label or (lambda x: str(x)),
    }

    code = ""
    with open(code_path, encoding="utf-8") as f:
        code = f.read()

    stdout_buf = io.StringIO()
    ok = True
    error = ""
    try:
        with contextlib.redirect_stdout(stdout_buf):
            exec(compile(code, "<agent_code>", "exec"), ns)
    except Exception:  # noqa: BLE001
        ok = False
        error = traceback.format_exc()

    figures = sorted(
        fn for fn in os.listdir(figures_dir)
        if fn not in pre_existing and fn.lower().endswith((".png", ".svg", ".jpg"))
    )

    result = {
        "ok": ok,
        "stdout": stdout_buf.getvalue(),
        "error": error,
        "figures": figures,
    }
    sys.stdout.write(_RESULT_MARK + json.dumps(result, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
