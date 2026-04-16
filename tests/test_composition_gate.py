"""构图门禁：早退文案与分支逻辑。"""

from ita.core.composition_gate import (
    MSG_NEITHER_PAPER_NOR_ARM,
    MSG_NO_PAPER,
    MSG_NO_PAPER_SKIN_NOT_FOREARM,
    MSG_NO_SKIN,
    NOTE_NO_ANALYSIS,
    early_exit_message,
    note_no_analysis,
)


def test_neither_paper_nor_arm_returns_unified_message() -> None:
    assert (
        early_exit_message(
            has_white_paper=False,
            skin_mask_present=False,
            arm_ok=False,
            arm_msg="",
        )
        == MSG_NEITHER_PAPER_NOR_ARM
    )


def test_no_paper_but_skin_not_forearm_uses_distinct_message() -> None:
    assert (
        early_exit_message(
            has_white_paper=False,
            skin_mask_present=True,
            arm_ok=False,
            arm_msg="条状不足",
        )
        == MSG_NO_PAPER_SKIN_NOT_FOREARM
    )


def test_no_paper_but_arm_ok_returns_paper_only() -> None:
    assert (
        early_exit_message(
            has_white_paper=False,
            skin_mask_present=True,
            arm_ok=True,
            arm_msg="",
        )
        == MSG_NO_PAPER
    )


def test_paper_but_no_skin() -> None:
    assert (
        early_exit_message(
            has_white_paper=True,
            skin_mask_present=False,
            arm_ok=False,
            arm_msg="",
        )
        == MSG_NO_SKIN
    )


def test_paper_arm_fail_appends_no_analysis_to_arm_message() -> None:
    assert (
        early_exit_message(
            has_white_paper=True,
            skin_mask_present=True,
            arm_ok=False,
            arm_msg="请伸展前臂",
        )
        == note_no_analysis("请伸展前臂")
    )
    assert NOTE_NO_ANALYSIS in early_exit_message(
        has_white_paper=True,
        skin_mask_present=True,
        arm_ok=False,
        arm_msg="请伸展前臂",
    )


def test_note_no_analysis_idempotent() -> None:
    once = note_no_analysis("白纸亮度不足")
    assert NOTE_NO_ANALYSIS in once
    assert note_no_analysis(once) == once


def test_ok_proceeds() -> None:
    assert (
        early_exit_message(
            has_white_paper=True,
            skin_mask_present=True,
            arm_ok=True,
            arm_msg="",
        )
        is None
    )
