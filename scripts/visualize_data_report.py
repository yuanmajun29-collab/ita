"""
为 data/ 样例图生成本地可视化 HTML 报告（浏览器打开即可）。

包含：原图与质量叠加图、ITA°/Lab/分类、质量分条形对比、分项检查摘要。

用法（在项目根目录 ita/ 下）:
    PYTHONPATH=. python3 scripts/visualize_data_report.py
    PYTHONPATH=. python3 scripts/visualize_data_report.py /path/to/out.html
"""

from __future__ import annotations

import base64
import html
import sys
from datetime import datetime
from pathlib import Path

import cv2

from ita import __version__
from ita.core.offline_analyze import IMAGE_SUFFIX, analyze_bgr
from ita.core.quality_checker import QualityChecker


def _jpeg_b64(img, quality: int = 82) -> str:
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("imencode failed")
    return base64.b64encode(buf).decode("ascii")


def _ita_marker_pct(ita: float) -> float:
    """将 ITA° 映射到 0–100%（用于量尺上的标记位置）。"""
    t = (ita + 90) / 180.0
    return max(0.0, min(100.0, t * 100.0))


def _interpretation_section_html() -> str:
    """与 README「8000 服务评测结果解读」一致的报告内说明（静态 HTML）。"""
    return """
  <section class="guide">
    <h2>结果解读（8000 服务 / data 评测）</h2>
    <ul>
      <li><strong>卡片 PASS / FAIL</strong>：PASS 表示「白纸校准 → 皮肤采样 → ITA°」流水线成功；FAIL 多为未检测到白纸或皮肤区域，需重拍或检查构图。</li>
      <li><strong>ITA°</strong>：肤色类型学角度；量尺上越靠右越偏浅、越靠左越偏深。与医学上仪器 ITA 对比时需相同部位与光照。</li>
      <li><strong>分类 / Fitzpatrick</strong>：由 ITA° 映射得到，供防晒与维D等场景参考，非临床诊断。</li>
      <li><strong>置信度</strong>：分类到区间中心的接近程度（0～1）。接近类别边界时值往往偏低，建议结合多次测量。</li>
      <li><strong>L*a*b*</strong>：与 ITA° 同源；L* 偏高通常更亮，b* 与黄调相关。</li>
      <li><strong>质量综合分 / ready</strong>：综合模糊、亮度、白纸与皮肤占比等；<strong>ready=true</strong> 表示达到拍照引导门槛。与「分析是否成功」独立——略模糊时仍可能算出 ITA，但 ready 可为 false。</li>
      <li><strong>分项（blur / brightness 等）</strong>：各子项 score 为 0～1；tips 为对应改进建议。</li>
      <li><strong>校准 RGB</strong>：白纸均值越接近白、归一化后肤色越可比；若白纸过暗，message 会提示改善光照。</li>
    </ul>
    <p class="guide-foot">自动化测试：<code>pytest</code> / <code>verify_demo.py</code> 全通过表示接口与 <code>data/</code> 样例回归正常；与单张图的医学准确度无直接等价关系。</p>
  </section>
"""


