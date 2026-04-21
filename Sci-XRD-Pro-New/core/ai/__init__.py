# -*- coding: utf-8 -*-
"""
Sci-XRD-Pro AI分析模块
=====================

集成Ollama本地AI服务，为XRD分析提供智能辅助功能

主要功能:
- 图谱智能解读
- 物相匹配建议  
- 杂质检测提醒
- 分析报告生成
"""

from .client import OllamaClient, get_ai_client

__all__ = ['OllamaClient', 'get_ai_client']
