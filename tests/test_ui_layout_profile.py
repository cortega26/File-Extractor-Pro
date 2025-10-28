"""Tests for responsive layout profile calculation."""

from __future__ import annotations

from ui import (
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    calculate_layout_profile,
)


def test_calculate_layout_profile_compact_layout() -> None:
    profile = calculate_layout_profile(
        width=600,
        height=500,
        required_width=MIN_WINDOW_WIDTH,
        required_height=MIN_WINDOW_HEIGHT,
        scaling=1.4,
    )

    assert profile.extension_columns == 2
    assert profile.mode_columns == 1
    assert profile.main_column_weights == (1, 1, 1)
    assert profile.row_weights[5] == 1
    assert profile.min_width >= MIN_WINDOW_WIDTH
    assert profile.min_height >= MIN_WINDOW_HEIGHT


def test_calculate_layout_profile_standard_layout() -> None:
    profile = calculate_layout_profile(
        width=1100,
        height=800,
        required_width=MIN_WINDOW_WIDTH,
        required_height=MIN_WINDOW_HEIGHT,
        scaling=1.0,
    )

    assert profile.extension_columns == 4
    assert profile.mode_columns == 2
    assert profile.main_column_weights == (0, 1, 0)
    assert 5 not in profile.row_weights
    assert profile.min_width >= MIN_WINDOW_WIDTH
    assert profile.min_height >= MIN_WINDOW_HEIGHT
