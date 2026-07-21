"""Kiểm thử cho mô hình Friction Score"""

import pandas as pd
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.friction_score import (
    build_friction_table,
    filter_scoreable_tasks,
    compute_friction_components,
    compute_friction_score,
    build_friction_by_group,
    build_data_dictionary,
)


def _master_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Task ID": [1, 2, 3, 4],
            "Occupation (O*NET-SOC Title)": ["IT Role"] * 4,
            "Task": ["High", "Medium", "Low", "Missing"],
            "Has_Expert_Rating": [True, True, True, False],
            "Has_Worker_Rating": [True, True, True, True],
            "Expert_Automation Capacity Rating": [5, 3, 1, 4],
            "Worker_Automation Desire Rating": [1, 3, 5, 4],
            "Worker_Job Security Rating": [1, 3, 5, 2],
            "Worker_Enjoyment Rating": [5, 3, 1, 2],
            "Share_HumanAgency_Control": [0.5, 0.2, 0.0, 0.1],
            "Share_HumanAgency_Empathy": [0.4, 0.1, 0.0, 0.0],
            "Share_HumanAgency_Ethical": [0.3, 0.0, 0.0, 0.0],
            "Expert_N_Raters": [3, 2, 1, 2],
            "Worker_N_Respondents": [10, 8, 5, 3],
        }
    )


def test_build_friction_table_filters_and_ranks() -> None:
    result = build_friction_table(_master_fixture())

    # one row has Has_Expert_Rating=False and should be dropped
    assert len(result) == 3
    # the task with large positive gap (Expert 5 vs Worker 1) should rank first
    assert list(result["Task"])[0] == "High"


def test_components_and_reason_label() -> None:
    master = _master_fixture()
    scoreable = filter_scoreable_tasks(master)
    with_components = compute_friction_components(scoreable)
    scored = compute_friction_score(with_components)

    top_reason = scored.loc[scored["Task"] == "High", "Lý do chính"].values[0]
    assert (
        top_reason
        == "Chênh lệch AI làm được vs người lao động muốn"
    )


def test_build_friction_by_group_aggregates() -> None:
    master = _master_fixture()
    friction_table = build_friction_table(master)

    worker_level = pd.DataFrame(
        {
            "Task ID": [1, 1, 2, 3],
            "AI Suffering Attitude": ["Agree", "Agree", "Disagree", "Agree"],
            "AI Job Importance Attitude": ["High", "High", "Low", "High"],
            "AI Tedious Work Attitude": ["Low", "Low", "High", "Low"],
            "Experience": ["Senior", "Junior", "Junior", "Senior"],
        }
    )

    by_group = build_friction_by_group(friction_table, worker_level)
    assert "Avg_Friction_Score" in by_group.columns
    assert "Pct_Canh_Bao_Do" in by_group.columns


def test_build_data_dictionary_has_rows() -> None:
    d = build_data_dictionary()
    assert not d.empty
