# -*- coding: utf-8 -*-
"""
代码安全验证器
用于检查用户提交的代码是否包含危险操作
"""
import ast
import re
from typing import Tuple


# 禁止的 Python 模块和函数
FORBIDDEN_MODULES = {
    'os', 'sys', 'subprocess', 'socket', 'urllib', 'requests',
    'open', 'file', 'input', 'eval', 'exec', 'compile',
    'importlib', 'imp', 'pkgutil', '__import__', 'ctypes',
    'multiprocessing', 'threading', 'pickle', 'marshal'
}

FORBIDDEN_FUNCTIONS = {
    'open', 'file', 'eval', 'exec', 'compile',
    '__import__', 'execfile', 'reload', 'exit', 'quit',
    'raw_input', 'help', 'license', 'credits'
    # 注意：input() 函数允许使用，因为输入通过 subprocess.communicate() 传递
}


def validate_python_code(code: str) -> Tuple[bool, str]:
    """
    验证 Python 代码安全性
    
    Args:
        code: Python 代码字符串
    
    Returns:
        (is_valid, error_message) - 如果 is_valid 为 False，error_message 包含错误原因
    """
    # 1. 检查代码长度
    if len(code) > 50000:  # 50KB
        return False, '代码长度不能超过 50000 字符'
    
    if not code.strip():
        return False, '代码不能为空'
    
    # 2. 检查禁止的函数调用（简单字符串匹配）
    # 注意：input() 函数允许使用，因为输入通过 subprocess.communicate() 传递
    for func in FORBIDDEN_FUNCTIONS:
        pattern = r'\b' + re.escape(func) + r'\s*\('
        if re.search(pattern, code):
            return False, f'禁止使用函数: {func}'
    
    # 3. 使用 AST 解析代码
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f'语法错误: {str(e)}'
    except Exception as e:
        return False, f'代码解析失败: {str(e)}'
    
    # 4. 检查 AST 节点
    for node in ast.walk(tree):
        # 检查导入语句
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split('.')[0]
                if module_name in FORBIDDEN_MODULES:
                    return False, f'禁止导入模块: {module_name}'
        
        # 检查 from ... import
        if isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module.split('.')[0]
                if module_name in FORBIDDEN_MODULES:
                    return False, f'禁止导入模块: {module_name}'
        
        # 检查函数调用
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in FORBIDDEN_FUNCTIONS:
                    return False, f'禁止调用函数: {node.func.id}'
            # 检查属性调用，如 os.system
            elif isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id in FORBIDDEN_MODULES:
                        return False, f'禁止使用模块: {node.func.value.id}'
    
    return True, ''


def validate_code_length(code: str, max_length: int = 50000) -> Tuple[bool, str]:
    """
    验证代码长度
    
    Args:
        code: 代码字符串
        max_length: 最大长度（字符数）
    
    Returns:
        (is_valid, error_message)
    """
    if len(code) > max_length:
        return False, f'代码长度不能超过 {max_length} 字符'
    return True, ''

