"""
皮肤区域检测与提取模块

使用 YCbCr/HSV 色彩空间检测皮肤像素，
排除白纸区域和高光/阴影，提取有效皮肤样本。
"""

import cv2
import numpy as np
from typing import Optional, Tuple


class SkinDetector:
    """皮肤区域检测器：从图像中提取皮肤像素并计算平均颜色"""

    # YCbCr 肤色阈值（放宽范围以适配更多肤色类型）
    YCBCR_CB_LOW = 77
    YCBCR_CB_HIGH = 177
    YCBCR_CR_LOW = 100
    YCBCR_CR_HIGH = 180

    # HSV 肤色阈值（辅助判断）
    HSV_H_LOW = 0
    HSV_H_HIGH = 50
    HSV_S_LOW = 20
    HSV_S_HIGH = 180

    def __init__(self):
        self.skin_mask: Optional[np.ndarray] = None
        self.skin_mean_rgb: Optional[Tuple[int, int, int]] = None
        self.skin_area_ratio: float = 0.0

    def detect_skin(self, image: np.ndarray) -> Optional[np.ndarray]:
        """
        检测图像中的皮肤区域

        Args:
            image: BGR 格式输入图像

        Returns:
            皮肤区域掩码，未检测到返回 None
        """
        if image is None or image.size == 0:
            return None

        # 转换到 YCbCr 色彩空间
        ycbcr = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
        y, cb, cr = cv2.split(ycbcr)

        # YCbCr 肤色范围
        cb_mask = cv2.inRange(cb, self.YCBCR_CB_LOW, self.YCBCR_CB_HIGH)
        cr_mask = cv2.inRange(cr, self.YCBCR_CR_LOW, self.YCBCR_CR_HIGH)
        ycbcr_skin = cv2.bitwise_and(cb_mask, cr_mask)

        # 转换到 HSV 作为辅助判断
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        h_mask = cv2.inRange(h, self.HSV_H_LOW, self.HSV_H_HIGH)
        s_mask = cv2.inRange(s, self.HSV_S_LOW, self.HSV_S_HIGH)
        hsv_skin = cv2.bitwise_and(h_mask, s_mask)

        # 两个空间取交集，提高准确率
        skin_mask = cv2.bitwise_and(ycbcr_skin, hsv_skin)

        # 排除过亮区域（白纸、高光）- Y 通道 > 230
        bright_mask = cv2.inRange(y, 230, 255)
        skin_mask = cv2.bitwise_and(skin_mask, cv2.bitwise_not(bright_mask))

        # 排除过暗区域（阴影）
        dark_mask = cv2.inRange(v, 0, 40)
        skin_mask = cv2.bitwise_and(skin_mask, cv2.bitwise_not(dark_mask))

        # 形态学操作：去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)

        # 面积检查
        skin_area = cv2.countNonZero(skin_mask)
        self.skin_area_ratio = skin_area / (image.shape[0] * image.shape[1])

        if skin_area < 100:  # 至少 100 个像素
            return None

        self.skin_mask = skin_mask
        return skin_mask

    def detect_skin_exclude_white(
        self,
        image: np.ndarray,
        white_mask: Optional[np.ndarray] = None
    ) -> Optional[np.ndarray]:
        """
        检测皮肤区域并排除白纸区域

        Args:
            image: BGR 格式输入图像
            white_mask: 白纸掩码（可选）

        Returns:
            皮肤区域掩码
        """
        skin_mask = self.detect_skin(image)
        if skin_mask is None:
            return None

        # 如果有白纸掩码，扩大白纸区域再排除（避免白纸边缘的皮肤像素被误纳入）
        if white_mask is not None:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (30, 30))
            expanded_white = cv2.dilate(white_mask, kernel)
            skin_mask = cv2.bitwise_and(skin_mask, cv2.bitwise_not(expanded_white))

        # 再次检查面积
        if cv2.countNonZero(skin_mask) < 50:
            return None

        self.skin_mask = skin_mask
        return skin_mask

    def get_skin_mean_rgb(
        self,
        image: np.ndarray,
        mask: Optional[np.ndarray] = None
    ) -> Optional[Tuple[int, int, int]]:
        """
        计算皮肤区域的平均 RGB 值
        使用中间亮度像素，排除高光和阴影

        Args:
            image: BGR 格式图像
            mask: 皮肤掩码，为 None 使用上次检测结果

        Returns:
            (R, G, B) 平均值
        """
        if mask is None:
            mask = self.skin_mask
        if mask is None:
            return None

        # 获取皮肤像素
        skin_pixels = image[mask > 0]

        if len(skin_pixels) == 0:
            return None

        # 转换为灰度，取中间亮度 40%-80% 的像素（排除高光和阴影）
        gray = cv2.cvtColor(skin_pixels.reshape(-1, 1, 3), cv2.COLOR_BGR2GRAY).flatten()

        lower = np.percentile(gray, 40)
        upper = np.percentile(gray, 80)

        valid_mask = (gray >= lower) & (gray <= upper)
        valid_pixels = skin_pixels[valid_mask]

        if len(valid_pixels) < 10:
            # 如果中间范围像素太少，退而求其次用全部皮肤像素
            valid_pixels = skin_pixels

        mean_bgr = np.mean(valid_pixels, axis=0)
        return (int(mean_bgr[2]), int(mean_bgr[1]), int(mean_bgr[0]))  # 转 RGB
