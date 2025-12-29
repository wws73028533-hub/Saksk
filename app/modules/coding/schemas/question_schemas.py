# -*- coding: utf-8 -*-
"""
题目相关Schema
使用Pydantic进行数据验证和序列化
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class QuestionCreateSchema(BaseModel):
    """创建题目Schema"""
    title: str = Field(..., min_length=1, max_length=200, description="题目标题")
    subject_id: Optional[int] = Field(None, description="科目ID")
    q_type: str = Field(..., description="题目类型", pattern="^(函数题|编程题)$")
    difficulty: str = Field(..., description="难度等级", pattern="^(easy|medium|hard)$")
    description: str = Field(..., min_length=1, description="题目描述")
    examples: Optional[List[Dict[str, Any]]] = Field(default=[], description="输入输出示例")
    constraints: Optional[List[str]] = Field(default=[], description="约束条件")
    code_template: Optional[str] = Field(default="", description="代码模板")
    programming_language: str = Field(default="python", description="编程语言")
    time_limit: int = Field(default=5, ge=1, le=30, description="时间限制（秒）")
    memory_limit: int = Field(default=128, ge=64, le=512, description="内存限制（MB）")
    test_cases_json: str = Field(..., description="测试用例（JSON格式）")
    hints: Optional[List[str]] = Field(default=[], description="提示信息")
    is_enabled: bool = Field(default=True, description="是否启用")


class QuestionUpdateSchema(BaseModel):
    """更新题目Schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="题目标题")
    subject_id: Optional[int] = Field(None, description="科目ID")
    q_type: Optional[str] = Field(None, description="题目类型", pattern="^(函数题|编程题)$")
    difficulty: Optional[str] = Field(None, description="难度等级", pattern="^(easy|medium|hard)$")
    description: Optional[str] = Field(None, min_length=1, description="题目描述")
    examples: Optional[List[Dict[str, Any]]] = Field(None, description="输入输出示例")
    constraints: Optional[List[str]] = Field(None, description="约束条件")
    code_template: Optional[str] = Field(None, description="代码模板")
    programming_language: Optional[str] = Field(None, description="编程语言")
    time_limit: Optional[int] = Field(None, ge=1, le=30, description="时间限制（秒）")
    memory_limit: Optional[int] = Field(None, ge=64, le=512, description="内存限制（MB）")
    test_cases_json: Optional[str] = Field(None, description="测试用例（JSON格式）")
    hints: Optional[List[str]] = Field(None, description="提示信息")
    is_enabled: Optional[bool] = Field(None, description="是否启用")


class QuestionResponseSchema(BaseModel):
    """题目响应Schema"""
    id: int = Field(..., description="题目ID")
    title: str = Field(..., description="题目标题")
    subject_id: Optional[int] = Field(None, description="科目ID")
    subject_name: Optional[str] = Field(None, description="科目名称")
    difficulty: str = Field(..., description="难度等级")
    description: str = Field(..., description="题目描述")
    examples: Optional[List[Dict[str, Any]]] = Field(default=[], description="输入输出示例")
    constraints: Optional[List[str]] = Field(default=[], description="约束条件")
    code_template: Optional[str] = Field(default="", description="代码模板")
    programming_language: str = Field(default="python", description="编程语言")
    time_limit: int = Field(default=5, description="时间限制（秒）")
    memory_limit: int = Field(default=128, description="内存限制（MB）")
    hints: Optional[List[str]] = Field(default=[], description="提示信息")
    acceptance_rate: Optional[float] = Field(None, description="通过率")
    total_submissions: Optional[int] = Field(None, description="总提交次数")
    is_favorite: Optional[bool] = Field(None, description="是否收藏")
    status: Optional[str] = Field(None, description="用户状态（unsolved/solving/solved）")
    created_at: Optional[str] = Field(None, description="创建时间")

    class Config:
        from_attributes = True
        # Pydantic v2 兼容性
        populate_by_name = True


class QuestionListResponseSchema(BaseModel):
    """题目列表响应Schema"""
    questions: List[QuestionResponseSchema] = Field(..., description="题目列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    per_page: int = Field(..., description="每页数量")

