"""API 数据模型定义"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AnalysisResponse(BaseModel):
    """肤色分析结果"""
    success: bool = Field(..., description="分析是否成功")
    ita: Optional[float] = Field(None, description="ITA 角度值")
    category: Optional[str] = Field(None, description="肤色分类名称")
    category_id: Optional[str] = Field(None, description="肤色分类ID")
    description: Optional[str] = Field(None, description="分类描述")
    fitzpatrick: Optional[List[str]] = Field(None, description="Fitzpatrick 分型参考")
    uv_advice: Optional[str] = Field(None, description="紫外线防护建议")
    confidence: Optional[float] = Field(None, description="置信度")
    lab: Optional[dict] = Field(None, description="L*a*b* 色彩值")
    calibrated: bool = Field(False, description="是否使用了白纸校准")
    message: Optional[str] = Field(None, description="额外信息或错误说明")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    version: str = "1.0.0"
