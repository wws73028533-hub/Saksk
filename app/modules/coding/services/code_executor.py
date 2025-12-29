# -*- coding: utf-8 -*-
"""
代码执行服务
提供安全的代码执行功能
"""
import subprocess
import tempfile
import os
import time
import sys
from typing import Dict, Any, Optional
from app.core.utils.code_validator import validate_python_code


class CodeExecutor:
    """代码执行器基类"""
    
    def __init__(self, time_limit: int = 5, output_limit: int = 10000):
        """
        初始化代码执行器
        
        Args:
            time_limit: 时间限制（秒）
            output_limit: 输出长度限制（字符数）
        """
        self.time_limit = time_limit
        self.output_limit = output_limit
    
    def execute(
        self, 
        code: str, 
        language: str = 'python',
        input_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行代码
        
        Args:
            code: 代码字符串
            language: 编程语言（目前仅支持python）
            input_data: 输入数据（可选）
        
        Returns:
            {
                'status': 'success' | 'error' | 'timeout',
                'output': str,
                'error': Optional[str],
                'execution_time': float
            }
        """
        raise NotImplementedError
    
    def _truncate_output(self, output: str) -> str:
        """
        截断输出，防止过长输出
        
        Args:
            output: 原始输出
        
        Returns:
            截断后的输出
        """
        if len(output) > self.output_limit:
            return output[:self.output_limit] + '\n... (输出过长，已截断)'
        return output


class PythonExecutor(CodeExecutor):
    """Python 代码执行器（使用 subprocess，开发环境）"""
    
    def execute(
        self, 
        code: str, 
        language: str = 'python',
        input_data: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行 Python 代码
        
        Args:
            code: Python 代码
            language: 编程语言（目前仅支持python）
            input_data: 输入数据（可选）
        
        Returns:
            {
                'status': 'success' | 'error' | 'timeout',
                'output': str,
                'error': Optional[str],
                'execution_time': float
            }
        """
        if language != 'python':
            return {
                'status': 'error',
                'output': '',
                'error': f'不支持的编程语言: {language}',
                'execution_time': 0
            }
        
        # 1. 代码验证
        is_valid, error_msg = validate_python_code(code)
        if not is_valid:
            return {
                'status': 'error',
                'output': '',
                'error': error_msg,
                'execution_time': 0
            }
        
        # 2. 创建临时文件
        code_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.py', 
                delete=False, 
                encoding='utf-8'
            ) as f:
                f.write(code)
                code_file = f.name
            
            # 3. 执行代码
            start_time = time.time()
            
            # 确定Python命令（Windows使用python，Linux/Mac使用python3）
            python_cmd = 'python3' if sys.platform != 'win32' else 'python'
            
            # 使用 subprocess 执行（注意：生产环境应使用 Docker）
            process = subprocess.Popen(
                [python_cmd, code_file],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            try:
                input_str = input_data if input_data is not None else ''
                stdout, stderr = process.communicate(input=input_str, timeout=self.time_limit)
                execution_time = time.time() - start_time
                
                # 截断输出
                stdout = self._truncate_output(stdout)
                stderr = self._truncate_output(stderr) if stderr else None
                
                if process.returncode == 0:
                    return {
                        'status': 'success',
                        'output': stdout,
                        'error': None,
                        'execution_time': round(execution_time, 3)
                    }
                else:
                    return {
                        'status': 'error',
                        'output': stdout,
                        'error': stderr,
                        'execution_time': round(execution_time, 3)
                    }
            
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                return {
                    'status': 'timeout',
                    'output': '',
                    'error': f'代码执行超时（超过 {self.time_limit} 秒）',
                    'execution_time': self.time_limit
                }
        
        except Exception as e:
            return {
                'status': 'error',
                'output': '',
                'error': f'执行失败: {str(e)}',
                'execution_time': 0
            }
        
        finally:
            # 清理临时文件
            if code_file and os.path.exists(code_file):
                try:
                    os.unlink(code_file)
                except Exception:
                    pass


