"""Tính ROI Index tương đối cho các task thuộc khối ngành IT.

ROI Index ở đây là chỉ số *ưu tiên kinh tế*, không phải ROI kế toán. Dữ liệu
WORKBank không chứa chi phí xây dựng/vận hành AI Agent nên không đủ để tính
(lợi ích - chi phí) / chi phí. Chỉ số này kết hợp:

* quy mô giá trị lao động của nghề (lương x số lao động);
* tỷ trọng thời gian, tần suất và tầm quan trọng của task;
* khả năng AI thực hiện task theo đánh giá chuyên gia.

Chạy: ``python -m src.roi_index``
Đầu ra: ``data/processed/roi_index.csv``
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

ID_COLUMNS = ["Task ID", "O*NET-SOC Code", "Occupation (O*NET-SOC Title)", "Task"]
REQUIRED_COLUMNS = [
    "Occupation Mean Annual Wage",
    "Occupation Employment",
    "Frequency",
    "Importance",
    "Expert_Automation Capacity Rating",
    "Worker_Time",
]

# Phân vị được tính trên các task đủ dữ liệu, giúp vùng chiến lược thích ứng với
# phân phối thực tế thay vì dùng ngưỡng tùy ý trên điểm Min-Max.
HIGH_ROI_QUANTILE = 0.75
MEDIUM_ROI_QUANTILE = 0.40


def _validate_columns(df: pd.DataFrame) -> None:
    """Báo lỗi rõ ràng nếu bảng master không đúng schema mong đợi."""
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Thiếu cột bắt buộc để tính ROI Index: {missing}")


def _minmax(series: pd.Series, valid_mask: pd.Series | None = None) -> pd.Series:
    """Chuẩn hóa Min-Max về [0, 1], giữ NaN và không rò dữ liệu thiếu."""
    numeric = pd.to_numeric(series, errors="coerce")
    mask = numeric.notna() if valid_mask is None else (valid_mask & numeric.notna())
    result = pd.Series(np.nan, index=series.index, dtype=float)
    if not mask.any():
        return result

    minimum = numeric.loc[mask].min()
    maximum = numeric.loc[mask].max()
    result.loc[mask] = (
        (numeric.loc[mask] - minimum) / (maximum - minimum)
        if maximum > minimum
        else 1.0
    )
    return result


def _complete_case_mask(df: pd.DataFrame) -> pd.Series:
    """Chọn các task có đủ và hợp lệ mọi thành phần của ROI Index."""
    numeric = df[REQUIRED_COLUMNS].apply(pd.to_numeric, errors="coerce")
    mask = numeric.notna().all(axis=1)
    mask &= numeric["Occupation Mean Annual Wage"].gt(0)
    mask &= numeric["Occupation Employment"].gt(0)
    mask &= numeric["Frequency"].gt(0)
    mask &= numeric["Importance"].gt(0)
    mask &= numeric["Frequency"].between(1, 7)
    mask &= numeric["Importance"].between(1, 5)
    mask &= numeric["Expert_Automation Capacity Rating"].between(1, 5)
    mask &= numeric["Worker_Time"].between(1, 5)
    return mask


def compute_roi_index(row: pd.Series) -> float:
    """Tính điểm tiềm năng kinh tế thô cho một dòng đã chuẩn hóa.

    Hàm này nhận các cột thành phần đã chuẩn hóa do :func:`build_roi_table`
    tạo ra. Dùng tích thay vì tổng để một yếu tố rất cao không che lấp hoàn
    toàn một yếu tố gần bằng 0.
    """
    components = [
        row.get("Market Scale", np.nan),
        row.get("Task Exposure", np.nan),
        row.get("Automation Potential", np.nan),
    ]
    if any(pd.isna(value) for value in components):
        return np.nan
    return float(np.prod(components))


def classify_strategy_zone(
    roi_index: float,
    medium_threshold: float = MEDIUM_ROI_QUANTILE,
    high_threshold: float = HIGH_ROI_QUANTILE,
) -> str:
    """Phân vùng một ROI Index theo các ngưỡng đã xác định."""
    if pd.isna(roi_index):
        return "Chưa đủ dữ liệu"
    if roi_index >= high_threshold:
        return "Tự động hóa ngay"
    if roi_index >= medium_threshold:
        return "Cân nhắc"
    return "Giữ nguyên / Theo dõi"


def _confidence(row: pd.Series) -> str:
    """Đánh giá sức mạnh bằng chứng từ cả expert và worker ratings.

    Mức Cao yêu cầu 3 expert raters (mức tối đa trong mẫu IT) và ít nhất 8
    worker respondents (trung vị của mẫu IT). Đây là quy tắc mô tả chất lượng
    bằng chứng, không phải khoảng tin cậy thống kê.
    """
    if not row["ROI Data Complete"]:
        return "Chưa đủ dữ liệu"
    n_raters = pd.to_numeric(row.get("Expert_N_Raters"), errors="coerce")
    n_workers = pd.to_numeric(row.get("Worker_N_Respondents"), errors="coerce")
    strong_expert = pd.notna(n_raters) and n_raters >= 3
    strong_worker = pd.notna(n_workers) and n_workers >= 8
    return "Cao" if strong_expert and strong_worker else "Trung bình"


def build_roi_table(master: pd.DataFrame) -> pd.DataFrame:
    """Tạo bảng ROI cấp task, gồm cả cờ chất lượng và vùng chiến lược.

    ``Worker_Time`` là rating 1-5 với hai neo do codebook quy định: 1 tương
    ứng 10% và 5 tương ứng 100% thời gian làm việc. ``Time Share Proxy`` nội
    suy tuyến tính giữa hai neo; đây vẫn là proxy, không phải số giờ thực tế.
    """
    _validate_columns(master)
    df = master.copy()
    complete = _complete_case_mask(df)
    df["ROI Data Complete"] = complete

    wage = pd.to_numeric(df["Occupation Mean Annual Wage"], errors="coerce")
    employment = pd.to_numeric(df["Occupation Employment"], errors="coerce")
    frequency = pd.to_numeric(df["Frequency"], errors="coerce")
    importance = pd.to_numeric(df["Importance"], errors="coerce")
    worker_time = pd.to_numeric(df["Worker_Time"], errors="coerce")
    capacity = pd.to_numeric(
        df["Expert_Automation Capacity Rating"], errors="coerce"
    )

    # Wage x Employment là wage-bill proxy cấp nghề. Log giảm độ lệch; xếp
    # hạng phân vị trên các nghề duy nhất tránh để nghề có nhiều task tự tạo
    # thêm trọng số trong bước chuẩn hóa Market Scale.
    labor_market_value = np.log1p(wage * employment).where(complete)
    occupation_col = "Occupation (O*NET-SOC Title)"
    occupation_market = (
        pd.DataFrame({occupation_col: df[occupation_col], "value": labor_market_value})
        .dropna()
        .groupby(occupation_col, as_index=True)["value"]
        .first()
    )
    occupation_percentile = occupation_market.rank(method="average", pct=True)
    df["Market Scale"] = df[occupation_col].map(occupation_percentile).where(complete)

    # Chuẩn hóa theo neo của thang đo gốc, không theo min/max quan sát trong
    # mẫu. Vì vậy Frequency=3 (hơn một lần/tháng) không bị biến thành 0.
    df["Frequency Intensity"] = ((frequency - 1.0) / 6.0).clip(0, 1).where(complete)
    df["Importance Intensity"] = ((importance - 1.0) / 4.0).clip(0, 1).where(complete)
    df["Time Share Proxy"] = (
        0.10 + 0.90 * ((worker_time - 1.0) / 4.0)
    ).clip(0.10, 1.0).where(complete)
    df["Task Exposure"] = (
        0.50 * df["Time Share Proxy"]
        + 0.25 * df["Frequency Intensity"]
        + 0.25 * df["Importance Intensity"]
    )
    df["Automation Potential"] = ((capacity - 1.0) / 4.0).clip(0, 1).where(complete)
    df["Economic Potential Raw"] = df.apply(compute_roi_index, axis=1)
    df["ROI Index"] = _minmax(df["Economic Potential Raw"], complete)

    valid_roi = df.loc[complete, "ROI Index"].dropna()
    medium_threshold = (
        float(valid_roi.quantile(MEDIUM_ROI_QUANTILE)) if not valid_roi.empty else np.nan
    )
    high_threshold = (
        float(valid_roi.quantile(HIGH_ROI_QUANTILE)) if not valid_roi.empty else np.nan
    )
    df["Strategy Zone"] = df["ROI Index"].apply(
        lambda value: classify_strategy_zone(
            value, medium_threshold=medium_threshold, high_threshold=high_threshold
        )
    )
    df["Data Confidence"] = df.apply(_confidence, axis=1)
    df["Time Cost Score"] = worker_time

    output_columns = [
        *[column for column in ID_COLUMNS if column in df.columns],
        "Occupation Mean Annual Wage",
        "Occupation Employment",
        "Frequency",
        "Importance",
        "Expert_Automation Capacity Rating",
        "Expert_N_Raters",
        "Worker_N_Respondents",
        "Time Cost Score",
        "Time Share Proxy",
        "Market Scale",
        "Frequency Intensity",
        "Importance Intensity",
        "Task Exposure",
        "Automation Potential",
        "Economic Potential Raw",
        "ROI Index",
        "ROI Data Complete",
        "Data Confidence",
        "Strategy Zone",
    ]
    output_columns = [column for column in output_columns if column in df.columns]
    return (
        df[output_columns]
        .drop_duplicates(subset=[column for column in ID_COLUMNS if column in df.columns])
        .sort_values("ROI Index", ascending=False, na_position="last")
        .reset_index(drop=True)
    )


def main() -> None:
    master_path = PROCESSED_DIR / "it_master.csv"
    output_path = PROCESSED_DIR / "roi_index.csv"
    master = pd.read_csv(master_path)
    roi_table = build_roi_table(master)
    roi_table.to_csv(output_path, index=False, float_format="%.6f")

    complete_count = int(roi_table["ROI Data Complete"].sum())
    print(f"[OK] Exported {len(roi_table):,} tasks to {output_path}")
    print(f"[INFO] {complete_count:,} tasks have complete ROI data")
    print(roi_table["Strategy Zone"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
