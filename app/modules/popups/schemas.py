# -*- coding: utf-8 -*-
"""弹窗模块 Pydantic 验证模型"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PopupCreateSchema(BaseModel):
    """创建弹窗的验证模型"""
    title: str = Field(..., min_length=1, max_length=200, description="弹窗标题")
    content: str = Field(..., min_length=1, description="弹窗内容（纯文本）")
    popup_type: str = Field(default='info', description="弹窗类型：info/warning/success/error")
    is_active: bool = Field(default=True, description="是否启用")
    priority: int = Field(default=0, ge=0, description="优先级（数字越大越优先）")
    start_at: Optional[datetime] = Field(default=None, description="开始显示时间")
    end_at: Optional[datetime] = Field(default=None, description="结束显示时间")

    class Config:
        json_schema_extra = {
            "example": {
                "title": "系统维护通知",
                "content": "系统将于今晚22:00-24:00进行维护，期间可能无法访问。",
                "popup_type": "warning",
                "is_active": True,
                "priority": 10,
                "start_at": "2025-01-20T00:00:00",
                "end_at": "2025-01-21T23:59:59"
            }
        }


class PopupUpdateSchema(BaseModel):
    """更新弹窗的验证模型"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    popup_type: Optional[str] = Field(None)
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None


class PopupResponseSchema(BaseModel):
    """弹窗响应模型"""
    id: int
    title: str
    content: str
    popup_type: str
    is_active: bool
    priority: int
    start_at: Optional[datetime]
    end_at: Optional[datetime]
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PopupStatsSchema(BaseModel):
    """弹窗统计模型"""
    popup_id: int
    total_views: int = Field(description="总显示次数")
    total_dismissals: int = Field(description="总关闭次数")
    dismissal_rate: float = Field(description="关闭率（0-1）")


