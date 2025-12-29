# -*- coding: utf-8 -*-
"""
输出格式化工具
"""
from typing import Optional


def format_output(output: str) -> str:
    """
    格式化输出（去除首尾空白和换行符）
    
    Args:
        output: 原始输出
    
    Returns:
        格式化后的输出
    """
    if output is None:
        return ""
    return output.strip().rstrip('\n\r')


def compare_output(actual: str, expected: str, strict: bool = False) -> bool:
    """
    比较实际输出与期望输出
    
    Args:
        actual: 实际输出
        expected: 期望输出
        strict: 是否严格模式（逐行比较）
    
    Returns:
        是否匹配
    """
    actual = format_output(actual)
    expected = format_output(expected)
    
    if strict:
        # 严格模式：逐行比较
        actual_lines = actual.split('\n')
        expected_lines = expected.split('\n')
        if len(actual_lines) != len(expected_lines):
            return False
        return all(
            format_output(a) == format_output(e)
            for a, e in zip(actual_lines, expected_lines)
        )
    else:
        # 非严格模式：整体比较（去除首尾空白）
        return actual == expected

