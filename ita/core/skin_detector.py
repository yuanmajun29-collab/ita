"""
皮肤区域检测与提取模块

使用 YCbCr 和 HSV 色彩空间联合检测皮肤像素，
排除白纸区域，取中间亮度像素计算平均颜色。
"""

import cv2
import numpy as np
from typing import Tuple, Optional


class SkinDetector:
    """皮肤区域检测器"""

    def __init__(self):
        # YCbCr 肤色范围（经典阈值）
        self.ycbcr_cb_low = 77
        self.ycbcr_cb_high = 127
        self.ycbcr_cr_low = 133
        self.ycbcr_cr_high = 173

        # HSV 肤色范围
        self.hsv_h_low = 0
        self.hsv_h_high = 25      # 肤色色相范围（红色-橙色）
        self.hsv_s_low = 30       # 最低饱和度（排除灰白）
        self.hsv_s_high = 200     # 最高饱和度
        self.hsv_v_low = 50       # 最低亮度
        self.hsv_v_high = 255

        # 中间亮度采样范围
        self.brightness_pct_low = 25
        self.brightness_pct_high = 75

        # 最小皮肤面积比例
        self.min_skin_area_ratio = 0.005

    def detect_skin(self, image: np.ndarray,
                    white_mask: Optional[np.ndarray] = None) -> Tuple[np.ndarray, dict]:
        """
        检测图像中的皮肤区域

        参数:
            image: BGR 格式图像
            white_mask: 白纸区域掩码（可选，用于排除）

        返回:
            (skin_mask, info)
            skin_mask: 皮肤区域二值掩码
            info: 检测信息
        """
        ycbcr = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # YCbCr 皮肤掩码
        mask_ycbcr = cv2.inRange(
            ycbcr,
            np.array([0, self.ycbcr_cb_low, self.ycbcr_cr_low]),
            np.array([255, self.ycbcr_cb_high, self.ycbcr_cr_high])
        )

        # HSV 皮肤掩码
        mask_hsv = cv2.inRange(
            hsv,
            np.array([self.hsv_h_low, self.hsv_s_low, self.hsv_v_low]),
            np.array([self.hsv_h_high, self.hsv_s_high, self.hsv_v_high])
        )

        # 额外处理深色皮肤（色相偏大）
        mask_hsv_dark = cv2.inRange(
            hsv,
            np.array([5, 15, 20]),
            np.array([35, 180, 200])
        )

        # 合并掩码
        skin_mask = cv2.bitwise_and(mask_ycbcr, mask_hsv)
        skin_mask = cv2.bitwise_or(skin_mask, cv2.bitwise_and(mask_ycbcr, mask_hsv_dark))

        # 排除白纸区域
        if white_mask is not None:
            skin_mask = cv2.bitwise_and(skin_mask, cv2.bitwise_not(white_mask))

        # 形态学去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel, iterations=1)

        # 填充小孔洞
        skin_mask = cv2.dilate(skin_mask, kernel, iterations=1)

        # 统计信息
        skin_area = np.sum(skin_mask > 0)
        total_area = image.shape[0] * image.shape[1]
        area_ratio = skin_area / total_area

        if skin_area == 0:
            return skin_mask, {
                "detected": False,
                "reason": "未检测到皮肤区域",
                "area_ratio": 0
            }

        return skin_mask, {
            "detected": True,
            "area_ratio": area_ratio,
            "area_pixels": int(skin_area)
        }

    def extract_skin_color(self, image: np.ndarray,
                           skin_mask: np.ndarray) -> Tuple[np.ndarray, dict]:
        """
        从皮肤掩码中提取平均颜色（排除极端亮度像素）

        参数:
            image: BGR 格式图像
            skin_mask: 皮肤区域掩码

        返回:
            (mean_rgb, info)
            mean_rgb: 皮肤平均 RGB 值 [B, G, R]
            info: 额外信息
        """
        skin_pixels = image[skin_mask == 255]

        if len(skin_pixels) == 0:
            return np.array([0, 0, 0]), {
                "success": False,
                "reason": "皮肤区域无有效像素"
            }

        # 计算亮度
        gray = cv2.cvtColor(
            skin_pixels.reshape(-1, 1, 3).astype(np.uint8),
            cv2.COLOR_BGR2GRAY
        ).flatten()

        # 排除极端亮度像素（高光和阴影）
        p_low = np.percentile(gray, self.brightness_pct_low)
        p_high = np.percentile(gray, self.brightness_pct_high)
        valid = (gray >= p_low) & (gray <= p_high)
        valid_pixels = skin_pixels[valid]

        if len(valid_pixels) < 10:
            valid_pixels = skin_pixels

        mean_rgb = np.mean(valid_pixels, axis=0)
        std_rgb = np.std(valid_pixels, axis=0)

        return mean_rgb, {
            "success": True,
            "mean_rgb": mean_rgb.tolist(),
            "std_rgb": std_rgb.tolist(),
            "valid_pixels": len(valid_pixels),
            "total_pixels": len(skin_pixels)
        }
