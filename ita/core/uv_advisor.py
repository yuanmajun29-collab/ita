"""
紫外线指数与维D照射建议模块

基于用户肤色的 Fitzpatrick 分型和实时 UV 指数，
提供个性化的维生素D合成建议。
"""

import math
from typing import Dict, Optional
from datetime import datetime

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


# Fitzpatrick 分型对应的 MED（最小红斑剂量，单位：J/m²）和 SPF 建议时间
FITZPATRICK_DATA = {
    "I": {
        "name": "极白皙",
        "med_minutes": 15,      # 不涂防晒霜情况下晒红的时间（分钟）
        "spf_recommended": "SPF 50+",
        "max_safe_minutes": 10,  # 建议最大无防护日照时间
        "vitd_efficiency": 1.0,  # 维D合成效率系数（越高越容易合成）
    },
    "II": {
        "name": "白皙",
        "med_minutes": 20,
        "spf_recommended": "SPF 50",
        "max_safe_minutes": 15,
        "vitd_efficiency": 0.95,
    },
    "III": {
        "name": "中等",
        "med_minutes": 25,
        "spf_recommended": "SPF 30",
        "max_safe_minutes": 20,
        "vitd_efficiency": 0.85,
    },
    "IV": {
        "name": "偏棕",
        "med_minutes": 30,
        "spf_recommended": "SPF 30",
        "max_safe_minutes": 25,
        "vitd_efficiency": 0.70,
    },
    "V": {
        "name": "深棕",
        "med_minutes": 40,
        "spf_recommended": "SPF 15",
        "max_safe_minutes": 30,
        "vitd_efficiency": 0.55,
    },
    "VI": {
        "name": "极深",
        "med_minutes": 50,
        "spf_recommended": "SPF 15",
        "max_safe_minutes": 40,
        "vitd_efficiency": 0.40,
    },
}


# UV 指数等级描述
UV_LEVELS = {
    (0, 2): {"level": "低", "color": "#4CAF50", "danger": "安全", "advice": "无需特别防护"},
    (3, 5): {"level": "中等", "color": "#FFC107", "danger": "注意", "advice": "建议使用防晒霜"},
    (6, 7): {"level": "高", "color": "#FF9800", "danger": "危险", "advice": "减少户外暴晒，使用SPF30+"},
    (8, 10): {"level": "很高", "color": "#F44336", "danger": "很危险", "advice": "避免正午外出，使用SPF50+"},
    (11, 20): {"level": "极高", "color": "#9C27B0", "danger": "极危险", "advice": "尽量待在室内"},
}


