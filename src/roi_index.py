"""
roi_index.py
Phụ trách: Thành viên 2 - Data Analyst (Kinh tế)

Tính ROI Index cho từng task/nghề IT dựa trên: Occupation Mean Annual Wage,
Occupation Employment, Frequency/Importance, Automation Capacity Rating và Time cost.
Phân loại vào các vùng chiến lược: Tự động hóa ngay / Cân nhắc / Giữ nguyên.
"""

from pathlib import Path
import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

# Ngưỡng phân loại vùng chiến lược - điều chỉnh dựa trên phân phối thực tế của ROI Index
STRATEGY_THRESHOLDS = {
    "Tự động hóa ngay": 0.7,
    "Cân nhắc": 0.4,
    # còn lại -> "Giữ nguyên"
}


def compute_time_saved_hours(row: pd.Series) -> float:
    """Ước tính số giờ tiết kiệm được mỗi năm cho một task.

    Công thức tham khảo:
        Giờ tiết kiệm/năm ≈ Time (giờ/lần thực hiện, từ desires.csv)
                              × Frequency (số lần/năm, chuẩn hóa từ Frequency O*NET)
                              × (Automation Capacity Rating / thang điểm tối đa)

    TODO (TV2): tinh chỉnh công thức + chuẩn hóa thang điểm Frequency/Automation Capacity
    theo đúng phạm vi giá trị thực tế trong dữ liệu.
    """
    time_cost = row.get("Time", 0) or 0
    frequency = row.get("Frequency", 1) or 1
    automation_capacity = row.get("Automation Capacity Rating", 0) or 0
    max_rating = 5  # điều chỉnh nếu thang điểm khác

    return time_cost * frequency * (automation_capacity / max_rating)


def compute_roi_index(row: pd.Series) -> float:
    """Ước tính ROI Index (0-1) kết hợp tiền tiết kiệm được và mức độ AI làm được.

    Công thức tham khảo:
        ROI Index ≈ normalize( Wage × Employment × Automation Capacity × Importance )

    TODO (TV2): thay thế bằng công thức chuẩn hóa thực tế (vd Min-Max scaling)
    sau khi có phân phối dữ liệu đầy đủ.
    """
    wage = row.get("Occupation Mean Annual Wage", 0) or 0
    employment = row.get("Occupation Employment", 0) or 0
    automation_capacity = row.get("Automation Capacity Rating", 0) or 0
    importance = row.get("Importance", 1) or 1
    max_rating = 5

    raw_score = wage * employment * (automation_capacity / max_rating) * importance
    return raw_score  # TODO: chuẩn hóa về [0, 1] trên toàn bộ tập dữ liệu


def classify_strategy_zone(roi_index_normalized: float) -> str:
    """Phân loại vùng chiến lược dựa trên ROI Index đã chuẩn hóa [0, 1]."""
    if roi_index_normalized >= STRATEGY_THRESHOLDS["Tự động hóa ngay"]:
        return "Tự động hóa ngay"
    if roi_index_normalized >= STRATEGY_THRESHOLDS["Cân nhắc"]:
        return "Cân nhắc"
    return "Giữ nguyên"


def build_roi_table(master: pd.DataFrame) -> pd.DataFrame:
    """Xuất bảng (Occupation, Task, ROI Index, Giờ tiết kiệm, Vùng chiến lược)."""
    df = master.copy()
    df["Hours Saved"] = df.apply(compute_time_saved_hours, axis=1)
    df["ROI Index Raw"] = df.apply(compute_roi_index, axis=1)

    # Chuẩn hóa Min-Max về [0, 1]
    min_v, max_v = df["ROI Index Raw"].min(), df["ROI Index Raw"].max()
    df["ROI Index"] = (
        (df["ROI Index Raw"] - min_v) / (max_v - min_v) if max_v > min_v else 0.0
    )
    df["Strategy Zone"] = df["ROI Index"].apply(classify_strategy_zone)

    cols = [
        "Occupation (O*NET-SOC Title)",
        "Task",
        "ROI Index",
        "Hours Saved",
        "Strategy Zone",
    ]
    return df[[c for c in cols if c in df.columns]].drop_duplicates()


def main() -> None:
    master_path = PROCESSED_DIR / "it_master.csv"
    master = pd.read_csv(master_path)
    roi_table = build_roi_table(master)
    out_path = PROCESSED_DIR / "roi_index.csv"
    roi_table.to_csv(out_path, index=False)
    print(f"[OK] Đã xuất {len(roi_table):,} dòng ra {out_path}")


if __name__ == "__main__":
    main()
