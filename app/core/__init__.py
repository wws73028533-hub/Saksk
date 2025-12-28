# -*- coding: utf-8 -*-
"""
core核心模块 - 共享代码
包含：数据模型、工具函数、配置、扩展等
"""

# 导出常用模块，方便导入
from . import models
from . import utils
from . import config
from . import extensions

__all__ = ['models', 'utils', 'config', 'extensions']

