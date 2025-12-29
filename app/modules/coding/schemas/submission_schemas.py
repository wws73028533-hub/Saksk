# -*- coding: utf-8 -*-
"""
提交相关Schema
使用Pydantic进行数据验证和序列化
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ExecuteCodeSchema(BaseModel):
    """执行代码Schema（不判题）"""
    code: str = Field(..., min_length=1, description="代码")
    language: str = Field(default="python", description="编程语言")
    input: Optional[str] = Field(default=None, description="输入数据（可选）")
    time_limit: Optional[int] = Field(default=5, ge=1, le=30, description="时间限制（秒）")
    memory_limit: Optional[int] = Field(default=128, ge=64, le=512, description="内存限制（MB）")


class SubmitCodeSchema(BaseModel):
    """提交代码Schema（自动判题）"""
    question_id: int = Field(..., gt=0, description="题目ID")
    code: str = Field(..., min_length=1, description="代码")
    language: str = Field(default="python", description="编程语言")


class TestCaseResultSchema(BaseModel):
    """测试用例结果Schema"""
    case_id: int = Field(..., description="测试用例ID")
    status: str = Field(..., description="状态（passed/failed）")
    input: Optional[str] = Field(None, description="输入")
    expected_output: Optional[str] = Field(None, description="期望输出")
    actual_output: Optional[str] = Field(None, description="实际输出")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")


class SubmissionResponseSchema(BaseModel):
    """提交响应Schema"""
    id: int = Field(..., description="提交ID")
    question_id: int = Field(..., description="题目ID")
    question_title: Optional[str] = Field(None, description="题目标题")
    code: str = Field(..., description="提交的代码")
    language: str = Field(..., description="编程语言")
    status: str = Field(..., description="提交状态")
    passed_cases: int = Field(..., description="通过的测试用例数")
    total_cases: int = Field(..., description="总测试用例数")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")
    error_message: Optional[str] = Field(None, description="错误信息")
    test_results: Optional[List[TestCaseResultSchema]] = Field(None, description="测试用例结果")
    submitted_at: str = Field(..., description="提交时间")

    class Config:
        from_attributes = True
        # Pydantic v2 兼容性
        populate_by_name = True


class SubmissionListResponseSchema(BaseModel):
    """提交列表响应Schema"""
    submissions: List[SubmissionResponseSchema] = Field(..., description="提交列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    per_page: int = Field(..., description="每页数量")

