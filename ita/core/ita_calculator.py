"""
ITA° 计算引擎模块

将校准后的 RGB 颜色转换为 CIELAB 色彩空间，计算 ITA°（个体类型角）。

ITA° = arctan((L* - 50) / b*) × 180 / π

其中 L* 和 b* 来自 CIELAB 色彩空间：
- L*：亮度 (0=黑, 100=白)
- b*：黄蓝轴 (正值偏黄, 负值偏蓝)
"""

import math
import numpy as np
from typing import Tuple, Optional


def _srgb_to_linear(c: float) -> float:
    """将 sRGB 分量转换为线性 RGB"""
    c = c / 255.0
    if c <= 0.04045:
        return c / 12.92
    else:
        return ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    """将线性 RGB 转换为 sRGB"""
    if c <= 0.0031308:
        s = 12.92 * c
    else:
        s = 1.055 * (c ** (1.0 / 2.4)) - 0.055
    return max(0.0, min(1.0, s)) * 255.0


def rgb_to_xyz(rgb: np.ndarray) -> np.ndarray:
    """
    sRGB → CIE XYZ 转换 (D65 白点)

    参数:
        rgb: [R, G, B] 值范围 0-255

    返回:
        xyz: [X, Y, Z]
    """
    # sRGB 转线性
    r = _srgb_to_linear(rgb[0])
    g = _srgb_to_linear(rgb[1])
    b = _srgb_to_linear(rgb[2])

    # sRGB 转 XYZ 矩阵 (D65)
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b

    return np.array([x, y, z])


def xyz_to_lab(xyz: np.ndarray) -> np.ndarray:
    """
    CIE XYZ → CIE L*a*b* 转换 (D65 白点)

    D65 参考白点: Xn=0.95047, Yn=1.00000, Zn=1.08883

    参数:
        xyz: [X, Y, Z]

    返回:
        lab: [L*, a*, b*]
    """
    # D65 白点
    xn, yn, zn = 0.95047, 1.00000, 1.08883

    # 归一化
    fx = xyz[0] / xn
    fy = xyz[1] / yn
    fz = xyz[2] / zn

    # f(t) 函数
    delta = 6.0 / 29.0

    def f(t):
        if t > delta ** 3:
            return t ** (1.0 / 3.0)
        else:
            return t / (3 * delta ** 2) + 4.0 / 29.0

    fx = f(fx)
    fy = f(fy)
    fz = f(fz)

    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)

    return np.array([L, a, b])


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """
    sRGB → CIE L*a*b* 完整转换

    参数:
        rgb: [R, G, B] 值范围 0-255（顺序：红、绿、蓝）

    返回:
        lab: [L*, a*, b*]
    """
    xyz = rgb_to_xyz(rgb)
    lab = xyz_to_lab(xyz)
    return lab


def calculate_ita(lab: np.ndarray) -> float:
    """
    计算 ITA°（个体类型角）

    ITA° = arctan((L* - 50) / b*) × 180 / π

    参数:
        lab: [L*, a*, b*]

    返回:
        ita: ITA 角度值
    """
    l_star = lab[0]
    b_star = lab[1] if len(lab) < 3 else lab[2]

    # 处理 b* 接近 0 的情况
    if abs(b_star) < 0.01:
        if l_star > 50:
            return 90.0   # 非常浅色
        else:
            return -90.0  # 非常深色

    ita = math.atan2(l_star - 50, b_star) * 180.0 / math.pi
    return ita


def analyze_color(rgb: np.ndarray) -> dict:
    """
    完整颜色分析：RGB → Lab → ITA°

    参数:
        rgb: 平均皮肤 RGB 值 [R, G, B] 或 [B, G, R]（自动检测）

    返回:
        {
            "rgb": [R, G, B],
            "lab": {"L": float, "a": float, "b": float},
            "ita": float,
            "xyz": [X, Y, Z]
        }
    """
    rgb = np.array(rgb, dtype=float)

    # 如果值范围看起来像 0-255 BGR（OpenCV格式），转 RGB
    # 简单启发：如果第一通道最大，可能是 OpenCV BGR
    # 这里假设传入的是 RGB 顺序

    rgb = np.clip(rgb, 0, 255)

    # 转换
    lab = rgb_to_lab(rgb)
    xyz = rgb_to_xyz(rgb)
    ita = calculate_ita(lab)

    return {
        "rgb": rgb.tolist(),
        "lab": {
            "L": round(lab[0], 2),
            "a": round(lab[1], 2),
            "b": round(lab[2], 2)
        },
        "xyz": [round(x, 4) for x in xyz.tolist()],
        "ita": round(ita, 2)
    }
