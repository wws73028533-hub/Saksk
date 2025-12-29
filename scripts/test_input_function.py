# -*- coding: utf-8 -*-
"""测试 input() 函数是否可用"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.code_executor import PythonExecutor

executor = PythonExecutor()
result = executor.execute('a = int(input())\nprint(a * 2)', '5')
print(f'Status: {result["status"]}')
print(f'Output: {result.get("output", "")}')
print(f'Error: {result.get("error")}')

















