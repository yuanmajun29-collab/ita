"""
白纸检测与颜色校准模块

核心思路：在同一张照片中，白纸提供已知反射率参照，
用于校正光照偏差和设备传感器差异。
"""

import cv2
import numpy as np
from typing import Tuple, Optional


class Calibrator:
    """白纸检测与颜色归一化校准器"""

    def __init__(self):
        # 白色区域 HSV 阈值参数
        self.hue_low = 0
        self.hue_high = 180
        self.sat_low = 0
        self.sat_high = 50       # 白纸饱和度很低
        self.val_low = 180       # 白纸亮度较高
        self.val_high = 255

        # 最小白纸面积（图像面积的 0.5%）
        self.min_white_area_ratio = 0.005

        # 中间亮度采样范围（排除极端像素）
        self.brightness_percentile_low = 20
        self.brightness_percentile_high = 80

    def detect_white_region(self, image: np.ndarray) -> Tuple[Optional[np.ndarray], dict]:
        """
        自动检测图像中的白纸区域

        参数:
            image: BGR 格式输入图像

        返回:
            (white_mask, info)
            white_mask: 白纸区域的二值掩码，未检测到则为 None
            info: 检测信息字典
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # 构建白色区域掩码
        mask = cv2.inRange(
            hsv,
            np.array([self.hue_low, self.sat_low, self.val_low]),
            np.array([self.hue_high, self.sat_high, self.val_high])
        )

        # 形态学操作：去噪 + 填充
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

        # 找到最大连通区域（通常是白纸）
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)

        if num_labels <= 1:
            return None, {
                "detected": False,
                "reason": "未检测到白纸区域，请确保照片中包含白色A4纸"
            }

        # 排除背景标签(0)，找面积最大的连通区域
        stats[0, cv2.CC_STAT_AREA] = 0  # 忽略背景
        max_label = np.argmax(stats[:, cv2.CC_STAT_AREA])
        max_area = stats[max_label, cv2.CC_STAT_AREA]

        # 检查面积是否足够
        min_area = image.shape[0] * image.shape[1] * self.min_white_area_ratio
        if max_area < min_area:
            return None, {
                "detected": False,
                "reason": f"检测到的白色区域过小({max_area}px)，请确保白纸完整可见"
            }

        # 提取白纸掩码
        white_mask = (labels == max_label).astype(np.uint8) * 255

        # 计算白纸区域统计信息
        white_pixels = image[white_mask == 255]
        mean_rgb = np.mean(white_pixels, axis=0).tolist()
        std_rgb = np.std(white_pixels, axis=0).tolist()

        return white_mask, {
            "detected": True,
            "area_ratio": max_area / (image.shape[0] * image.shape[1]),
            "mean_rgb": mean_rgb,
            "std_rgb": std_rgb,
            "center": centroids[max_label].tolist()
        }

    def get_white_reference(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        从白纸掩码中提取参考白色（排除极端像素）

        参数:
            image: BGR 格式图像
            mask: 白纸区域掩码

        返回:
            mean_rgb: 白纸区域中间亮度像素的平均 RGB 值 [B, G, R]
        """
        white_pixels = image[mask == 255]

        # 计算每个像素的亮度
        gray = cv2.cvtColor(white_pixels.reshape(-1, 1, 3).astype(np.uint8), cv2.COLOR_BGR2GRAY)
        gray = gray.flatten()

        # 取中间亮度范围的像素
        p_low = np.percentile(gray, self.brightness_percentile_low)
        p_high = np.percentile(gray, self.brightness_percentile_high)
        valid_mask = (gray >= p_low) & (gray <= p_high)

        valid_pixels = white_pixels[valid_mask]

        if len(valid_pixels) < 10:
            # 回退到全部白纸像素
            return np.mean(white_pixels, axis=0)

        return np.mean(valid_pixels, axis=0)

    def calibrate(self, image: np.ndarray, skin_rgb: np.ndarray,
                  mask: Optional[np.ndarray] = None) -> Tuple[np.ndarray, dict]:
        """
        基于白纸校准皮肤颜色

        参数:
            image: BGR 格式图像
            skin_rgb: 皮肤区域平均 RGB 值 [B, G, R]
            mask: 白纸掩码（可选，为 None 时自动检测）

        返回:
            (normalized_rgb, calib_info)
            normalized_rgb: 校准后的 RGB 值 [0-255]
            calib_info: 校准信息
        """
        # 检测或使用提供的白纸掩码
        if mask is None:
            mask, detect_info = self.detect_white_region(image)
            if mask is None:
                return skin_rgb, {
                    "success": False,
                    "reason": detect_info.get("reason", "未检测到白纸"),
                    "normalized": False
                }
        else:
            detect_info = {"detected": True, "manual_mask": True}

        # 获取白纸参考色
        white_ref = self.get_white_reference(image, mask)

        # 避免除零，加微小偏移
        white_ref_safe = np.maximum(white_ref, 1.0)

        # 归一化：皮肤颜色相对于白纸的位置
        normalized = (skin_rgb / white_ref_safe) * 255.0
        normalized = np.clip(normalized, 0, 255)

        return normalized, {
            "success": True,
            "normalized": True,
            "white_reference": white_ref.tolist(),
            "white_mean": detect_info.get("mean_rgb"),
            "skin_raw": skin_rgb.tolist(),
            "skin_normalized": normalized.tolist()
        }
