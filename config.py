# -*- coding: utf-8 -*-
"""全局配置：路径、数据加载、LLM 配置。"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORT_DIR = BASE_DIR / "reports"

# 沙箱执行配置（LLM 生成代码的安全隔离执行）
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "30"))          # 单次执行超时（秒）
SANDBOX_MAX_ROUNDS = int(os.getenv("SANDBOX_MAX_ROUNDS", "8"))     # ReAct 最大迭代轮数


def load_env():
    """尽力加载 .env（不存在或未装 dotenv 时静默跳过）。"""
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE_DIR / ".env")
    except Exception:
        pass


def llm_config() -> dict:
    """读取 LLM 配置；未配置时返回 None 值，Agent 走规则引擎降级。"""
    load_env()
    return {
        "base_url": os.getenv("LLM_BASE_URL"),
        "api_key": os.getenv("LLM_API_KEY"),
        "model": os.getenv("LLM_MODEL", "deepseek-chat"),
    }


def llm_enabled() -> bool:
    cfg = llm_config()
    return bool(cfg["base_url"] and cfg["api_key"])
