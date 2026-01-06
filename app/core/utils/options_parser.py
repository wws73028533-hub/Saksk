# -*- coding: utf-8 -*-
"""统一的题目选项解析工具

背景：题库 options 字段历史上存在多种格式：
- ["A、内容", "B、内容" ...]
- ["A.内容", "B.内容" ...]
- ["内容1", "内容2" ...]（无 A/B 前缀）
- [0.4, 0.45, ...]（数字）
- [{"key": "A", "value": "内容"}, ...]（已结构化）

本模块提供统一解析函数，供 quiz 页面与 chat 题目卡片复用，避免兼容性分裂。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


def parse_options(raw_options: Any) -> List[Dict[str, str]]:
    """解析题目选项为统一结构：[{key, value}, ...]

    raw_options:
      - None / ''
      - JSON 字符串（DB 中常见）
      - list（部分调用方已 json.loads）

    解析策略：
      1) 若为 dict 结构，读 key/value
      2) 若为 str：优先解析 A、 / A. 前缀；否则作为纯文本，后续补 A/B/C...
      3) 其它类型（数字等）转 str
      4) 若所有 key 为空，按顺序补 A/B/C...
    """

    if raw_options is None:
        return []

    opt_list = None

    # 允许传入 JSON 字符串
    if isinstance(raw_options, str):
        s = raw_options.strip()
        if not s:
            return []
        try:
            opt_list = json.loads(s)
        except Exception:
            # 非 JSON：当作单个选项文本（极少见）
            opt_list = [s]
    else:
        opt_list = raw_options

    if not isinstance(opt_list, list):
        return []

    options_payload: List[Dict[str, str]] = []
    for item in opt_list:
        if isinstance(item, dict):
            # 保留 value 中的换行符，只去掉首尾空白（空格、制表符），但保留换行符
            value = str(item.get('value') or '')
            # 去掉首尾的空白字符（空格、制表符），但保留换行符
            value = value.rstrip(' \t').lstrip(' \t') if value else ''
            options_payload.append({
                'key': str(item.get('key') or '').strip(),
                'value': value,
            })
            continue

        # 其它类型统一转字符串
        item_str = '' if item is None else str(item)
        s = item_str.strip()
        if not s:
            options_payload.append({'key': '', 'value': ''})
            continue

        # 优先解析 "A、xxx" / "A.xxx"
        delimiter = '、' if '、' in s else ('.' if '.' in s else None)
        if delimiter:
            parts = s.split(delimiter, 1)
            # parts[0] 一般为 A/B/C/D 或 1/2 等
            if len(parts) == 2 and parts[0].strip() and len(parts[0].strip()) <= 3:
                options_payload.append({'key': parts[0].strip()[:1].upper(), 'value': parts[1].strip()})
                continue

        # 兜底：如果首字符像 A/B/C/D，尝试把它当 key
        first = s[:1].upper()
        if first and first in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            options_payload.append({
                'key': first,
                'value': s[1:].lstrip(' :：.,、\t\r\n').strip(),
            })
        else:
            options_payload.append({'key': '', 'value': s})

    # 如果 key 全为空，则补 A/B/C...
    if options_payload and all((not (x.get('key') or '').strip()) for x in options_payload):
        seed = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        for i, x in enumerate(options_payload):
            x['key'] = seed[i] if i < len(seed) else str(i + 1)

    return options_payload

