# -*- coding: utf-8 -*-
import json
from typing import Any, Dict, List, Optional

import requests


class DashScopeClient:
    """DashScope OpenAI-compatible client (chat.completions)."""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "").rstrip("/")

    def chat_completions(
        self,
        *,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        top_p: float = 0.8,
        max_tokens: int = 800,
        timeout: int = 25,
    ) -> str:
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY 未配置")
        if not self.base_url:
            raise ValueError("DASHSCOPE_BASE_URL 未配置")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": float(temperature),
            "top_p": float(top_p),
            "max_tokens": int(max_tokens),
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if resp.status_code < 200 or resp.status_code >= 300:
            # 尽量提取错误信息（不要泄露密钥）
            msg = ""
            try:
                js = resp.json()
                msg = js.get("error", {}).get("message") or js.get("message") or ""
            except Exception:
                msg = resp.text[:300] if resp.text else ""
            raise RuntimeError(f"DashScope 调用失败：HTTP {resp.status_code} {msg}".strip())

        try:
            data = resp.json()
        except json.JSONDecodeError:
            raise RuntimeError("DashScope 返回非 JSON 响应")

        try:
            choices = data.get("choices") or []
            msg = (choices[0] or {}).get("message") or {}
            content = (msg.get("content") or "").strip()
        except Exception:
            content = ""

        if not content:
            raise RuntimeError("DashScope 未返回有效内容")
        return content