class UVAdvisor:
    """UV 指数获取与维D照射建议"""

    def __init__(self, weather_api_key: Optional[str] = None):
        """
        初始化

        Args:
            weather_api_key: OpenWeatherMap API Key（可选）
        """
        self.weather_api_key = weather_api_key
        self.last_uv: Optional[float] = None
        self.last_location: Optional[str] = None

    def get_uv_level_info(self, uv_index: float) -> Dict:
        """
        获取 UV 指数等级信息

        Args:
            uv_index: UV 指数值

        Returns:
            等级信息字典
        """
        for (low, high), info in UV_LEVELS.items():
            if low <= uv_index <= high:
                return {
                    "uv_index": uv_index,
                    "level": info["level"],
                    "color": info["color"],
                    "danger": info["danger"],
                    "advice": info["advice"]
                }

        # UV > 20 极端情况
        return {
            "uv_index": uv_index,
            "level": "极端",
            "color": "#9C27B0",
            "danger": "极端危险",
            "advice": "绝对避免日晒"
        }

    def map_fitzpatrick(self, fitzpatrick_str: str) -> Optional[str]:
        """
        将分类结果中的 Fitzpatrick 字符串映射到标准分型编号

        Args:
            fitzpatrick_str: 如 "I-II", "II-III" 等

        Returns:
            分型编号，如 "II"
        """
        # 提取第一个罗马数字
        roman_map = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6}

        parts = fitzpatrick_str.replace(" ", "").split("-")
        if not parts:
            return None

        first = parts[0].upper()
        return first if first in roman_map else None

    def calculate_vitd_advice(
        self,
        ita: float,
        fitzpatrick: str,
        uv_index: float,
        exposure_time_minutes: Optional[float] = None
    ) -> Dict:
        """
        计算维D合成建议

        Args:
            ita: ITA° 值
            fitzpatrick: Fitzpatrick 分型字符串
            uv_index: 当前 UV 指数
            exposure_time_minutes: 用户计划照射时间（可选）

        Returns:
            维D建议字典
        """
        fp_type = self.map_fitzpatrick(fitzpatrick)
        if fp_type is None:
            fp_type = "III"  # 默认中等

        fp_data = FITZPATRICK_DATA.get(fp_type, FITZPATRICK_DATA["III"])
        uv_info = self.get_uv_level_info(uv_index)

        # 计算建议照射时间（分钟）
        # 基于公式：建议时间 ≈ MED × 维D效率系数 / UV指数调整因子
        # UV 指数调整因子：UV 6 时为标准，其他按比例
        uv_factor = max(uv_index / 6.0, 0.3)
        base_time = fp_data["med_minutes"] * fp_data["vitd_efficiency"]

        # 维D最佳合成时间（皮肤科建议约 1/4 到 1/2 MED 时间）
        vitd_optimal_min = max(round(base_time * 0.25 / uv_factor), 3)
        vitd_optimal_max = max(round(base_time * 0.5 / uv_factor), 5)

        # 安全上限（不超过 MED 的 60%）
        safe_max = max(round(fp_data["max_safe_minutes"] / uv_factor), 5)

        # 维D合成量估算（基于 Holick 2007 研究）
        # 全身暴露在 UV 3-5 下 15-30 分钟可产生约 10000-25000 IU 维D
        # 根据肤色、UV、暴露面积估算
        exposure_area_factor = 0.25  # 假设暴露前臂面积约全身 25%
        base_iu_per_min = 500 * uv_factor * fp_data["vitd_efficiency"]
        vitd_at_optimal_min = round(base_iu_per_min * vitd_optimal_min * exposure_area_factor)
        vitd_at_optimal_max = round(base_iu_per_min * vitd_optimal_max * exposure_area_factor)

        # 每日建议摄入量参考
        daily_target = 1000  # WHO 建议成人每日 1000 IU
        achieving_pct = min(round(vitd_at_optimal_max / daily_target * 100), 100)

        result = {
            "uv": uv_info,
            "fitzpatrick_type": fp_type,
            "fitzpatrick_name": fp_data["name"],
            "spf_recommended": fp_data["spf_recommended"],
            "vitd": {
                "optimal_time_range": f"{vitd_optimal_min}-{vitd_optimal_max} 分钟",
                "optimal_min_minutes": vitd_optimal_min,
                "optimal_max_minutes": vitd_optimal_max,
                "safe_max_minutes": safe_max,
                "estimated_iu_range": f"{vitd_at_optimal_min}-{vitd_at_optimal_max} IU",
                "estimated_iu_min": vitd_at_optimal_min,
                "estimated_iu_max": vitd_at_optimal_max,
                "daily_target_iu": daily_target,
                "achieving_pct": achieving_pct,
            },
            "recommendations": self._generate_recommendations(
                uv_info, fp_data, vitd_optimal_min, vitd_optimal_max, achieving_pct
            )
        }

        # 如果用户指定了照射时间，计算预估
        if exposure_time_minutes is not None:
            result["user_exposure"] = self._estimate_exposure(
                exposure_time_minutes, fp_data, uv_index, base_iu_per_min, exposure_area_factor
            )

        return result

    def _generate_recommendations(
        self,
        uv_info: Dict,
        fp_data: Dict,
        vitd_min: int,
        vitd_max: int,
        achieving_pct: int
    ) -> list:
        """生成个性化建议列表"""
        recommendations = []

        # UV 安全建议
        if uv_info["uv_index"] >= 8:
            recommendations.append("⚠️ 当前紫外线极强，建议避免正午时段（10:00-15:00）外出")
            recommendations.append(f"🧴 如需外出，请使用 {fp_data['spf_recommended']} 防晒霜")
        elif uv_info["uv_index"] >= 6:
            recommendations.append("☀️ 当前紫外线较强，建议缩短日照时间")
            recommendations.append(f"🧴 建议使用 {fp_data['spf_recommended']} 防晒霜")
        elif uv_info["uv_index"] >= 3:
            recommendations.append("🌤️ 当前紫外线适中，是适当的日照时间")
            recommendations.append(f"🧴 建议使用 {fp_data['spf_recommended']} 防晒霜")
        else:
            recommendations.append("🌤️ 当前紫外线较弱，适合较长时间户外活动")
            recommendations.append("💡 但维D合成效率也较低")

        # 维D合成建议
        recommendations.append(
            f"⏱️ 建议日照时间：{vitd_min}-{vitd_max} 分钟（暴露前臂/面部）"
        )

        if achieving_pct >= 80:
            recommendations.append("✅ 此照射时间可满足大部分每日维D需求")
        elif achieving_pct >= 50:
            recommendations.append("📊 此照射时间可满足约一半每日维D需求，建议结合饮食补充")
        else:
            recommendations.append("💡 当前UV较低，建议通过食物或补充剂补充维D")

        # 肤色相关建议
        if fp_data["vitd_efficiency"] < 0.6:
            recommendations.append("📋 深色皮肤人群合成维D效率较低，建议定期检测血清 25(OH)D 水平")

        # 通用建议
        recommendations.append("🍞 建议在上午 10 点前或下午 3 点后进行日照")
        recommendations.append("🐟 可多食用富含维D的食物：三文鱼、蛋黄、强化牛奶")

        return recommendations

    def _estimate_exposure(
        self,
        time_min: float,
        fp_data: Dict,
        uv_index: float,
        base_iu: float,
        area_factor: float
    ) -> Dict:
        """估算指定时间的照射效果"""
        safe_limit = fp_data["max_safe_minutes"]
        vitd_iu = round(base_iu * time_min * area_factor)

        # 判断是否超过安全时间
        if time_min > safe_limit:
            risk = "high"
            risk_desc = f"超过安全时间 {time_min - safe_limit:.0f} 分钟，晒伤风险高"
        elif time_min > safe_limit * 0.7:
            risk = "medium"
            risk_desc = "接近安全上限，建议注意防晒"
        else:
            risk = "low"
            risk_desc = "在安全范围内"

        return {
            "time_minutes": time_min,
            "estimated_iu": vitd_iu,
            "daily_target_achieving": min(round(vitd_iu / 1000 * 100), 100),
            "risk_level": risk,
            "risk_description": risk_desc,
        }

    async def fetch_uv_index(
        self,
        lat: float,
        lon: float
    ) -> Optional[Dict]:
        """
        从 OpenWeatherMap API 获取实时 UV 指数

        Args:
            lat: 纬度
            lon: 经度

        Returns:
            包含 UV 指数等信息的字典，失败返回 None
        """
        if not self.weather_api_key:
            return None

        if not HAS_AIOHTTP:
            return None

        url = "https://api.openweathermap.org/data/2.5/onecall"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": self.weather_api_key,
            "exclude": "minutely,hourly,daily,alerts",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    uv = data.get("current", {}).get("uvi")
                    if uv is not None:
                        self.last_uv = uv
                        return {
                            "uv_index": uv,
                            "location": f"{lat},{lon}",
                            "timestamp": datetime.now().isoformat()
                        }
                    return None
        except Exception:
            return None

    @staticmethod
    def estimate_uv_from_context(month: int, hour: int, latitude: float) -> float:
        """
        根据时间、月份和纬度粗略估算 UV 指数（无 API 时使用）

        Args:
            month: 月份 1-12
            hour: 小时 0-23
            lat: 纬度

        Returns:
            估算的 UV 指数
        """
        # 基于月份的 UV 基础值（北半球中纬度）
        monthly_uv = {
            1: 1.5, 2: 2.5, 3: 4.0, 4: 5.5, 5: 7.0, 6: 8.5,
            7: 9.0, 8: 8.0, 9: 5.5, 10: 3.5, 11: 2.0, 12: 1.5
        }

        base_uv = monthly_uv.get(month, 4.0)

        # 时间修正：正午 UV 最高，早晚低
        # UV 曲线近似正弦分布，12点为峰值
        hour_factor = math.sin(math.pi * (hour - 6) / 12) if 6 <= hour <= 18 else 0.0
        hour_factor = max(hour_factor, 0)

        # 纬度修正：赤道最高，向两极递减
        lat_factor = math.cos(math.radians(latitude))
        lat_factor = max(lat_factor, 0.3)

        estimated_uv = base_uv * hour_factor * lat_factor
        return max(round(estimated_uv, 1), 0)
