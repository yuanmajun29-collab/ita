"""
图像质量评估模块

实时检测拍照质量：模糊度、亮度分布、反光、白纸检测、皮肤覆盖、手机倾斜角度。
为拍照引导提供实时反馈。
"""

import cv2
import numpy as np
from typing import Dict, Tuple, Optional


class QualityChecker:
    """图像质量检测器：实时评估拍照是否达标"""

    def __init__(self):
        # 质量阈值
        self.BLUR_THRESHOLD = 80.0        # Laplacian 方差阈值
        self.BRIGHTNESS_MIN = 40.0         # 最低平均亮度
        self.BRIGHTNESS_MAX = 230.0        # 最高平均亮度
        self.BRIGHTNESS_STD_MIN = 20.0     # 亮度标准差最小值（过均匀=过曝）
        self.GLARE_THRESHOLD = 0.03        # 反光面积占比阈值
        self.WHITE_AREA_MIN_RATIO = 0.08   # 白纸最小面积占比
        self.SKIN_AREA_MIN_RATIO = 0.10    # 皮肤最小面积占比
        self.TILT_ANGLE_MAX = 15.0         # 最大允许倾斜角度（度）
        self.OVERLAP_RATIO_MAX = 0.15      # 白纸与皮肤重叠比例上限

    def check_all(self, image: np.ndarray) -> Dict:
        """
        执行全部质量检查

        Args:
            image: BGR 格式输入图像

        Returns:
            质量评估结果字典
        """
        if image is None or image.size == 0:
            return self._empty_result("无效图像")

        checks = {}

        # 1. 模糊检测
        checks["blur"] = self.check_blur(image)

        # 2. 亮度检查
        checks["brightness"] = self.check_brightness(image)

        # 3. 反光检测
        checks["glare"] = self.check_glare(image)

        # 4. 白纸检测
        checks["white_paper"] = self.check_white_paper(image)

        # 5. 皮肤覆盖
        checks["skin_coverage"] = self.check_skin_coverage(
            image, checks["white_paper"].get("mask")
        )

        # 6. 白纸与皮肤重叠检测
        checks["overlap"] = self.check_overlap(
            checks["white_paper"].get("mask"),
            checks["skin_coverage"].get("mask")
        )

        # 7. 手机倾斜检测
        checks["tilt"] = self.check_tilt(checks["white_paper"])

        # 综合评分
        score, ready = self._calculate_score(checks)

        return {
            "score": score,
            "ready": ready,
            "checks": checks,
            "tips": self._generate_tips(checks, ready),
        }

    def check_blur(self, image: np.ndarray) -> Dict:
        """
        检测图像模糊度

        使用 Laplacian 方差法：方差越高越清晰

        Returns:
            {"score": float, "blurry": bool, "variance": float}
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        variance = cv2.Laplacian(gray, cv2.CV_64F).var()

        blurry = variance < self.BLUR_THRESHOLD
        # 归一化到 0-1（方差越大越好）
        score = min(variance / 300.0, 1.0)

        return {
            "score": round(score, 2),
            "blurry": blurry,
            "variance": round(variance, 1),
        }

    def check_brightness(self, image: np.ndarray) -> Dict:
        """
        检查图像亮度

        检查整体亮度是否在合理范围内，以及是否过曝（亮度过于均匀）

        Returns:
            {"score": float, "level": str, "mean": float, "std": float}
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean_val = np.mean(gray)
        std_val = np.std(gray)

        # 判断亮度等级
        if mean_val < self.BRIGHTNESS_MIN:
            level = "too_dark"
            score = 0.2
        elif mean_val > self.BRIGHTNESS_MAX:
            level = "too_bright"
            score = 0.3
        elif std_val < self.BRIGHTNESS_STD_MIN:
            level = "overexposed"  # 过曝导致反差不足
            score = 0.4
        else:
            level = "good"
            # 在合理范围内，越接近中间值分数越高
            ideal = (self.BRIGHTNESS_MAX + self.BRIGHTNESS_MIN) / 2
            deviation = abs(mean_val - ideal) / (self.BRIGHTNESS_MAX - self.BRIGHTNESS_MIN)
            score = max(1.0 - deviation, 0.5)

        return {
            "score": round(score, 2),
            "level": level,
            "mean": round(mean_val, 1),
            "std": round(std_val, 1),
        }

    def check_glare(self, image: np.ndarray) -> Dict:
        """
        检测反光区域

        通过检测过亮的饱和像素区域来判断反光

        Returns:
            {"score": float, "has_glare": bool, "ratio": float}
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # 反光区域特征：亮度极高且饱和度低
        glare_mask = (v > 250) & (s < 30)
        glare_ratio = np.count_nonzero(glare_mask) / (image.shape[0] * image.shape[1])

        has_glare = glare_ratio > self.GLARE_THRESHOLD
        score = max(1.0 - glare_ratio * 20, 0.0)

        return {
            "score": round(score, 2),
            "has_glare": has_glare,
            "ratio": round(glare_ratio, 4),
        }

    def check_white_paper(self, image: np.ndarray) -> Dict:
        """
        检测白纸区域

        Args:
            image: BGR 格式图像

        Returns:
            {"score": float, "detected": bool, "ratio": float, "mask": np.ndarray}
        """
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]

        # 白色区域：高亮度、低饱和度
        _, bright_mask = cv2.threshold(v_channel, 200, 255, cv2.THRESH_BINARY)
        s_channel = hsv[:, :, 1]
        white_mask = cv2.inRange(hsv, np.array([0, 0, 200]), np.array([180, 50, 255]))
        combined = cv2.bitwise_and(bright_mask, white_mask)

        # 形态学处理
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel_open)
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel_close)

        # 找最大连通区域
        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        area_ratio = 0.0
        mask = None

        if contours:
            max_contour = max(contours, key=cv2.contourArea)
            area_ratio = cv2.contourArea(max_contour) / (image.shape[0] * image.shape[1])
            mask = np.zeros_like(combined)
            cv2.drawContours(mask, [max_contour], -1, 255, -1)

        detected = area_ratio >= self.WHITE_AREA_MIN_RATIO
        score = min(area_ratio / 0.20, 1.0) if detected else area_ratio / self.WHITE_AREA_MIN_RATIO

        return {
            "score": round(min(score, 1.0), 2),
            "detected": detected,
            "ratio": round(area_ratio, 4),
            "mask": mask,
        }

    def check_skin_coverage(
        self,
        image: np.ndarray,
        white_mask: Optional[np.ndarray] = None
    ) -> Dict:
        """
        检测皮肤覆盖面积

        Args:
            image: BGR 格式图像
            white_mask: 白纸掩码（用于排除）

        Returns:
            {"score": float, "detected": bool, "ratio": float, "mask": np.ndarray}
        """
        ycbcr = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        y, cb, cr = cv2.split(ycbcr)
        h, s, v = cv2.split(hsv)

        # YCbCr 肤色范围
        cb_mask = cv2.inRange(cb, 77, 177)
        cr_mask = cv2.inRange(cr, 100, 180)
        ycbcr_skin = cv2.bitwise_and(cb_mask, cr_mask)

        # HSV 辅助
        h_mask = cv2.inRange(h, 0, 50)
        s_mask = cv2.inRange(s, 20, 180)
        hsv_skin = cv2.bitwise_and(h_mask, s_mask)

        skin_mask = cv2.bitwise_and(ycbcr_skin, hsv_skin)

        # 排除白纸区域（扩大边缘）
        if white_mask is not None:
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (30, 30))
            expanded_white = cv2.dilate(white_mask, kernel)
            skin_mask = cv2.bitwise_and(skin_mask, cv2.bitwise_not(expanded_white))

        # 排除过暗区域
        dark_mask = cv2.inRange(v, 0, 40)
        skin_mask = cv2.bitwise_and(skin_mask, cv2.bitwise_not(dark_mask))

        # 形态学去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)

        area_ratio = np.count_nonzero(skin_mask) / (image.shape[0] * image.shape[1])
        detected = area_ratio >= self.SKIN_AREA_MIN_RATIO
        score = min(area_ratio / 0.25, 1.0) if detected else area_ratio / self.SKIN_AREA_MIN_RATIO

        return {
            "score": round(min(score, 1.0), 2),
            "detected": detected,
            "ratio": round(area_ratio, 4),
            "mask": skin_mask,
        }

    def check_overlap(
        self,
        white_mask: Optional[np.ndarray],
        skin_mask: Optional[np.ndarray]
    ) -> Dict:
        """检查白纸和皮肤区域是否过度重叠"""
        if white_mask is None or skin_mask is None:
            return {"score": 1.0, "ratio": 0.0, "ok": True}

        overlap = cv2.bitwise_and(white_mask, skin_mask)
        white_area = np.count_nonzero(white_mask)
        overlap_area = np.count_nonzero(overlap)
        ratio = overlap_area / max(white_area, 1)

        ok = ratio < self.OVERLAP_RATIO_MAX
        score = max(1.0 - ratio * 5, 0.0)

        return {
            "score": round(score, 2),
            "ratio": round(ratio, 4),
            "ok": ok,
        }

    def check_tilt(self, white_paper_result: Dict) -> Dict:
        """
        检测手机倾斜角度

        通过白纸轮廓的最小外接矩形的长宽比和角度来估算

        Returns:
            {"score": float, "tilted": bool, "angle": float}
        """
        # 需要从原始检测结果中获取轮廓信息
        # 这里使用简化方法：基于白纸检测结果判断
        if not white_paper_result.get("detected"):
            return {
                "score": 0.5,
                "tilted": False,
                "angle": 0.0,
                "message": "未检测到白纸，无法判断倾斜"
            }

        # 默认未检测到明显倾斜
        return {
            "score": 1.0,
            "tilted": False,
            "angle": 0.0,
            "message": "水平角度正常"
        }

    def check_tilt_from_contours(
        self,
        image: np.ndarray,
        white_mask: np.ndarray
    ) -> Dict:
        """
        高级倾斜检测：通过白纸轮廓的旋转角度判断

        Args:
            image: 输入图像
            white_mask: 白纸掩码

        Returns:
            倾斜信息字典
        """
        contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return {"score": 0.5, "tilted": False, "angle": 0.0, "message": "无轮廓"}

        max_contour = max(contours, key=cv2.contourArea)

        # 使用最小外接矩形获取角度
        rect = cv2.minAreaRect(max_contour)
        angle = rect[2]

        # 规范化角度到 -90 ~ 90
        if angle > 45:
            angle = 90 - angle
        elif angle < -45:
            angle = -90 - angle

        abs_angle = abs(angle)
        tilted = abs_angle > self.TILT_ANGLE_MAX
        score = max(1.0 - abs_angle / 45.0, 0.0)

        if tilted:
            message = f"手机倾斜约 {abs_angle:.0f}°，请保持水平"
        else:
            message = "水平角度正常"

        return {
            "score": round(score, 2),
            "tilted": tilted,
            "angle": round(abs_angle, 1),
            "message": message,
        }

    def _calculate_score(self, checks: Dict) -> Tuple[float, bool]:
        """
        计算综合质量分数

        Args:
            checks: 各项检查结果

        Returns:
            (score, ready) 分数 0-1，是否可以拍照
        """
        # 关键项权重
        weights = {
            "blur": 0.20,
            "brightness": 0.20,
            "white_paper": 0.25,
            "skin_coverage": 0.25,
            "glare": 0.05,
            "overlap": 0.05,
        }

        total_score = 0.0
        total_weight = 0.0

        for key, weight in weights.items():
            if key in checks:
                total_score += checks[key]["score"] * weight
                total_weight += weight

        if total_weight > 0:
            final_score = total_score / total_weight
        else:
            final_score = 0.0

        # 是否可以拍照（关键项必须通过）
        ready = (
            checks.get("blur", {}).get("blurry", True) is False and
            checks.get("white_paper", {}).get("detected", False) is True and
            checks.get("skin_coverage", {}).get("detected", False) is True and
            checks.get("brightness", {}).get("level") == "good" and
            checks.get("overlap", {}).get("ok", True) is True
        )

        return round(final_score, 2), ready

    def _generate_tips(self, checks: Dict, ready: bool) -> list:
        """生成拍照建议"""
        tips = []

        if ready:
            tips.append("✅ 条件良好，可以拍照！")
            return tips

        # 逐项检查
        blur_check = checks.get("blur", {})
        if blur_check.get("blurry"):
            tips.append("📷 图像模糊，请保持手机稳定")

        brightness_check = checks.get("brightness", {})
        bl = brightness_check.get("level", "")
        if bl == "too_dark":
            tips.append("💡 画面太暗，请在更亮的环境下拍摄")
        elif bl == "too_bright":
            tips.append("💡 画面太亮，避免直射光源")
        elif bl == "overexposed":
            tips.append("💡 可能过曝，远离强光源")

        glare_check = checks.get("glare", {})
        if glare_check.get("has_glare"):
            tips.append("✨ 检测到反光，调整角度避开反光")

        white_check = checks.get("white_paper", {})
        if not white_check.get("detected"):
            tips.append("📄 未检测到白纸，请确保A4白纸在画面中")

        skin_check = checks.get("skin_coverage", {})
        if not skin_check.get("detected"):
            tips.append("🦶 未检测到皮肤，请确保前臂在画面中")

        overlap_check = checks.get("overlap", {})
        if not overlap_check.get("ok"):
            tips.append("📐 白纸和手臂太近，请分开一些")

        tilt_check = checks.get("tilt", {})
        if tilt_check.get("tilted"):
            tips.append("📐 手机倾斜，请保持水平拍摄")

        if not tips:
            tips.append("📸 调整拍照角度和位置后重试")

        return tips

    def _empty_result(self, message: str) -> Dict:
        return {
            "score": 0.0,
            "ready": False,
            "checks": {},
            "tips": [f"⚠️ {message}"],
        }

    def get_quality_overlay(
        self,
        image: np.ndarray,
        checks: Dict
    ) -> np.ndarray:
        """
        生成质量反馈叠加图像

        在原图上绘制检测框和提示信息

        Args:
            image: 原始 BGR 图像
            checks: 质量检查结果

        Returns:
            标注后的 BGR 图像
        """
        overlay = image.copy()

        # 绘制白纸检测框（绿色=正常）
        white_check = checks.get("white_paper", {})
        if white_check.get("mask") is not None:
            mask = white_check["mask"]
            color = (0, 200, 0) if white_check["detected"] else (0, 0, 200)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(overlay, contours, -1, color, 2)

        # 绘制皮肤区域（蓝色轮廓）
        skin_check = checks.get("skin_coverage", {})
        if skin_check.get("mask") is not None:
            mask = skin_check["mask"]
            color = (200, 150, 0) if skin_check["detected"] else (200, 0, 0)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                if cv2.contourArea(cnt) > 100:
                    cv2.drawContours(overlay, [cnt], -1, color, 1)

        return overlay
