"""
对仓库 data/ 目录中的样例图做回归验收。

CI 要求：必须存在 data/ 且至少有一张合规样例图，否则测试失败。
每张图：核心流水线须成功；质量综合分须不低于阈值；/api/analyze 须成功。
"""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest

from ita.core.offline_analyze import IMAGE_SUFFIX, analyze_bgr, quality_summary

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

if DATA_DIR.is_dir():
    DATA_IMAGES: list[Path] = sorted(
        p
        for p in DATA_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIX
    )
else:
    DATA_IMAGES = []

# 低于此分说明构图/光照/清晰度问题突出，不适合作为合格样例入库
MIN_QUALITY_SCORE = 0.70


def test_data_directory_has_sample_images() -> None:
    assert DATA_DIR.is_dir(), f"缺少目录: {DATA_DIR}（CI 要求保留 data/ 样例图）"
    assert DATA_IMAGES, (
        f"{DATA_DIR} 下至少需要一张样例图（后缀 {sorted(IMAGE_SUFFIX)}）"
    )


@pytest.mark.parametrize("path", DATA_IMAGES, ids=[p.name for p in DATA_IMAGES])
def test_data_image_core_pipeline_succeeds(path: Path) -> None:
    image = cv2.imread(str(path))
    assert image is not None, f"无法解码: {path.name}"
    result = analyze_bgr(image)
    assert result.get("success") is True, (path.name, result.get("message"))
    ita = result["result"]["ita"]
    assert -90 <= ita <= 90, path.name
    assert result["result"]["category"]


@pytest.mark.parametrize("path", DATA_IMAGES, ids=[p.name for p in DATA_IMAGES])
def test_data_image_quality_score(path: Path) -> None:
    image = cv2.imread(str(path))
    assert image is not None
    q = quality_summary(image)
    assert q["score"] >= MIN_QUALITY_SCORE, (
        path.name,
        q["score"],
        q.get("tips"),
    )


@pytest.mark.parametrize("path", DATA_IMAGES, ids=[p.name for p in DATA_IMAGES])
def test_data_image_api_analyze(client, path: Path) -> None:
    body = path.read_bytes()
    resp = client.post(
        "/api/analyze",
        files={"file": (path.name, body, "image/jpeg")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True, (path.name, data.get("message"))
    assert data["result"]["ita"] is not None
