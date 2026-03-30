"""
白纸检测与颜色校准模块

通过检测图像中的白色A4纸区域，计算光照校准系数，
消除不同设备和光照条件对肤色分析的影响。
"""

import cv2
import numpy as np
from typing import Optional, Tuple, Dict


class WhitePaperCalibrator:
    """白纸校准器：基于白纸参考进行颜色归一化"""

    # HSV 空间白纸检测阈值
    WHITE_HSV_LOW = np.array([0, 0, 200])
    WHITE_HSV_HIGH = np.array([180, 50, 255])

    def __init__(self, min_area_ratio: float = 0.02):
        """
        初始化校准器

        Args:
            min_area_ratio: 白纸最小面积占比（相对于全图），低于此值视为未检测到白纸
        """
        self.min_area_ratio = min_area_ratio
        self.calibration_coefficients: Optional[Tuple[float, float, float]] = None
        self.white_mean_rgb: Optional[Tuple[int, int, int]] = None
        self.is_calibrated = False

    def detect_white_paper(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        自动检测图像中的白纸区域

        Args:
            image: BGR 格式输入图像

        Returns:
            白纸区域的掩码（mask），未检测到返回 None
        """
        if image is None or image.size == 0:
            return None

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # 基于亮度 V 通道先粗筛高亮区域
        v_channel = hsv[:, :, 2]
        _, bright_mask = cv2.threshold(v_channel, 200, 255, cv2.THRESH_BINARY)

        # 再用 HSV 三通道精确筛选白色
        white_mask = cv2.inRange(hsv, self.WHITE_HSV_LOW, self.WHITE_HSV_HIGH)

        # 两个掩码取交集
        combined_mask = cv2.bitwise_and(bright_mask, white_mask)

        # 形态学操作：去除噪点、填充空洞
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))

        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel_open)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel_close)

        # 找最大连通区域（白纸通常是最大白色区域）
        contours, _ = cv2.findContours(
            combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours:
            return None

        max_contour = max(contours, key=cv2.contourArea)
        white_area = cv2.contourArea(max_contour)
        image_area = image.shape[0] * image.shape[1]

        # 面积检查
        if white_area / image_area < self.min_area_ratio:
            return None

        # 生成白纸掩码
        mask = np.zeros_like(combined_mask)
        cv2.drawContours(mask, [max_contour], -1, 255, -1)

        return mask

    def get_white_mean(self, image: np.ndarray, mask: np.ndarray) -> Tuple[int, int, int]:
        """
        计算白纸区域的平均 RGB 值

        Args:
            image: BGR 格式图像
            mask: 白纸区域掩码

        Returns:
            (R, G, B) 平均值
        """
        mean_bgr = cv2.mean(image, mask=mask)[:3]
        # 转换为 RGB 顺序
        return (int(mean_bgr[2]), int(mean_bgr[1]), int(mean_bgr[0]))

    def calibrate(
        self,
        image: np.ndarray,
        mask: Optional[np.ndarray] = None
    ) -> Dict:
        """
        执行颜色校准

        Args:
            image: BGR 格式输入图像
            mask: 可选的白纸掩码，为 None 则自动检测

        Returns:
            校准结果字典，包含系数和状态
        """
        result = {
            "success": False,
            "white_mean_rgb": None,
            "coefficients": None,
            "message": ""
        }

        # 自动检测白纸
        if mask is None:
            mask = self.detect_white_paper(image)
            if mask is None:
                result["message"] = "未检测到白纸区域，请确保照片中包含A4白纸"
                return result

        # 计算白纸平均 RGB
        self.white_mean_rgb = self.get_white_mean(image, mask)

        # 检查白纸颜色是否合理（不能太暗或偏色严重）
        if max(self.white_mean_rgb) < 150:
            result["message"] = "白纸区域亮度不足，请在更好的光照条件下拍照"
            return result

        # 计算校准系数（假设理想白纸为 255, 255, 255）
        r, g, b = self.white_mean_rgb
        self.calibration_coefficients = (
            255.0 / max(r, 1),
            255.0 / max(g, 1),
            255.0 / max(b, 1)
        )

        self.is_calibrated = True
        result["success"] = True
        result["white_mean_rgb"] = self.white_mean_rgb
        result["coefficients"] = self.calibration_coefficients
        result["message"] = "校准成功"

        return result

    def normalize_color(
        self,
        skin_rgb: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        """
        基于校准系数归一化皮肤颜色

        Args:
            skin_rgb: 皮肤平均 RGB 值

        Returns:
            归一化后的 RGB 值 (0-255)
        """
        if not self.is_calibrated or self.calibration_coefficients is None:
            return skin_rgb

        kr, kg, kb = self.calibration_coefficients
        r_norm = min(skin_rgb[0] * kr, 255.0)
        g_norm = min(skin_rgb[1] * kg, 255.0)
        b_norm = min(skin_rgb[2] * kb, 255.0)

        return (r_norm, g_norm, b_norm)
