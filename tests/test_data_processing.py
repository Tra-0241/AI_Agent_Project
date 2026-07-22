"""
Test cơ bản cho src/data_processing.py.
Chạy: pytest tests/
"""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from src.data_processing import filter_it_occupations


def test_filter_it_occupations_keeps_only_it():
    df = pd.DataFrame(
        {
            "Occupation (O*NET-SOC Title)": ["Web Developers", "Registered Nurses"],
            "Task": ["Build API", "Check patient vitals"],
        }
    )
    result = filter_it_occupations(df)
    assert list(result["Occupation (O*NET-SOC Title)"]) == ["Web Developers"]