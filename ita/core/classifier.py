"""
肤色分类器

基于 ITA° 值进行肤色五分类，
并映射到 Fitzpatrick 皮肤分型。
"""

from typing import Dict


class SkinClassifier:
    """肤色分类器：ITA° → 肤色类别 + Fitzpatrick 分型"""

    # ITA° 分类阈值（参考 Del Bino et al. 及相关文献）
    CATEGORIES = [
        {
            "name": "浅色",
            "ita_min": 55,
            "ita_max": 90,
            "description": "非常白皙的皮肤，容易被晒伤",
            "fitzpatrick": "I-II",
            "color_hex": "#FDEBD0"
        },
        {
            "name": "中等色",
            "ita_min": 28,
            "ita_max": 55,
            "description": "白皙到橄榄色，偶尔晒伤但能晒黑",
            "fitzpatrick": "II-III",
            "color_hex": "#F5CBA7"
        },
        {
            "name": "晒黑色",
            "ita_min": 10,
            "ita_max": 28,
            "description": "自然偏棕或日晒后变深",
            "fitzpatrick": "III-IV",
            "color_hex": "#E59866"
        },
        {
            "name": "棕色",
            "ita_min": -30,
            "ita_max": 10,
            "description": "天然棕褐色皮肤，很少晒伤",
            "fitzpatrick": "IV-V",
            "color_hex": "#BA4A00"
        },
        {
            "name": "深色",
            "ita_min": -90,
            "ita_max": -30,
            "description": "深棕色至黑色皮肤，极少晒伤",
            "fitzpatrick": "V-VI",
            "color_hex": "#6E2C00"
        }
    ]

    def __init__(self):
        self.last_category: Dict = None
        self.last_confidence: float = 0.0

    def classify(self, ita: float) -> Dict:
        """
        根据 ITA° 值进行肤色分类

        Args:
            ita: ITA° 角度值

        Returns:
            分类结果字典
        """
        result = {
            "ita": ita,
            "category": None,
            "description": None,
            "fitzpatrick": None,
            "color_hex": None,
            "confidence": 0.0,
            "all_scores": {}
        }

        # 计算每个类别的置信度（基于到类别中心的距离）
        scores = {}
        for cat in self.CATEGORIES:
            center = (cat["ita_min"] + cat["ita_max"]) / 2
            half_range = (cat["ita_max"] - cat["ita_min"]) / 2
            distance = abs(ita - center)

            # 高斯型置信度
            sigma = half_range / 2
            if sigma > 0:
                score = math.exp(-0.5 * (distance / sigma) ** 2)
            else:
                score = 1.0 if distance == 0 else 0.0

            scores[cat["name"]] = round(score, 4)

        # 找到最佳分类
        best_name = max(scores, key=scores.get)
        best_score = scores[best_name]

        for cat in self.CATEGORIES:
            if cat["name"] == best_name:
                result.update({
                    "category": cat["name"],
                    "description": cat["description"],
                    "fitzpatrick": cat["fitzpatrick"],
                    "color_hex": cat["color_hex"],
                    "confidence": best_score
                })
                self.last_category = cat
                break

        result["all_scores"] = scores
        self.last_confidence = best_score

        return result


# 需要导入 math
import math
