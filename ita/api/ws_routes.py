"""
实时质量检测 API 路由

提供 WebSocket 实时质量反馈和单帧质量检查接口。
"""

import base64
import json
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ita.core.quality_checker import QualityChecker

router = APIRouter(prefix="/api")
quality_checker = QualityChecker()


class QualityResponse(BaseModel):
    """质量检查响应"""
    success: bool
    score: float
    ready: bool
    tips: list
    checks: dict


def _decode_image(image_b64: str) -> Optional[np.ndarray]:
    """Base64 解码图像"""
    try:
        # 去除 data:image/xxx;base64, 前缀
        if ',' in image_b64:
            image_b64 = image_b64.split(',')[1]
        img_data = base64.b64decode(image_b64)
        nparr = np.frombuffer(img_data, np.uint8)
        return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception:
        return None


@router.post("/quality-check", response_model=QualityResponse)
async def check_quality(file: UploadFile = File(...)):
    """
    单帧图像质量检查

    上传一张图片，返回质量评估结果。
    用于拍照后/上传前的质量预检。
    """
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        return QualityResponse(
            success=False, score=0.0, ready=False,
            tips=["⚠️ 无法解析图片"], checks={}
        )

    result = quality_checker.check_all(image)

    return QualityResponse(
        success=True,
        score=result["score"],
        ready=result["ready"],
        tips=result["tips"],
        checks={k: {kk: vv for kk, vv in v.items() if kk != "mask"}
                for k, v in result["checks"].items()},
    )


@router.websocket("/ws/quality")
async def websocket_quality(websocket: WebSocket):
    """
    WebSocket 实时质量检测

    前端摄像头预览时，持续发送帧数据，
    后端实时返回质量评估结果。

    协议：
    - 客户端发送: {"image": "data:image/jpeg;base64,..."}
    - 服务端返回: {"score": 0.85, "ready": true, "tips": [...], "checks": {...}}
    """
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                image_b64 = msg.get("image", "")
                if not image_b64:
                    await websocket.send_json({"error": "无图像数据"})
                    continue

                image = _decode_image(image_b64)
                if image is None:
                    await websocket.send_json({"error": "图像解析失败"})
                    continue

                # 缩小图像加速处理
                h, w = image.shape[:2]
                if max(h, w) > 480:
                    scale = 480 / max(h, w)
                    small = cv2.resize(image, (int(w * scale), int(h * scale)))
                else:
                    small = image

                result = quality_checker.check_all(small)

                # 响应（不包含 mask 等大数据）
                response = {
                    "score": result["score"],
                    "ready": result["ready"],
                    "tips": result["tips"],
                    "checks": {}
                }
                for key, value in result["checks"].items():
                    check_data = {}
                    for ck, cv_val in value.items():
                        if ck == "mask":
                            # 将 mask 编码为 base64 缩略图
                            try:
                                _, buf = cv2.imencode('.png', cv_val)
                                check_data["mask_preview"] = base64.b64encode(buf).decode()[:500]
                            except Exception:
                                pass
                        elif isinstance(cv_val, (np.floating, float)):
                            check_data[ck] = round(float(cv_val), 3)
                        elif isinstance(cv_val, (np.integer, int)):
                            check_data[ck] = int(cv_val)
                        elif isinstance(cv_val, bool):
                            check_data[ck] = cv_val
                        else:
                            check_data[ck] = cv_val
                    response["checks"][key] = check_data

                await websocket.send_json(response)

            except json.JSONDecodeError:
                await websocket.send_json({"error": "无效的JSON格式"})
            except Exception as e:
                await websocket.send_json({"error": str(e)})

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
