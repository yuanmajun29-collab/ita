"""
API 数据模型定义
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any


class AnalysisResult(BaseModel):
    """肤色分析结果"""
    ita: float
    category: str
    description: str
    fitzpatrick: str
    color_hex: str
    confidence: float
    lab: Dict[str, float]
    xyz: Optional[Dict[str, float]] = None
    calibration: Optional[Dict] = None
    all_scores: Optional[Dict[str, float]] = None


class AnalysisResponse(BaseModel):
    """API 响应"""
    success: bool
    message: str
    result: Optional[AnalysisResult | Dict[str, Any]] = None
    timestamp: str


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    timestamp: str


class HistoryRecord(BaseModel):
    """历史记录"""
    id: str
    ita: float
    category: str
    fitzpatrick: str
    lab: Dict[str, float]
    timestamp: str
