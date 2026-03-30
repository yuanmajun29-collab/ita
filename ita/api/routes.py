"""
API 路由模块

提供图片上传分析、健康检查、历史记录查询、UV建议等接口。
"""

import uuid
import os
from datetime import datetime
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, HTTPException, Query

from ita.core.calibrator import WhitePaperCalibrator
from ita.core.skin_detector import SkinDetector
from ita.core.ita_calculator import ITACalculator
from ita.core.classifier import SkinClassifier
from ita.core.uv_advisor import UVAdvisor
from ita.core.database import get_database
from ita.api.models import AnalysisResponse, AnalysisResult, HealthResponse

router = APIRouter(prefix="/api")

# 允许的图片类型
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# UV 建议模块
_uv_advisor = UVAdvisor()


def _allowed_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_skin(
    file: UploadFile = File(...),
    lat: Optional[float] = Query(None, description="纬度，用于UV指数估算"),
    lon: Optional[float] = Query(None, description="经度，用于UV指数估算"),
    month: Optional[int] = Query(None, description="月份1-12，无定位时用"),
    hour: Optional[int] = Query(None, description="小时0-23，无定位时用"),
):
    """
    上传图片进行肤色分析

    要求图片包含前臂皮肤和白色A4纸（用于校准）
    可选传入坐标或时间，获取UV照射建议
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

        # 6. UV 指数获取
        uv_index = None
        uv_info = None
        vitd_advice = None
        location_str = None

        if lat is not None and lon is not None:
            location_str = f"{lat},{lon}"
            # 尝试从 API 获取 UV
            uv_data = await _uv_advisor.fetch_uv_index(lat, lon)
            if uv_data:
                uv_index = uv_data["uv_index"]
            else:
                # API 不可用，用估算值
                now = datetime.now()
                uv_index = _uv_advisor.estimate_uv_from_context(
                    now.month, now.hour, lat
                )
        elif month is not None and hour is not None:
            lat = 30.0  # 默认重庆纬度
            uv_index = _uv_advisor.estimate_uv_from_context(month, hour, lat)

        if uv_index is not None:
            uv_info = _uv_advisor.get_uv_level_info(uv_index)
            vitd_advice = _uv_advisor.calculate_vitd_advice(
                ita=analysis["ita"],
                fitzpatrick=classification["fitzpatrick"],
                uv_index=uv_index
            )

        # 7. 构建结果
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

        # 8. 保存到数据库
        record_id = str(uuid.uuid4())[:8]
        db = get_database()
        db_record = {
            "id": record_id,
            "ita": result.ita,
            "category": result.category,
            "fitzpatrick": result.fitzpatrick,
            "description": result.description,
            "color_hex": result.color_hex,
            "confidence": result.confidence,
            "lab": result.lab,
            "calibration": result.calibration,
            "uv_index": uv_index,
            "location": location_str,
            "vitd_advice": vitd_advice,
        }
        db.save_analysis(db_record)

        # 构建完整响应
        response_data = result.model_dump()
        if uv_info:
            response_data["uv"] = uv_info
        if vitd_advice:
            response_data["vitd_advice"] = vitd_advice
        response_data["record_id"] = record_id

        return AnalysisResponse(
            success=True,
            message="分析完成",
            result=response_data,
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
    db = get_database()
    record_count = db.get_record_count()
    return HealthResponse(
        status="ok",
        version="1.1.0",
        timestamp=datetime.now().isoformat()
    )


@router.get("/result/{record_id}", response_model=AnalysisResponse)
async def get_result(record_id: str):
    """查询历史分析结果"""
    db = get_database()
    record = db.get_record(record_id)

    if record is None:
        return AnalysisResponse(
            success=False,
            message=f"未找到记录 {record_id}",
            timestamp=datetime.now().isoformat()
        )

    return AnalysisResponse(
        success=True,
        message="查询成功",
        result=record,
        timestamp=datetime.now().isoformat()
    )


@router.get("/history", response_model=AnalysisResponse)
async def get_history(limit: int = Query(20, ge=1, le=100)):
    """获取最近的历史记录"""
    db = get_database()
    records = db.get_recent_records(limit)

    return AnalysisResponse(
        success=True,
        message=f"共 {len(records)} 条记录",
        result={"records": records, "total": db.get_record_count()},
        timestamp=datetime.now().isoformat()
    )


@router.get("/trend", response_model=AnalysisResponse)
async def get_trend(days: int = Query(30, ge=1, le=365)):
    """获取 ITA° 变化趋势"""
    db = get_database()
    trend = db.get_ita_trend(days)

    return AnalysisResponse(
        success=True,
        message=f"近 {days} 天趋势",
        result=trend,
        timestamp=datetime.now().isoformat()
    )


@router.post("/uv-advice", response_model=AnalysisResponse)
async def get_uv_advice(
    ita: float = Query(..., description="ITA° 值"),
    fitzpatrick: str = Query(..., description="Fitzpatrick 分型，如 II-III"),
    uv_index: Optional[float] = Query(None, description="UV 指数"),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    month: Optional[int] = Query(None),
    hour: Optional[int] = Query(None),
    exposure_time: Optional[float] = Query(None, description="计划照射分钟数"),
):
    """单独获取 UV 照射建议"""
    # 获取 UV 指数
    if uv_index is None:
        if lat is not None and lon is not None:
            uv_data = await _uv_advisor.fetch_uv_index(lat, lon)
            if uv_data:
                uv_index = uv_data["uv_index"]

        if uv_index is None:
            now = datetime.now()
            m = month or now.month
            h = hour or now.hour
            la = lat or 30.0
            uv_index = _uv_advisor.estimate_uv_from_context(m, h, la)

    advice = _uv_advisor.calculate_vitd_advice(
        ita=ita,
        fitzpatrick=fitzpatrick,
        uv_index=uv_index,
        exposure_time_minutes=exposure_time
    )

    return AnalysisResponse(
        success=True,
        message="UV 建议计算完成",
        result=advice,
        timestamp=datetime.now().isoformat()
    )