def _build_html(rows: list[dict], generated_at: str) -> str:
    #质量分对比条（纯 CSS）
    bar_rows = ""
    for r in rows:
        w = r["quality_score"] * 100
        bar_rows += (
            f'<div class="qbar"><span class="qname">{html.escape(r["file"])}</span>'
            f'<div class="qtrack"><div class="qfill" style="width:{w:.1f}%"></div></div>'
            f'<span class="qval">{r["quality_score"]:.2f}</span></div>'
        )

    cards = ""
    for r in rows:
        ita = r.get("ita")
        if ita is None:
            ita_bar = "<p class=\"fail\">分析未成功</p>"
        else:
            pct = _ita_marker_pct(float(ita))
            ita_bar = f"""
            <div class="ita-scale">
              <div class="ita-labels"><span>深 -90°</span><span>0°</span><span>浅 +90°</span></div>
              <div class="ita-track">
                <div class="ita-zones"></div>
                <div class="ita-marker" style="left:{pct:.1f}%"></div>
              </div>
              <p class="ita-value">ITA° = {ita:.2f}</p>
            </div>
            """

        tips_html = "".join(
            f"<li>{html.escape(t)}</li>" for t in r.get("tips", [])
        )
        cal = r.get("calibration") or {}
        cal_txt = ""
        if cal:
            cal_txt = (
                f"<p class=\"meta\">白纸 RGB {cal.get('white_mean_rgb')} · "
                f"皮肤均值 RGB {cal.get('skin_mean_rgb')} · "
                f"归一化 RGB {cal.get('normalized_rgb')}</p>"
            )

        status = "ok" if r.get("analysis_success") else "fail"
        cards += f"""
        <article class="card">
          <h3>{html.escape(r["file"])} <span class="badge {status}">{"PASS" if r["analysis_success"] else "FAIL"}</span></h3>
          <div class="imgs">
            <figure><figcaption>原图</figcaption><img src="data:image/jpeg;base64,{r["b64_orig"]}" alt=""></figure>
            <figure><figcaption>质量叠加（白纸轮廓 / 皮肤区域）</figcaption><img src="data:image/jpeg;base64,{r["b64_overlay"]}" alt=""></figure>
          </div>
          {ita_bar}
          <table class="metrics">
            <tr><th>分类</th><td>{html.escape(str(r.get("category", "—")))}</td></tr>
            <tr><th>Fitzpatrick</th><td>{html.escape(str(r.get("fitzpatrick", "—")))}</td></tr>
            <tr><th>置信度</th><td>{r.get("confidence", "—")}</td></tr>
            <tr><th>L*a*b*</th><td>{html.escape(str(r.get("lab", "—")))}</td></tr>
            <tr><th>质量综合分</th><td>{r["quality_score"]:.2f}（ready={r["quality_ready"]}）</td></tr>
          </table>
          {cal_txt}
          <p class="checks"><strong>分项</strong> {html.escape(r.get("checks_summary", ""))}</p>
          <ul class="tips">{tips_html}</ul>
        </article>
        """

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ITA data/ 验证报告</title>
  <style>
    :root {{
      --bg: #0f1419;
      --card: #1a2332;
      --text: #e7ecf3;
      --muted: #8b9cb3;
      --accent: #3d8bfd;
      --ok: #3fb950;
      --fail: #f85149;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 1.5rem;
      line-height: 1.5;
    }}
    h1 {{ font-size: 1.35rem; margin-top: 0; }}
    .meta-head {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 1.5rem; }}
    .summary {{
      background: var(--card);
      border-radius: 12px;
      padding: 1rem 1.25rem;
      margin-bottom: 1.5rem;
    }}
    .summary h2 {{ font-size: 1rem; margin: 0 0 0.75rem 0; }}
    .qbar {{ display: flex; align-items: center; gap: 0.75rem; margin: 0.4rem 0; font-size: 0.85rem; }}
    .qname {{ width: 6rem; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; }}
    .qtrack {{ flex: 1; height: 10px; background: #2d3848; border-radius: 5px; overflow: hidden; }}
    .qfill {{ height: 100%; background: linear-gradient(90deg, var(--accent), #7aa8ff); border-radius: 5px; }}
    .qval {{ width: 2.5rem; text-align: right; color: var(--muted); }}
    .card {{
      background: var(--card);
      border-radius: 12px;
      padding: 1.25rem;
      margin-bottom: 1.5rem;
    }}
    .card h3 {{ margin: 0 0 1rem 0; font-size: 1.05rem; display: flex; align-items: center; gap: 0.5rem; }}
    .badge {{ font-size: 0.7rem; padding: 0.15rem 0.45rem; border-radius: 4px; font-weight: 600; }}
    .badge.ok {{ background: rgba(63, 185, 80, 0.2); color: var(--ok); }}
    .badge.fail {{ background: rgba(248, 81, 73, 0.2); color: var(--fail); }}
    .imgs {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }}
    @media (max-width: 800px) {{ .imgs {{ grid-template-columns: 1fr; }} }}
    figure {{ margin: 0; }}
    figcaption {{ font-size: 0.8rem; color: var(--muted); margin-bottom: 0.35rem; }}
    .imgs img {{ width: 100%; height: auto; border-radius: 8px; display: block; }}
    .ita-scale {{ margin: 1rem 0; }}
    .ita-labels {{ display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--muted); }}
    .ita-track {{
      position: relative; height: 22px; margin: 0.35rem 0 0.5rem;
      border-radius: 6px; overflow: hidden;
      background: linear-gradient(90deg, #5c2a00 0%, #c45c2a 25%, #e8c89a 50%, #f5e6d3 75%, #ffffff 100%);
    }}
    .ita-marker {{
      position: absolute; top: 0; bottom: 0; width: 4px; margin-left: -2px;
      background: #111; box-shadow: 0 0 0 2px #fff;
    }}
    .ita-value {{ font-weight: 600; margin: 0; font-size: 0.95rem; }}
    .metrics {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    .metrics th, .metrics td {{ text-align: left; padding: 0.35rem 0.5rem; border-bottom: 1px solid #2d3848; }}
    .metrics th {{ color: var(--muted); width: 8rem; }}
    .meta, .checks {{ font-size: 0.85rem; color: var(--muted); }}
    .tips {{ margin: 0.5rem 0 0; padding-left: 1.2rem; font-size: 0.85rem; color: var(--muted); }}
    .fail {{ color: var(--fail); }}
    .guide {{
      background: #151d2a;
      border-left: 4px solid var(--accent);
      border-radius: 10px;
      padding: 1rem 1.1rem;
      margin-bottom: 1.5rem;
      font-size: 0.86rem;
      line-height: 1.55;
    }}
    .guide h2 {{ font-size: 1rem; margin: 0 0 0.65rem 0; color: var(--text); }}
    .guide ul {{ margin: 0; padding-left: 1.15rem; }}
    .guide li {{ margin: 0.35rem 0; color: #c5d0de; }}
    .guide-foot {{ margin: 0.75rem 0 0 0; font-size: 0.8rem; color: var(--muted); }}
    .guide code {{ font-size: 0.82em; background: #0f1419; padding: 0.1em 0.35em; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>ITA <code>data/</code> 验证可视化报告</h1>
  <p class="meta-head">生成时间 {html.escape(generated_at)} · 程序版本 {html.escape(__version__)} · 对应端口 8000 上同源分析逻辑</p>
  {_interpretation_section_html()}
  <section class="summary">
    <h2>质量综合分对比</h2>
    {bar_rows}
  </section>
  {cards}
</body>
</html>
"""


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    data_dir = root / "data"
    out_path = (
        Path(sys.argv[1]).expanduser()
        if len(sys.argv) > 1
        else root / "reports" / "data_eval.html"
    )

    if not data_dir.is_dir():
        print(f"缺少目录: {data_dir}", file=sys.stderr)
        return 1

    files = sorted(
        p for p in data_dir.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIX
    )
    if not files:
        print(f"未找到图像: {data_dir}", file=sys.stderr)
        return 1

    qc = QualityChecker()
    rows: list[dict] = []
    for path in files:
        image = cv2.imread(str(path))
        if image is None:
            rows.append({
                "file": path.name,
                "analysis_success": False,
                "b64_orig": "",
                "b64_overlay": "",
                "quality_score": 0.0,
                "quality_ready": False,
                "tips": ["无法解码图像"],
                "checks_summary": "",
            })
            continue

        full_q = qc.check_all(image)
        overlay = qc.get_quality_overlay(image, full_q["checks"])
        analysis = analyze_bgr(image)

        checks_parts = []
        for key, chk in (full_q.get("checks") or {}).items():
            if isinstance(chk, dict):
                checks_parts.append(f"{key}={chk.get('score', '?')}")
        checks_summary = "; ".join(checks_parts)

        row = {
            "file": path.name,
            "b64_orig": _jpeg_b64(image),
            "b64_overlay": _jpeg_b64(overlay),
            "quality_score": full_q["score"],
            "quality_ready": full_q["ready"],
            "tips": full_q.get("tips") or [],
            "checks_summary": checks_summary,
            "analysis_success": analysis.get("success", False),
            "ita": None,
            "category": None,
            "fitzpatrick": None,
            "confidence": None,
            "lab": None,
            "calibration": None,
        }
        if analysis.get("success") and analysis.get("result"):
            res = analysis["result"]
            row["ita"] = res["ita"]
            row["category"] = res["category"]
            row["fitzpatrick"] = res["fitzpatrick"]
            row["confidence"] = res["confidence"]
            row["lab"] = res["lab"]
            st = analysis.get("stages", {})
            cal = st.get("calibration", {})
            sk = st.get("skin", {})
            row["calibration"] = {
                "white_mean_rgb": cal.get("white_mean_rgb"),
                "skin_mean_rgb": sk.get("skin_mean_rgb"),
                "normalized_rgb": sk.get("normalized_rgb"),
            }
        rows.append(row)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    html_doc = _build_html(rows, datetime.now().isoformat(timespec="seconds"))
    out_path.write_text(html_doc, encoding="utf-8")
    print(f"已写入: {out_path}")
    print(f"用浏览器打开: file://{out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
