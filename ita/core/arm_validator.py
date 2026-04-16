"""
前臂（手臂）区域粗检

在已有皮肤掩码上，要求主导连通域呈条状（外接框长宽比），避免仅凭面部、
手部特写或其它小块肤色通过分析。与医学「是否为上臂」无关，仅为构图启发式。
"""

from __future__ import annotations

from typing import Dict, Tuple

import cv2
import numpy as np

# 最大皮肤连通域至少占整图比例（过滤极小色块）
MIN_LARGEST_BLOB_AREA_RATIO = 0.012

# 主导连通域最少像素
MIN_LARGEST_BLOB_PIXELS = 600

# 条状程度：max(宽,高)/min(宽,高)；真实照片可能略低，需与「近似正方形」色块区分
MIN_ELONGATION = 1.12


def _elongation_from_contour(contour) -> float:
    """同时考虑轴对齐外接矩形与最小外接矩形，取较大长宽比（利于斜拍前臂）。"""
    x, y, w, h = cv2.boundingRect(contour)
    asp = max(w, h) / max(min(w, h), 1)

    rect = cv2.minAreaRect(contour)
    (rw, rh) = rect[1]
    if rw <= 0 or rh <= 0:
        return float(asp)
    rw, rh = max(rw, rh), min(rw, rh)
    asp2 = rw / max(rh, 1e-6)
    return float(max(asp, asp2))


def validate_forearm_skin_mask(skin_mask: np.ndarray) -> Tuple[bool, str]:
    """
    判断皮肤掩码是否像「画面中存在伸展的前臂」一类条状区域。

    Returns:
        (True, "") 通过
        (False, message) 不通过
    """
    if skin_mask is None or skin_mask.size == 0:
        return False, "未检测到皮肤区域"

    h, w = skin_mask.shape[:2]
    img_area = float(h * w)
    total_skin = int(cv2.countNonZero(skin_mask))
    if total_skin < MIN_LARGEST_BLOB_PIXELS:
        return False, "皮肤区域过小，请将前臂完整收入画面"

    contours, _ = cv2.findContours(
        skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return False, "未检测到连贯的皮肤区域"

    largest = max(contours, key=cv2.contourArea)
    area = float(cv2.contourArea(largest))
    if area < MIN_LARGEST_BLOB_PIXELS:
        return False, "主导皮肤区域过小，请确保以手臂为主角拍摄"

    if area / img_area < MIN_LARGEST_BLOB_AREA_RATIO:
        return False, "画面中皮肤占比不足，请让前臂占据更大画面"

    elong = _elongation_from_contour(largest)
    if elong < MIN_ELONGATION:
        return (
            False,
            "未识别到典型前臂条状区域，请拍摄包含伸展前臂的照片（避免仅有面部或特写）",
        )

    return True, ""


def validate_forearm_skin_mask_detail(skin_mask: np.ndarray) -> Dict:
    """返回是否通过及诊断数值（便于调试）。"""
    ok, msg = validate_forearm_skin_mask(skin_mask)
    detail: Dict = {"ok": ok, "message": msg}
    if skin_mask is None or skin_mask.size == 0:
        return detail

    contours, _ = cv2.findContours(
        skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if contours:
        largest = max(contours, key=cv2.contourArea)
        h, w = skin_mask.shape[:2]
        area = float(cv2.contourArea(largest))
        detail["largest_area_ratio"] = round(area / (h * w), 4)
        detail["elongation"] = round(_elongation_from_contour(largest), 2)
    return detail
