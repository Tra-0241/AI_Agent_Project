"""
data_processing.py
Phụ trách: Thành viên 1 - Data Engineer

Đọc 4 file CSV từ WORKBank, merge theo Task ID / User ID, lọc riêng các
Occupation thuộc khối IT, làm sạch dữ liệu và xuất ra data/processed/it_master.csv
để Thành viên 2 (ROI Index) và Thành viên 3 (Friction Score) sử dụng.
"""

from pathlib import Path
import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

# Danh sách occupation thuộc khối IT cần lọc (chỉnh sửa theo O*NET-SOC Title thực tế trong dữ liệu)
IT_OCCUPATIONS = [
    "Computer Systems Analysts",
    "Software Quality Assurance Analysts and Testers",
    "Web Developers",
    "Web and Digital Interface Designers",
    "Database Administrators",
    "Database Architects",
    "Network and Computer Systems Administrators",
    "Computer Network Architects",
    "Information Security Analysts",
    "Project Management Specialists",
]


def load_raw_data() -> dict[str, pd.DataFrame]:
    """Đọc 4 file CSV gốc từ data/raw/."""
    return {
        "task": pd.read_csv(RAW_DIR / "task_statement_with_metadata.csv"),
        "expert": pd.read_csv(RAW_DIR / "expert_rated_technological_capability.csv"),
        "desires": pd.read_csv(RAW_DIR / "domain_worker_desires.csv"),
        "metadata": pd.read_csv(RAW_DIR / "domain_worker_metadata.csv"),
    }


def filter_it_occupations(df: pd.DataFrame, column: str = "Occupation (O*NET-SOC Title)") -> pd.DataFrame:
    """Lọc riêng các dòng thuộc khối Occupation IT."""
    return df[df[column].isin(IT_OCCUPATIONS)].copy()


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Chuẩn hóa kiểu dữ liệu và xử lý giá trị thiếu cơ bản.

    TODO (TV1): bổ sung logic làm sạch cụ thể theo từng cột
    (Boolean, Date, cột dạng chuỗi list như Skill ID) sau khi khảo sát dữ liệu thực tế.
    """
    df = df.copy()
    df = df.drop_duplicates()
    return df


def build_master_table() -> pd.DataFrame:
    """Merge task + expert + desires (theo Task ID) và desires + metadata (theo User ID),
    lọc khối IT, xuất bảng master dùng chung cho cả nhóm.
    """
    data = load_raw_data()

    task_it = filter_it_occupations(clean_dataframe(data["task"]))
    expert_it = filter_it_occupations(clean_dataframe(data["expert"]))
    desires_it = filter_it_occupations(clean_dataframe(data["desires"]))
    metadata = clean_dataframe(data["metadata"])

    # Merge expert rating vào task theo Task ID
    master = task_it.merge(
        expert_it.drop(columns=["Occupation (O*NET-SOC Title)", "Task"], errors="ignore"),
        on="Task ID",
        how="left",
        suffixes=("", "_expert"),
    )

    # Merge worker desire theo Task ID (desires có thể có nhiều dòng/worker cho mỗi task)
    master = master.merge(
        desires_it.drop(columns=["Occupation (O*NET-SOC Title)", "Task"], errors="ignore"),
        on="Task ID",
        how="left",
        suffixes=("", "_desire"),
    )

    # Gắn thêm hồ sơ worker (nếu cột User ID còn giữ lại sau merge với desires)
    if "User ID" in master.columns:
        master = master.merge(metadata, on="User ID", how="left", suffixes=("", "_worker"))

    return master


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    master = build_master_table()
    out_path = PROCESSED_DIR / "it_master.csv"
    master.to_csv(out_path, index=False)
    print(f"[OK] Đã xuất {len(master):,} dòng ra {out_path}")


if __name__ == "__main__":
    main()
