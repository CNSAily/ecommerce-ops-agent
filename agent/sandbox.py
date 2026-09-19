# -*- coding: utf-8 -*-
"""沙箱执行器：在隔离子进程中执行 LLM 生成的 pandas 代码。

设计目标：
1. 隔离性 —— 用户代码跑在独立子进程，崩溃/超时不影响主 Agent；
2. 可观察 —— 捕获 stdout（print 输出）与生成的图表，回传给 ReAct 循环；
3. 确定性 —— 通过 pickle 注入统一的数据上下文（orders DataFrame）。

安全边界说明：这是「轻量沙箱」（子进程 + 超时 + 固定数据上下文），
面向本地个人分析场景，不等同于 Docker/容器级强隔离。
"""

import json
import os
import pickle
import subprocess
import sys
import tempfile

from config import BASE_DIR, SANDBOX_TIMEOUT

RUNNER = BASE_DIR / "scripts" / "_sandbox_runner.py"

_RESULT_MARK = "__RESULT__"


class SandboxResult:
    """沙箱执行结果。"""

    def __init__(self, ok, stdout="", stderr="", figures=None, error=""):
        self.ok = ok
        self.stdout = stdout
        self.stderr = stderr
        self.figures = figures or []
        self.error = error

    def __repr__(self):
        return f"SandboxResult(ok={self.ok}, figures={self.figures}, error={self.error[:80]!r})"


def run_code(code: str, data: dict, figures_dir: str, timeout: int = None) -> SandboxResult:
    """执行一段 pandas 代码。

    参数：
        code        —— LLM 生成的 Python 代码
        data        —— export_for_sandbox() 导出的数据字典（含 orders）
        figures_dir —— 图表输出目录（绝对路径）
        timeout     —— 单次执行超时秒数（默认取 SANDBOX_TIMEOUT）

    返回 SandboxResult。
    """
    timeout = timeout or SANDBOX_TIMEOUT

    # 数据与代码分别落到临时文件，避免命令行传参过长
    fd, data_path = tempfile.mkstemp(suffix=".pkl")
    os.close(fd)
    with open(data_path, "wb") as f:
        pickle.dump(data, f)

    fd, code_path = tempfile.mkstemp(suffix=".py")
    os.close(fd)
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(code)

    try:
        proc = subprocess.run(
            [sys.executable, str(RUNNER), data_path, code_path, figures_dir],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            cwd=str(BASE_DIR),
        )
        return _parse(proc.stdout, proc.stderr)
    except subprocess.TimeoutExpired:
        return SandboxResult(False, "", "", [], f"执行超时（>{timeout}s），已强制终止。")
    except Exception as e:  # noqa: BLE001
        return SandboxResult(False, "", "", [], f"沙箱启动失败：{e}")
    finally:
        for p in (data_path, code_path):
            try:
                os.unlink(p)
            except OSError:
                pass


def _parse(stdout: str, stderr: str) -> SandboxResult:
    """从子进程 stdout 中解析结果标记。"""
    if not stdout:
        return SandboxResult(False, "", stderr, [], "子进程无输出。")
    for line in reversed(stdout.strip().splitlines()):
        line = line.strip()
        if line.startswith(_RESULT_MARK):
            try:
                res = json.loads(line[len(_RESULT_MARK):])
            except json.JSONDecodeError:
                continue
            return SandboxResult(
                ok=bool(res.get("ok")),
                stdout=res.get("stdout", ""),
                stderr=stderr,
                figures=res.get("figures", []),
                error=res.get("error", ""),
            )
    return SandboxResult(False, stdout, stderr, [], "沙箱未返回有效结果标记。")
