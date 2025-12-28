# -*- coding: utf-8 -*-
"""
代码执行服务
提供安全的代码执行功能
"""
import subprocess
import tempfile
import os
import time
from typing import Dict, Any, Optional
from app.core.utils.code_validator import validate_python_code


class CodeExecutor:
    """代码执行器基类"""
    
    def __init__(self, time_limit: int = 5, memory_limit: int = 128):
        """
        初始化代码执行器
        
        Args:
            time_limit: 时间限制（秒）
            memory_limit: 内存限制（MB，当前版本仅记录，不强制限制）
        """
        self.time_limit = time_limit
        self.memory_limit = memory_limit
    
    def execute(self, code: str, input_data: str = '') -> Dict[str, Any]:
        """
        执行代码
        
        Args:
            code: 代码字符串
            input_data: 输入数据（可选）
        
        Returns:
            {
                'output': str,
                'error': str or None,
                'execution_time': float,
                'status': 'success' or 'error' or 'timeout'
            }
        """
        raise NotImplementedError


class PythonExecutor(CodeExecutor):
    """Python 代码执行器（使用 subprocess，开发环境）"""
    
    def execute(self, code: str, input_data: str = '') -> Dict[str, Any]:
        """
        执行 Python 代码
        
        Args:
            code: Python 代码
            input_data: 输入数据（可选）
        
        Returns:
            {
                'output': str,
                'error': str or None,
                'execution_time': float,
                'status': 'success' or 'error' or 'timeout'
            }
        """
        # 1. 代码验证
        is_valid, error_msg = validate_python_code(code)
        if not is_valid:
            return {
                'output': '',
                'error': error_msg,
                'execution_time': 0,
                'status': 'error'
            }
        
        # 2. 创建临时文件
        code_file = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(code)
                code_file = f.name
            
            # 3. 执行代码
            start_time = time.time()
            
            # 使用 subprocess 执行（注意：生产环境应使用 Docker）
            process = subprocess.Popen(
                ['python', code_file],  # Windows 使用 'python'，Linux/Mac 可能需要 'python3'
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            try:
                stdout, stderr = process.communicate(input=input_data, timeout=self.time_limit)
                execution_time = time.time() - start_time
                
                if process.returncode == 0:
                    return {
                        'output': stdout,
                        'error': None,
                        'execution_time': round(execution_time, 3),
                        'status': 'success'
                    }
                else:
                    return {
                        'output': stdout,
                        'error': stderr,
                        'execution_time': round(execution_time, 3),
                        'status': 'error'
                    }
            
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                return {
                    'output': '',
                    'error': f'代码执行超时（超过 {self.time_limit} 秒）',
                    'execution_time': self.time_limit,
                    'status': 'timeout'
                }
        
        except Exception as e:
            return {
                'output': '',
                'error': f'执行失败: {str(e)}',
                'execution_time': 0,
                'status': 'error'
            }
        
        finally:
            # 清理临时文件
            if code_file and os.path.exists(code_file):
                try:
                    os.unlink(code_file)
                except Exception:
                    pass


