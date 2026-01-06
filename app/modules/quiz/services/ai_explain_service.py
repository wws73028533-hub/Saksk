# -*- coding: utf-8 -*-
import re
from typing import Any, Dict, List, Optional

from .dashscope_client import DashScopeClient


def _strip_html(text: str) -> str:
    if not text:
        return ""
    s = str(text)
    s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _build_user_prompt(payload: Dict[str, Any]) -> str:
    content = _strip_html(payload.get("content") or "")
    q_type = (payload.get("q_type") or "").strip()
    options = payload.get("options")
    answer = (payload.get("answer") or "").strip()

    lines: List[str] = []
    if q_type:
        lines.append(f"题型：{q_type}")
    if content:
        lines.append("题目：")
        lines.append(content)
    if isinstance(options, list) and options:
        lines.append("")
        lines.append("选项：")
        for opt in options[:10]:
            if isinstance(opt, dict):
                k = str(opt.get("key") or "").strip()
                v = _strip_html(str(opt.get("value") or "").strip())
                if k:
                    lines.append(f"{k}. {v}")
                else:
                    lines.append(v)
            else:
                lines.append(_strip_html(str(opt)))
    if answer:
        lines.append("")
        lines.append(f"参考答案：{answer}")

    lines.append("")
    lines.append("请给出中文解析，要求：")
    lines.append("1) 先用1-2句话概括考点；")
    lines.append("2) 给出正确答案/结论；")
    lines.append("3) 分步骤或逐项说明为什么；")
    lines.append("4) 给出1-2个易错点提醒；")
    lines.append("输出尽量精炼，不要赘述。")

    return "\n".join([x for x in lines if x is not None])


def generate_ai_explain(
    *,
    api_key: str,
    base_url: str,
    model: str,
    payload: Dict[str, Any],
    timeout: int = 25,
) -> str:
    client = DashScopeClient(api_key=api_key, base_url=base_url)

    system_prompt = (
        "你是一名专业的考试题解析老师。"
        "请用清晰的中文分点输出解析，保持简洁、准确、可操作。"
    )
    user_prompt = _build_user_prompt(payload)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    return client.chat_completions(
        model=model,
        messages=messages,
        temperature=0.2,
        top_p=0.8,
        max_tokens=900,
        timeout=timeout,
    )

