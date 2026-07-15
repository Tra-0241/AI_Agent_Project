"""
friction_score.py
Phụ trách: Thành viên 3 - Data Analyst (Nhân sự & Rủi ro)

So sánh Automation Capacity Rating (expert) với Automation Desire Rating (worker)
trên cùng Task ID để đo Friction Score, có trọng số theo Job Security Rating,
Enjoyment Rating và các cờ Reasons for Human Agency. Gắn cờ cảnh báo đỏ/xanh.
"""

from pathlib import Path
import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

REASON_COLUMNS = [
    "Reasons for Human Agency - Control",
    "Reasons for Human Agency - Domain Knowledge",
    "Reasons for Human Agency - Empathy",
    "Reasons for Human Agency - Quality Oversight",
    "Reasons for Human Agency - Dynamic",
    "Reasons for Human Agency - Ethical",
]

RED_FLAG_THRESHOLD = 0.6  # ngưỡng Friction Score để gắn cờ cảnh báo đỏ


def compute_friction_score(row: pd.Series) -> float:
    """Ước tính Friction Score (0-1): độ lệch pha giữa AI làm được và người lao động muốn.

    Công thức tham khảo:
        gap = Automation Capacity Rating - Automation Desire Rating  (chuẩn hóa cùng thang)
        Friction Score ≈ max(0, gap) × trọng số(Job Security, Enjoyment, cờ Human Agency)

    Ý nghĩa: friction cao khi AI làm được cao (gap dương lớn) NHƯNG người lao động
    có lý do giữ vai trò con người mạnh (Job Security thấp / Enjoyment cao / nhiều cờ Human Agency).

    TODO (TV3): tinh chỉnh trọng số cụ thể cho từng thành phần sau khi phân tích phân phối dữ liệu.
    """
    max_rating = 5
    capacity = (row.get("Automation Capacity Rating", 0) or 0) / max_rating
    desire = (row.get("Automation Desire Rating", 0) or 0) / max_rating
    gap = max(0.0, capacity - desire)

    job_security = (row.get("Job Security Rating", max_rating) or max_rating) / max_rating
    enjoyment = (row.get("Enjoyment Rating", 0) or 0) / max_rating

    reason_flags = sum(bool(row.get(col, False)) for col in REASON_COLUMNS)
    reason_weight = 1 + (reason_flags / len(REASON_COLUMNS))  # 1.0 - 2.0

    # Job Security thấp (lo mất việc) và Enjoyment cao (thích công việc) đều làm friction tăng
    security_weight = 1 + (1 - job_security)
    enjoyment_weight = 1 + enjoyment

    score = gap * reason_weight * security_weight * enjoyment_weight
    return score


def flag_status(friction_score_normalized: float) -> str:
    return "Cảnh báo đỏ" if friction_score_normalized >= RED_FLAG_THRESHOLD else "Xanh"


def main_reason(row: pd.Series) -> str:
    """Trả về lý do Human Agency có trọng số/tần suất cao nhất (đơn giản hoá: cờ đầu tiên = True)."""
    for col in REASON_COLUMNS:
        if row.get(col, False):
            return col.replace("Reasons for Human Agency - ", "")
    return "Không rõ"


def build_friction_table(master: pd.DataFrame) -> pd.DataFrame:
    """Xuất bảng (Occupation, Task, Friction Score, Cảnh báo đỏ/xanh, Lý do chính)."""
    df = master.copy()
    df["Friction Score Raw"] = df.apply(compute_friction_score, axis=1)

    min_v, max_v = df["Friction Score Raw"].min(), df["Friction Score Raw"].max()
    df["Friction Score"] = (
        (df["Friction Score Raw"] - min_v) / (max_v - min_v) if max_v > min_v else 0.0
    )
    df["Flag"] = df["Friction Score"].apply(flag_status)
    df["Main Reason"] = df.apply(main_reason, axis=1)

    cols = [
        "Occupation (O*NET-SOC Title)",
        "Task",
        "Friction Score",
        "Flag",
        "Main Reason",
    ]
    return df[[c for c in cols if c in df.columns]].drop_duplicates()


def main() -> None:
    master_path = PROCESSED_DIR / "it_master.csv"
    master = pd.read_csv(master_path)
    friction_table = build_friction_table(master)
    out_path = PROCESSED_DIR / "friction_score.csv"
    friction_table.to_csv(out_path, index=False)
    print(f"[OK] Đã xuất {len(friction_table):,} dòng ra {out_path}")


if __name__ == "__main__":
    main()
