# -*- coding: utf-8 -*-
"""
管理后台 API Schema 定义（Pydantic）
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class SubjectIdsSchema(BaseModel):
    """科目ID列表Schema"""
    subject_ids: List[int] = Field(..., description="科目ID列表", min_length=1)
    
    @field_validator('subject_ids')
    @classmethod
    def validate_subject_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError('科目ID列表不能为空')
        return v


class BatchSubjectActionSchema(BaseModel):
    """批量科目操作Schema"""
    action: str = Field(..., description="操作类型")
    subject_ids: List[int] = Field(..., description="科目ID列表", min_length=1)
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        if v not in ['restrict', 'unrestrict']:
            raise ValueError('操作类型必须是 restrict 或 unrestrict')
        return v


class BatchUserSubjectActionSchema(BaseModel):
    """批量用户科目操作Schema"""
    action: str = Field(..., description="操作类型")
    user_ids: List[int] = Field(..., description="用户ID列表", min_length=1)
    subject_ids: List[int] = Field(..., description="科目ID列表", min_length=1)
    
    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        if v not in ['restrict', 'unrestrict']:
            raise ValueError('操作类型必须是 restrict 或 unrestrict')
        return v


class SystemConfigUpdateSchema(BaseModel):
    """系统配置更新Schema"""
    config_value: str = Field(..., description="配置值")
    description: Optional[str] = Field(None, description="配置说明")


class BatchResetQuizCountSchema(BaseModel):
    """批量重置刷题数Schema"""
    user_ids: List[int] = Field(..., description="用户ID列表", min_length=1)





