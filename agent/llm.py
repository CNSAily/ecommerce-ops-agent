# -*- coding: utf-8 -*-
"""LLM 客户端（可选）。

采用 OpenAI 兼容协议，任意 base_url 均可（DeepSeek / 豆包 / 通义 / OpenAI ...）。
未配置 key 时，Agent 自动降级为内置规则引擎，功能不受影响。
"""

import config


class LLMClient:
    def __init__(self):
        cfg = config.llm_config()
        self.base_url = cfg["base_url"]
        self.api_key = cfg["api_key"]
        self.model = cfg["model"]
        self._client = None

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.api_key)

    def _ensure_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        return self._client

    def chat(self, system: str, user: str, max_tokens: int = 800) -> str:
        """调用 LLM，失败时返回空字符串（调用方自行降级）。"""
        if not self.enabled:
            return ""
        try:
            client = self._ensure_client()
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            return ""
