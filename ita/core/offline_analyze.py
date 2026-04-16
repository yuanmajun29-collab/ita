"""
离线图像分析：与 /api/analyze 相同的核心流水线（无 UV、不写库）。

供 scripts/evaluate_data与 data/ 回归测试复用。
"""

from __future__ import annotations

from ita.core.calibrator import WhitePaperCalibrator
from ita.core.arm_validator import validate_forearm_skin_mask
from ita.core.composition_gate import early_exit_message, note_no_analysis
from ita.core.skin_detector import SkinDetector
from ita.core.ita_calculator import ITACalculator
from ita.core.classifier import SkinClassifier
from ita.core.quality_checker import QualityChecker

IMAGE_SUFFIX = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".webp"})


def analyze_bgr(image) -> dict:
    """对 BGR ndarray 分析：须先识别 A4 与前臂；未通过则仅返回提示，不做校准与 ITA。"""
    out: dict = {"stages": {}}

    calibrator = WhitePaperCalibrator()
    white_mask = calibrator.detect_white_paper(image)
    detector = SkinDetector()
    skin_mask = detector.detect_skin_exclude_white(image, white_mask)

    if skin_mask is None:
        arm_ok, arm_msg = False, ""
    else:
        arm_ok, arm_msg = validate_forearm_skin_mask(skin_mask)

    early = early_exit_message(
        has_white_paper=white_mask is not None,
        skin_mask_present=skin_mask is not None,
        arm_ok=arm_ok,
        arm_msg=arm_msg,
    )
    if early is not None:
        out["success"] = False
        out["message"] = early
        out["stages"]["preflight"] = {
            "has_white_paper": white_mask is not None,
            "arm_ok": arm_ok,
        }
        return out

    cal_result = calibrator.calibrate(image, mask=white_mask)
    out["stages"]["calibration"] = {
        "success": cal_result["success"],
        "message": cal_result.get("message"),
        "white_mean_rgb": cal_result.get("white_mean_rgb"),
    }
    if not cal_result["success"]:
        out["success"] = False
        out["message"] = note_no_analysis(cal_result["message"])
        return out

    skin_rgb = detector.get_skin_mean_rgb(image, skin_mask)
    if skin_rgb is None:
        out["success"] = False
        out["message"] = note_no_analysis("皮肤采样失败")
        out["stages"]["skin"] = {"success": False}
        return out

    normalized_rgb = calibrator.normalize_color(skin_rgb)
    calculator = ITACalculator()
    analysis = calculator.analyze(normalized_rgb)
    classifier = SkinClassifier()
    classification = classifier.classify(analysis["ita"])

    out["success"] = True
    out["message"] = "分析完成"
    out["stages"]["skin"] = {
        "success": True,
        "skin_mean_rgb": list(skin_rgb),
        "normalized_rgb": [round(x, 2) for x in normalized_rgb],
        "skin_area_ratio": round(float(detector.skin_area_ratio), 4),
    }
    out["result"] = {
        "ita": analysis["ita"],
        "lab": analysis["lab"],
        "category": classification["category"],
        "fitzpatrick": classification["fitzpatrick"],
        "confidence": classification["confidence"],
        "description": classification["description"],
    }
    return out


def quality_summary(image) -> dict:
    qc = QualityChecker()
    r = qc.check_all(image)
    checks = r.get("checks") or {}
    slim = {}
    for k, v in checks.items():
        if isinstance(v, dict):
            slim[k] = {kk: vv for kk, vv in v.items() if kk != "mask"}
    return {
        "score": r["score"],
        "ready": r["ready"],
        "tips": r["tips"],
        "checks": slim,
    }
