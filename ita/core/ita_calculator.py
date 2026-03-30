"""
ITA° 计算引擎

将校准后的 RGB 值转换为 CIELAB 色彩空间，
计算 Individual Typology Angle (ITA°)。
"""

import numpy as np
import math
from typing import Optional, Tuple, Dict


class ITACalculator:
    """ITA° 计算器：RGB → CIELAB → ITA°"""

    # sRGB 线性化阈值
    SRGB_THRESHOLD = 0.04045

    # D65 白点
    D65_WHITE = np.array([0.95047, 1.0, 1.08883])

    def __init__(self):
        self.last_lab: Optional[Tuple[float, float, float]] = None
        self.last_ita: Optional[float] = None
        self.last_rgb_normalized: Optional[Tuple[float, float, float]] = None

    @staticmethod
    def srgb_to_linear(c: float) -> float:
        """将 sRGB 伽马值转换为线性值"""
        if c <= ITACalculator.SRGB_THRESHOLD:
            return c / 12.92
        else:
            return ((c + 0.055) / 1.055) ** 2.4

    @staticmethod
    def linear_to_srgb(c: float) -> float:
        """将线性值转换为 sRGB 伽马值"""
        if c <= 0.0031308:
            return c * 12.92
        else:
            return 1.055 * (c ** (1.0 / 2.4)) - 0.055

    def rgb_to_xyz(self, rgb: Tuple[float, float, float]) -> np.ndarray:
        """
        将 RGB (0-255) 转换为 XYZ 色彩空间

        使用 sRGB 到 XYZ (D65) 的标准转换矩阵

        Args:
            rgb: (R, G, B) 值，范围 0-255

        Returns:
            XYZ 值数组
        """
        # 归一化到 0-1
        r, g, b = rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0

        # 限制范围
        r = max(0.0, min(1.0, r))
        g = max(0.0, min(1.0, g))
        b = max(0.0, min(1.0, b))

        # sRGB 线性化
        r_lin = self.srgb_to_linear(r)
        g_lin = self.srgb_to_linear(g)
        b_lin = self.srgb_to_linear(b)

        # sRGB 到 XYZ 转换矩阵 (D65)
        xyz_matrix = np.array([
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041]
        ])

        rgb_linear = np.array([r_lin, g_lin, b_lin])
        xyz = xyz_matrix @ rgb_linear

        return xyz

    def xyz_to_lab(self, xyz: np.ndarray) -> Tuple[float, float, float]:
        """
        将 XYZ 转换为 CIELAB (D65)

        Args:
            xyz: XYZ 值数组

        Returns:
            (L*, a*, b*) 值
        """
        # 除以白点归一化
        xyz_norm = xyz / self.D65_WHITE

        # f 函数
        delta = 6.0 / 29.0

        def f(t):
            if t > delta ** 3:
                return t ** (1.0 / 3.0)
            else:
                return t / (3 * delta ** 2) + 4.0 / 29.0

        fx, fy, fz = f(xyz_norm[0]), f(xyz_norm[1]), f(xyz_norm[2])

        L = 116.0 * fy - 16.0
        a = 500.0 * (fx - fy)
        b_star = 200.0 * (fy - fz)

        return (L, a, b_star)

    def calculate_ita(self, lab: Tuple[float, float, float]) -> float:
        """
        计算 ITA° (Individual Typology Angle)

        公式：ITA° = arctan((L* - 50) / b*) × 180 / π

        Args:
            lab: (L*, a*, b*) 值

        Returns:
            ITA° 角度值（度）
        """
        L, a, b_star = lab

        # 处理 b* 接近零的情况（避免除零）
        if abs(b_star) < 0.01:
            if L > 50:
                return 90.0  # 极端浅色
            else:
                return -90.0  # 极端深色

        ita = math.atan2(L - 50, b_star) * 180.0 / math.pi
        return ita

    def analyze(self, rgb_normalized: Tuple[float, float, float]) -> Dict:
        """
        完整分析流程：RGB → XYZ → Lab → ITA°

        Args:
            rgb_normalized: 归一化后的 RGB 值 (0-255)

        Returns:
            分析结果字典，包含 Lab 值和 ITA°
        """
        self.last_rgb_normalized = rgb_normalized

        # RGB → XYZ
        xyz = self.rgb_to_xyz(rgb_normalized)

        # XYZ → Lab
        lab = self.xyz_to_lab(xyz)
        self.last_lab = lab

        # Lab → ITA°
        ita = self.calculate_ita(lab)
        self.last_ita = ita

        return {
            "lab": {
                "L": round(lab[0], 2),
                "a": round(lab[1], 2),
                "b": round(lab[2], 2)
            },
            "ita": round(ita, 2),
            "xyz": {
                "X": round(xyz[0], 4),
                "Y": round(xyz[1], 4),
                "Z": round(xyz[2], 4)
            }
        }
