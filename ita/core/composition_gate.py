"""
构图门禁：未识别到 A4 白纸或符合要求的前臂时仅返回提示，不进入校准与 ITA 分析。
"""

from __future__ import annotations

from typing import Optional

NOTE_NO_ANALYSIS = "本图不进行肤色分析。"


def note_no_analysis(message: str) -> str:
    """为错误提示附加「不进行肤色分析」说明（已包含则原样返回）。"""
    if not message or not message.strip():
        return NOTE_NO_ANALYSIS
    m = message.strip()
    if NOTE_NO_ANALYSIS in m:
        return m
    return f"{m}，{NOTE_NO_ANALYSIS}"


# 无 A4、且未检测到皮肤掩码（画面内无可用肤色区域）
MSG_NEITHER_PAPER_NOR_ARM = (
    "未检测到A4白纸与可用皮肤区域，请将A4白纸与伸展的前臂一并拍入画面；"
    "本图不进行肤色分析。"
)

# 无 A4，但有肤色区域、前臂启发式未通过（与「两者皆无」区分）
MSG_NO_PAPER_SKIN_NOT_FOREARM = (
    "未检测到A4白纸。画面中虽有肤色区域，但未识别为符合要求的伸展前臂；"
    "请补拍白纸并调整构图；本图不进行肤色分析。"
)

MSG_NO_PAPER = (
    "未检测到白纸区域，请确保照片中包含A4白纸；"
    "未识别到可用于校准的A4参考，本图不进行肤色分析。"
)

MSG_NO_SKIN = (
    "未检测到皮肤区域，请确保手臂清晰可见；"
    "未识别到符合要求的前臂，本图不进行肤色分析。"
)


def early_exit_message(
    *,
    has_white_paper: bool,
    skin_mask_present: bool,
    arm_ok: bool,
    arm_msg: str,
) -> Optional[str]:
    """
    在 calibrate / ITA 之前调用。

    Returns:
        若非 None，应直接返回给客户端并不再执行后续分析。
        None 表示应继续执行校准与完整流水线。
    """
    if not has_white_paper and not arm_ok:
        if skin_mask_present:
            return MSG_NO_PAPER_SKIN_NOT_FOREARM
        return MSG_NEITHER_PAPER_NOR_ARM
    if not has_white_paper and arm_ok:
        return MSG_NO_PAPER
    if has_white_paper and not arm_ok:
        if not skin_mask_present:
            return MSG_NO_SKIN
        return note_no_analysis(arm_msg) if arm_msg else MSG_NO_SKIN
    return None
