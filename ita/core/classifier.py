"""
肤色分类器模块

基于 ITA° 值将肤色分为五个类别，并关联 Fitzpatrick 分型。

ITA° 分类标准（参考医学文献）：
- 浅色：ITA° > 55°
- 中等色：ITA° 28° ~ 55°
- 晒黑色：ITA° 10° ~ 28°
- 棕色：ITA° -30° ~ 10°
- 深色：ITA° < -30°
"""

from typing import Tuple


# 肤色分类定义
SKIN_CATEGORIES = [
    {
        "id": "very_light",
        "name": "浅色",
        "ita_min": 55,
        "ita_max": 180,
        "description": "非常白皙的肤色，容易晒伤",
        "fitzpatrick": ["I", "II"],
        "uv_advice": "皮肤对紫外线非常敏感，外出请做好充分防晒（SPF50+），限制日晒时间。",
        "color": "#FFDFC4"
    },
    {
        "id": "medium",
        "name": "中等色",
        "ita_min": 28,
        "ita_max": 55,
        "description": "白皙到橄榄色，适度日晒会变棕",
        "fitzpatrick": ["II", "III"],
        "uv_advice": "皮肤对紫外线较敏感，建议使用 SPF30+ 防晒，可适度日光照射补充维D。",
        "color": "#F0C8A0"
    },
    {
        "id": "tanned",
        "name": "晒黑色",
        "ita_min": 10,
        "ita_max": 28,
        "description": "日晒后偏棕，不易晒伤",
        "fitzpatrick": ["III", "IV"],
        "uv_advice": "皮肤有一定耐受性，仍建议 SPF15+ 防晒，适合短时间日光浴。",
        "color": "#D4A574"
    },
    {
        "id": "brown",
        "name": "棕色",
        "ita_min": -30,
        "ita_max": 10,
        "description": "天然棕褐色，不易晒伤",
        "fitzpatrick": ["IV", "V"],
        "uv_advice": "皮肤对紫外线较耐受，日常防晒 SPF15 即可，自然光照可充分补充维D。",
        "color": "#A0724A"
    },
    {
        "id": "dark",
        "name": "深色",
        "ita_min": -180,
        "ita_max": -30,
        "description": "深棕色至黑色，极少晒伤",
        "fitzpatrick": ["V", "VI"],
        "uv_advice": "皮肤对紫外线耐受性较强，但仍需适当防护。注意检查皮肤有无异常变化。",
        "color": "#6B4226"
    }
]


def classify_skin(ita: float) -> dict:
    """
    根据 ITA° 值进行肤色分类

    参数:
        ita: ITA 角度值

    返回:
        {
            "ita": float,
            "category_id": str,
            "category_name": str,
            "description": str,
            "fitzpatrick": list,
            "uv_advice": str,
            "color": str,
            "confidence": float
        }
    """
    for cat in SKIN_CATEGORIES:
        if cat["ita_min"] <= ita < cat["ita_max"]:
            # 计算置信度：越接近类别中心，置信度越高
            center = (cat["ita_min"] + cat["ita_max"]) / 2
            half_range = (cat["ita_max"] - cat["ita_min"]) / 2
            distance = abs(ita - center)
            confidence = max(0.5, 1.0 - (distance / half_range) * 0.5)
            confidence = round(confidence, 2)

            return {
                "ita": ita,
                "category_id": cat["id"],
                "category_name": cat["name"],
                "description": cat["description"],
                "fitzpatrick": cat["fitzpatrick"],
                "uv_advice": cat["uv_advice"],
                "color": cat["color"],
                "confidence": confidence
            }

    # 边界情况
    if ita >= 180:
        cat = SKIN_CATEGORIES[0]
    else:
        cat = SKIN_CATEGORIES[-1]

    return {
        "ita": ita,
        "category_id": cat["id"],
        "category_name": cat["name"],
        "description": cat["description"],
        "fitzpatrick": cat["fitzpatrick"],
        "uv_advice": cat["uv_advice"],
        "color": cat["color"],
        "confidence": 0.5
    }


def get_all_categories() -> list:
    """获取所有肤色分类信息"""
    return [
        {
            "id": cat["id"],
            "name": cat["name"],
            "ita_range": f"{cat['ita_min']}° ~ {cat['ita_max']}°",
            "description": cat["description"],
            "fitzpatrick": cat["fitzpatrick"],
            "color": cat["color"]
        }
        for cat in SKIN_CATEGORIES
    ]
