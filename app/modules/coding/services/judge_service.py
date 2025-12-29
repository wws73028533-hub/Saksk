# -*- coding: utf-8 -*-
"""
判题服务
负责执行代码并验证测试用例
"""
from typing import Dict, Any, List, Optional
import json
from app.modules.coding.services.code_executor import PythonExecutor
from app.modules.coding.models.coding_question import CodingQuestion
from app.modules.coding.utils.formatters import compare_output


class JudgeService:
    """判题服务"""
    
    def __init__(self):
        self.executor = PythonExecutor()
    
    def judge(
        self,
        question_id: int,
        code: str,
        language: str = 'python',
        time_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        判题
        
        Args:
            question_id: 题目ID
            code: 用户代码
            language: 编程语言
            time_limit: 时间限制（秒），如果为None则使用题目的默认值
        
        Returns:
            {
                'status': 'accepted' | 'wrong_answer' | 'time_limit_exceeded' | 
                         'runtime_error' | 'compilation_error',
                'passed_cases': int,
                'total_cases': int,
                'test_results': List[Dict],
                'execution_time': float,
                'error_message': Optional[str]
            }
        """
        # 1. 获取题目信息
        question = CodingQuestion.get_by_id(question_id)
        if not question:
            return {
                'status': 'compilation_error',
                'passed_cases': 0,
                'total_cases': 0,
                'test_results': [],
                'execution_time': 0,
                'error_message': '题目不存在'
            }
        
        # 2. 获取测试用例
        test_cases_data = CodingQuestion.get_test_cases(question_id)
        test_cases = test_cases_data.get('test_cases', [])
        hidden_cases = test_cases_data.get('hidden_cases', [])
        
        # 合并所有测试用例（公开 + 隐藏）
        all_cases = test_cases + hidden_cases
        if not all_cases:
            return {
                'status': 'compilation_error',
                'passed_cases': 0,
                'total_cases': 0,
                'test_results': [],
                'execution_time': 0,
                'error_message': '题目没有测试用例'
            }
        
        # 3. 设置时间限制
        if time_limit is None:
            time_limit = question.get('time_limit', 5)
        self.executor.time_limit = time_limit
        
        # 4. 对每个测试用例执行代码
        test_results: List[Dict[str, Any]] = []
        total_execution_time = 0.0
        passed_count = 0
        
        for idx, case in enumerate(all_cases):
            case_input = case.get('input', '')
            expected_output = case.get('output', '')
            
            # 执行代码
            result = self.executor.execute(
                code=code,
                language=language,
                input_data=case_input
            )
            
            execution_time = result.get('execution_time', 0)
            total_execution_time += execution_time
            
            # 判断执行状态
            if result['status'] == 'timeout':
                test_results.append({
                    'case_id': idx + 1,
                    'status': 'failed',
                    'input': case_input,
                    'expected_output': expected_output,
                    'actual_output': '',
                    'execution_time': execution_time,
                    'error': '执行超时'
                })
                # 如果超时，直接返回
                return {
                    'status': 'time_limit_exceeded',
                    'passed_cases': passed_count,
                    'total_cases': len(all_cases),
                    'test_results': test_results,
                    'execution_time': total_execution_time,
                    'error_message': f'测试用例 {idx + 1} 执行超时'
                }
            
            if result['status'] == 'error':
                error_msg = result.get('error', '执行错误')
                test_results.append({
                    'case_id': idx + 1,
                    'status': 'failed',
                    'input': case_input,
                    'expected_output': expected_output,
                    'actual_output': result.get('output', ''),
                    'execution_time': execution_time,
                    'error': error_msg
                })
                # 如果是第一个测试用例就出错，可能是编译错误
                if idx == 0:
                    return {
                        'status': 'runtime_error',
                        'passed_cases': 0,
                        'total_cases': len(all_cases),
                        'test_results': test_results,
                        'execution_time': total_execution_time,
                        'error_message': error_msg
                    }
                continue
            
            # 比较输出
            actual_output = result.get('output', '')
            is_passed = compare_output(actual_output, expected_output)
            
            if is_passed:
                passed_count += 1
                test_status = 'passed'
            else:
                test_status = 'failed'
            
            test_results.append({
                'case_id': idx + 1,
                'status': test_status,
                'input': case_input,
                'expected_output': expected_output,
                'actual_output': actual_output,
                'execution_time': execution_time
            })
        
        # 5. 判断最终状态
        if passed_count == len(all_cases):
            final_status = 'accepted'
            error_message = None
        elif passed_count == 0:
            final_status = 'wrong_answer'
            error_message = '所有测试用例未通过'
        else:
            final_status = 'wrong_answer'
            error_message = f'部分测试用例未通过（{passed_count}/{len(all_cases)}）'
        
        return {
            'status': final_status,
            'passed_cases': passed_count,
            'total_cases': len(all_cases),
            'test_results': test_results,
            'execution_time': round(total_execution_time, 3),
            'error_message': error_message
        }

