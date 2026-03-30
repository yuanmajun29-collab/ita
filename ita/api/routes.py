"""API 路由"""

import uuid
import cv2
import numpy as np
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict

from ita.core.calibrator import Calibrator
from ita.core.skin_detector import SkinDetector
from ita.core.ita_calculator import analyze_color
from ita.core.classifier import classify_skin, get_all_categories
from ita.api.models import AnalysisResponse, HealthResponse

router = APIRouter()

# 存储历史结果（内存中，生产环境应使用数据库）
results_store: Dict[str, dict] = {}

# 初始化检测器
calibrator = Calibrator()
skin_detector = SkinDetector()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse()


@router.get("/categories")
async def get_categories():
    """获取所有肤色分类"""
    return {"categories": get_all_categories()}


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_image(file: UploadFile = File(...)):
    """
    上传图片进行肤色分析

    参数:
        file: 图片文件（支持 jpg, png, webp）

    返回:
        AnalysisResponse: 分析结果
    """
    # 验证文件类型
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file.content_type}，请上传 JPG/PNG/WebP 格式"
        )

    # 读取图片
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(status_code=400, detail="无法读取图片文件")

    try:
        # 步骤1：检测白纸区域
        white_mask, white_info = calibrator.detect_white_region(image)

        # 步骤2：检测皮肤区域
        skin_mask, skin_info = skin_detector.detect_skin(image, white_mask)

        if not skin_info["detected"]:
            return AnalysisResponse(
                success=False,
                message=skin_info.get("reason", "未检测到皮肤区域")
            )

        # 步骤3：提取皮肤颜色
        skin_rgb_bgr, extract_info = skin_detector.extract_skin_color(image, skin_mask)

        if not extract_info["success"]:
            return AnalysisResponse(
                success=False,
                message=extract_info.get("reason", "无法提取皮肤颜色")
            )

        # 步骤4：白纸校准
        calibrated = False
        if white_info["detected"] and white_mask is not None:
            # OpenCV BGR → RGB
            skin_rgb_rgb = np.array([skin_rgb_bgr[2], skin_rgb_bgr[1], skin_rgb_bgr[0]])
            normalized_rgb, calib_info = calibrator.calibrate(image, skin_rgb_bgr, white_mask)
            calibrated = calib_info.get("success", False)

            # 使用校准后的 RGB（注意顺序：calibrator 返回 BGR 顺序）
            input_rgb = np.array([normalized_rgb[2], normalized_rgb[1], normalized_rgb[0]])
        else:
            # 无白纸，直接使用原始 RGB
            input_rgb = np.array([skin_rgb_bgr[2], skin_rgb_bgr[1], skin_rgb_bgr[0]])

        # 步骤5：颜色分析（RGB → Lab → ITA°）
        color_info = analyze_color(input_rgb)

        # 步骤6：肤色分类
        classification = classify_skin(color_info["ita"])

        # 生成结果
        result_id = str(uuid.uuid4())[:8]
        response = AnalysisResponse(
            success=True,
            ita=classification["ita"],
            category=classification["category_name"],
            category_id=classification["category_id"],
            description=classification["description"],
            fitzpatrick=classification["fitzpatrick"],
            uv_advice=classification["uv_advice"],
            confidence=classification["confidence"],
            lab=color_info["lab"],
            calibrated=calibrated,
            message="分析完成" + ("（已白纸校准）" if calibrated else "（未检测到白纸，结果仅供参考）")
        )

        # 存储结果
        results_store[result_id] = {
            "response": response.model_dump(),
            "timestamp": datetime.now().isoformat()
        }

        return response

    except Exception as e:
        return AnalysisResponse(
            success=False,
            message=f"分析过程出错: {str(e)}"
        )


@router.get("/result/{result_id}")
async def get_result(result_id: str):
    """查询历史分析结果"""
    if result_id not in results_store:
        raise HTTPException(status_code=404, detail="未找到该分析结果")

    return results_store[result_id]
