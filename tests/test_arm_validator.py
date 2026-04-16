"""前臂条状区域校验（与 analyze 流水线一致）。"""

import cv2
import numpy as np
import pytest

from ita.core.arm_validator import validate_forearm_skin_mask


@pytest.fixture
def canvas() -> np.ndarray:
    return np.zeros((200, 320), dtype=np.uint8)


def test_accepts_elongated_skin_blob(canvas):
    """条状皮肤区域应通过。"""
    canvas[70:150, 30:280] = 255
    ok, msg = validate_forearm_skin_mask(canvas)
    assert ok is True
    assert msg == ""


def test_rejects_compact_square_like_blob(canvas):
    """近似正方形的大块皮肤（易为面部特写）应拒绝。"""
    canvas[50:150, 110:210] = 255
    ok, msg = validate_forearm_skin_mask(canvas)
    assert ok is False
    assert "前臂" in msg or "条状" in msg


def test_rejects_tiny_skin_area():
    """过小区域应拒绝。"""
    m = np.zeros((200, 200), dtype=np.uint8)
    m[10:25, 10:25] = 255
    ok, msg = validate_forearm_skin_mask(m)
    assert ok is False
