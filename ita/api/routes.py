"""
API 路由模块

提供图片上传分析、健康检查、历史记录查询等接口。
"""

import uuid
import os
import tempfile
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException

from ita.core.calibrator import WhitePaperCalibrator
from ita.core.skin_detector import SkinDetector
from ita.core.ita_calculator import ITACalculator
from ita.core.classifier import SkinClassifier
from ita.api.models import AnalysisResponse, AnalysisResult, HealthResponse, HistoryRecord

router = APIRouter(prefix="/api")

# 简单的内存历史记录存储
_history_store: list = []

# 允许的图片类型
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def _allowed_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_skin(file: UploadFile = File(...)):
    """
    上传图片进行肤色分析

    要求图片包含前臂皮肤和白色A4纸（用于校准）
    """
    # 验证文件类型
    if not file.filename or not _allowed_file(file.filename):
        return AnalysisResponse(
            success=False,
            message="不支持的文件格式，请上传 JPG/PNG/BMP/WebP 图片",
            timestamp=datetime.now().isoformat()
        )

    # 读取文件
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        return AnalysisResponse(
            success=False,
            message="文件过大，请上传小于 10MB 的图片",
            timestamp=datetime.now().isoformat()
        )

    # 解码图片
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        return AnalysisResponse(
            success=False,
            message="无法解析图片，请确保文件未损坏",
            timestamp=datetime.now().isoformat()
        )

    try:
        # 1. 白纸校准
        calibrator = WhitePaperCalibrator()
        cal_result = calibrator.calibrate(image)

        if not cal_result["success"]:
            return AnalysisResponse(
                success=False,
                message=cal_result["message"],
                timestamp=datetime.now().isoformat()
            )

        # 2. 皮肤检测
        detector = SkinDetector()
        skin_mask = detector.detect_skin_exclude_white(
            image, mask=calibrator.detect_white_paper(image)
        )

        if skin_mask is None:
            return AnalysisResponse(
                success=False,
                message="未检测到皮肤区域，请确保手臂清晰可见",
                timestamp=datetime.now().isoformat()
            )

        skin_rgb = detector.get_skin_mean_rgb(image, skin_mask)
        if skin_rgb is None:
            return AnalysisResponse(
                success=False,
                message="皮肤区域采样失败，请重拍",
                timestamp=datetime.now().isoformat()
            )

        # 3. 颜色归一化
        normalized_rgb = calibrator.normalize_color(skin_rgb)

        # 4. ITA° 计算
        calculator = ITACalculator()
        analysis = calculator.analyze(normalized_rgb)

        # 5. 肤色分类
        classifier = SkinClassifier()
        classification = classifier.classify(analysis["ita"])

        # 构建结果
        result = AnalysisResult(
            ita=analysis["ita"],
            category=classification["category"],
            description=classification["description"],
            fitzpatrick=classification["fitzpatrick"],
            color_hex=classification["color_hex"],
            confidence=classification["confidence"],
            lab=analysis["lab"],
            xyz=analysis.get("xyz"),
            calibration={
                "white_mean_rgb": cal_result["white_mean_rgb"],
                "skin_mean_rgb": skin_rgb,
                "normalized_rgb": tuple(round(v, 2) for v in normalized_rgb)
            },
            all_scores=classification["all_scores"]
        )

        # 保存到历史记录
        record_id = str(uuid.uuid4())[:8]
        _history_store.append({
            "id": record_id,
            "ita": result.ita,
            "category": result.category,
            "fitzpatrick": result.fitzpatrick,
            "lab": result.lab,
            "timestamp": datetime.now().isoformat()
        })

        return AnalysisResponse(
            success=True,
            message="分析完成",
            result=result,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        return AnalysisResponse(
            success=False,
            message=f"分析过程出错: {str(e)}",
            timestamp=datetime.now().isoformat()
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查接口"""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        timestamp=datetime.now().isoformat()
    )


@router.get("/result/{record_id}", response_model=AnalysisResponse)
async def get_result(record_id: str):
    """查询历史分析结果"""
    for record in reversed(_history_store):
        if record["id"] == record_id:
            return AnalysisResponse(
                success=True,
                message="查询成功",
                result=AnalysisResult(**record),
                timestamp=datetime.now().isoformat()
            )

    return AnalysisResponse(
        success=False,
        message=f"未找到记录 {record_id}",
        timestamp=datetime.now().isoformat()
    )


@router.get("/history", response_model=AnalysisResponse)
async def get_history():
    """获取所有历史记录"""
    records = []
    for r in reversed(_history_store[-20:]):  # 最近 20 条
        records.append(HistoryRecord(**r))

    return AnalysisResponse(
        success=True,
        message=f"共 {len(records)} 条记录",
        timestamp=datetime.now().isoformat()
    )
