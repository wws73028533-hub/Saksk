# -*- coding: utf-8 -*-
"""填空题题干/答案解析

导入期支持：
- 在题干中用 {答案} 标记空
- 例如："题干内容和{答案1}和{答案2}" ->
  - content: "题干内容和__和__"（统一占位符）
  - answer: "答案1;;答案2"（按空位顺序）

答案格式约定：
- 不同空用 ';;' 分隔
- 同一空的多个可接受答案用 ';' 分隔（可选）

示例："{北京;京城}是{中国}的首都" ->
  answer = "北京;京城;;中国"
"""

from __future__ import annotations

import re
from typing import List, Tuple


BLANK_TOKEN = '__'  # 与前端 num_blanks = q.content.count('__') 对齐


def parse_fill_blank(content: str) -> Tuple[str, str, int]:
    """解析填空题：把 {..} 替换为占位符，提取答案

    返回：(new_content, answer, blank_count)
    """
    if not content:
        return content or '', '', 0

    matches: List[str] = re.findall(r'\{(.*?)\}', content)
    if not matches:
        return content, '', 0

    # 答案：按空位顺序，用 ';;' 分隔
    # 允许单个空内用 ';' 表示同义答案（导入时不做额外拆分）
    answer = ';;'.join([m.strip() for m in matches])

    # 题干：每个 {..} 替换成 '__'
    new_content = re.sub(r'\{.*?\}', BLANK_TOKEN, content)
    return new_content, answer, len(matches)

