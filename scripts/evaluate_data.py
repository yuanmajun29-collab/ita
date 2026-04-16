"""
对指定目录中的测试图像批量运行肤色分析流水线与质量评估。

用法（在项目根目录 ita/ 下）:
    PYTHONPATH=. python3 scripts/evaluate_data.py
    PYTHONPATH=. python3 scripts/evaluate_data.py /path/to/images
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2

from ita.core.offline_analyze import IMAGE_SUFFIX, analyze_bgr, quality_summary


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "data"
    if not data_dir.is_dir():
        print(f"目录不存在: {data_dir}", file=sys.stderr)
        return 1

    files = sorted(
        p for p in data_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIX
    )
    if not files:
        print(f"未找到图像: {data_dir}", file=sys.stderr)
        return 1

    rows = []
    for path in files:
        image = cv2.imread(str(path))
        if image is None:
            rows.append({"file": path.name, "error": "无法解码图像"})
            continue
        q = quality_summary(image)
        a = analyze_bgr(image)
        row = {
            "file": path.name,
            "shape": [int(image.shape[0]), int(image.shape[1])],
            "quality_score": q["score"],
            "quality_ready": q["ready"],
            "analysis_success": a.get("success"),
            "analysis_message": a.get("message"),
        }
        if a.get("result"):
            row.update({
                "ita": a["result"]["ita"],
                "category": a["result"]["category"],
                "fitzpatrick": a["result"]["fitzpatrick"],
                "confidence": a["result"]["confidence"],
                "lab_L": a["result"]["lab"]["L"],
                "lab_a": a["result"]["lab"]["a"],
                "lab_b": a["result"]["lab"]["b"],
            })
        if a.get("stages", {}).get("calibration"):
            row["white_mean_rgb"] = a["stages"]["calibration"].get("white_mean_rgb")
        rows.append(row)
        row["_quality_tips"] = q["tips"]
        row["_quality_checks"] = q["checks"]

    summary_rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    print(json.dumps(summary_rows, ensure_ascii=False, indent=2))

    print("\n=== 可读摘要 ===", flush=True)
    ok = sum(1 for r in rows if r.get("analysis_success"))
    print(f"样本数: {len(rows)}，分析成功: {ok}", flush=True)
    for r in rows:
        name = r.get("file", "?")
        if r.get("error"):
            print(f"- {name}: 错误 {r['error']}")
            continue
        if r.get("analysis_success"):
            print(
                f"- {name}: ITA°={r.get('ita')} | {r.get('category')} ({r.get('fitzpatrick')}) "
                f"| 置信度={r.get('confidence')} | 质量分={r.get('quality_score')} ready={r.get('quality_ready')}"
            )
        else:
            print(f"- {name}: 分析失败 — {r.get('analysis_message')} | 质量分={r.get('quality_score')}")
        for tip in r.get("_quality_tips") or []:
            print(f"    {tip}")

    print("\n=== 效果说明（无人工标注 ITA 时）===", flush=True)
    print(
        "- 流水线完整性: 以「分析成功」为准；失败时结合 quality_ready / tips 判断是否为光照、白纸或构图问题。\n"
        "- 质量分: QualityChecker 加权分项（模糊、亮度、白纸、皮肤覆盖等），ready=True 表示达到拍照门槛。\n"
        "- 若多样本 ITA 差异过大，需检查是否同一人、同一条手臂、光照与白纸是否一致。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
