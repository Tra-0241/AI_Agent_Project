"""Kiểm thử cho mô hình ROI Index của Thành viên 2."""

import numpy as np
import pandas as pd
import pytest

from src.roi_index import build_roi_table, classify_strategy_zone


def _master_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Task ID": [1, 2, 3, 4],
            "O*NET-SOC Code": ["15-1"] * 4,
            "Occupation (O*NET-SOC Title)": ["IT Role"] * 4,
            "Task": ["Low", "Medium", "High", "Missing"],
            "Occupation Mean Annual Wage": [50_000, 80_000, 120_000, np.nan],
            "Occupation Employment": [10_000, 50_000, 100_000, 20_000],
            "Frequency": [3, 5, 7, 4],
            "Importance": [2, 3.5, 5, 3],
            "Expert_Automation Capacity Rating": [1, 3, 5, 4],
            "Expert_N_Raters": [2, 2, 3, 3],
            "Worker_N_Respondents": [5, 8, 10, 10],
            "Worker_Time": [1, 2, 3, 2],
        }
    )


def test_build_roi_table_ranks_complete_rows_and_preserves_missing() -> None:
    result = build_roi_table(_master_fixture()).set_index("Task")

    assert result.loc["High", "ROI Index"] == pytest.approx(1.0)
    assert result.loc["Low", "ROI Index"] == pytest.approx(0.0)
    assert pd.isna(result.loc["Missing", "ROI Index"])
    assert result.loc["Missing", "Strategy Zone"] == "Chưa đủ dữ liệu"
    assert not bool(result.loc["Missing", "ROI Data Complete"])


def test_output_uses_real_master_column_names() -> None:
    result = build_roi_table(_master_fixture())

    assert result["Automation Potential"].notna().sum() == 3
    assert "Time Cost Score" in result.columns
    assert "Time Share Proxy" in result.columns
    assert "Task Exposure" in result.columns
    assert "Hours Saved" not in result.columns


def test_confidence_uses_expert_rater_count() -> None:
    result = build_roi_table(_master_fixture()).set_index("Task")

    assert result.loc["High", "Data Confidence"] == "Cao"
    assert result.loc["Medium", "Data Confidence"] == "Trung bình"


def test_scale_anchors_are_used_instead_of_sample_minmax() -> None:
    result = build_roi_table(_master_fixture()).set_index("Task")

    assert result.loc["Low", "Frequency Intensity"] == pytest.approx((3 - 1) / 6)
    assert result.loc["Low", "Importance Intensity"] == pytest.approx((2 - 1) / 4)
    assert result.loc["Low", "Time Share Proxy"] == pytest.approx(0.10)
    assert result.loc["High", "Time Share Proxy"] == pytest.approx(0.55)


def test_strategy_zone_handles_missing_value() -> None:
    assert classify_strategy_zone(np.nan) == "Chưa đủ dữ liệu"
    assert classify_strategy_zone(0.8, 0.4, 0.7) == "Tự động hóa ngay"
    assert classify_strategy_zone(0.5, 0.4, 0.7) == "Cân nhắc"
    assert classify_strategy_zone(0.2, 0.4, 0.7) == "Giữ nguyên / Theo dõi"


def test_missing_required_column_has_clear_error() -> None:
    with pytest.raises(ValueError, match="Thiếu cột bắt buộc"):
        build_roi_table(_master_fixture().drop(columns=["Frequency"]))
