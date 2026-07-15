"""
Test cơ bản cho src/data_processing.py.
Chạy: pytest tests/
"""

import pandas as pd

from src.data_processing import filter_it_occupations, clean_dataframe


def test_filter_it_occupations_keeps_only_it():
    df = pd.DataFrame(
        {
            "Occupation (O*NET-SOC Title)": ["Web Developers", "Registered Nurses"],
            "Task": ["Build API", "Check patient vitals"],
        }
    )
    result = filter_it_occupations(df)
    assert list(result["Occupation (O*NET-SOC Title)"]) == ["Web Developers"]


def test_clean_dataframe_drops_duplicates():
    df = pd.DataFrame({"a": [1, 1, 2]})
    result = clean_dataframe(df)
    assert len(result) == 2
