"""
friction_score.py
Phụ trách: Thành viên 3 

Đọc 2 file đã xử lý bởi TV1 (data/processed/it_master.csv và it_worker_level.csv), 
tính Friction Score cho từng task IT dựa trên độ lệch pha giữa "AI làm được" 
(Expert_Automation Capacity Rating) và "người lao động muốn" (Worker_Automation Desire
Rating), có trọng số theo Job Security Rating, Enjoyment Rating và
các lý do muốn giữ vai trò con người (Reasons for Human Agency).

Xuất ra:
data/processed/friction_score.csv -> Input chính cho Dashboard TV4.

outputs/analysis/friction_score_by_group.csv -> Phân tích theo nhóm nhân khẩu học/thái độ AI.

outputs/dictionaries/friction_score_data_dictionary.csv -> Giải thích ý nghĩa các cột do TV3 tạo.

Cách chạy:
    python friction_score.py
(mặc định đọc từ ../data/processed và ghi ra ../data/processed so với vị trí
file này; chỉnh PROCESSED_DIR bên dưới nếu cấu trúc repo khác)
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"

ANALYSIS_DIR = OUTPUT_DIR / "analysis"
DICTIONARY_DIR = OUTPUT_DIR / "dictionaries"
SENSITIVITY_DIR = OUTPUT_DIR / "sensitivity"

# ==============================================
# 1. CẤU HÌNH CÔNG THỨC
# 
# Friction Score = mức độ "lực cản" khi triển khai AI Agent cho 1 task:
# AI càng CÓ KHẢ NĂNG làm (Expert rating cao) mà người lao động càng
# KHÔNG MUỐN nhường (Worker desire thấp, Job Security thấp = lo mất việc,
# Enjoyment cao = thích task nên không muốn giao AI, hoặc nêu nhiều lý do
# muốn giữ con người vì Control/Ethical/Empathy) thì Friction Score càng cao.
#
# LỰA CHỌN TRỌNG SỐ - ĐÃ KIỂM ĐỊNH BẰNG PCA (xem sensitivity_analysis.py):
# Ban đầu dự định lấy trọng số từ PCA (data-driven), nhưng chạy PCA trên 131
# task IT thực tế cho thấy 4 thành phần gần như KHÔNG tương quan với nhau
# (|r| = 0.10-0.22) và PC1 chỉ giải thích 33.6% phương sai (PC2 giải thích
# 31.2%, gần bằng PC1) -> không có "trục chính" nào áp đảo. Tệ hơn, PC1 tải
# âm (-0.17) lên Capacity_Desire_Gap - biến quan trọng nhất về mặt lý thuyết
# của đề tài - tức là PCA sẽ cho biến này trọng số gần như bằng 0 (~3%),
# ngược hoàn toàn với logic đề tài đặt ra.
#
# Kết luận: vì 4 biến gần trực giao (không redundant), KHÔNG có cơ sở dữ
# liệu nào để nói biến này quan trọng hơn biến kia -> dùng trọng số BẰNG
# NHAU là lựa chọn có cơ sở thống kê (chính tính trực giao là bằng chứng),
# thay vì áp đặt chủ quan hay ép dùng PCA không phù hợp.

WEIGHT_CAPACITY_DESIRE_GAP = 0.25   # lệch pha AI làm được vs người lao động muốn
WEIGHT_JOB_SECURITY = 0.25          # càng lo mất việc -> càng cản trở
WEIGHT_ENJOYMENT = 0.25             # càng thích task -> càng không muốn nhường
WEIGHT_HUMAN_AGENCY = 0.25          # càng nhiều lý do muốn giữ vai trò con người

# Ngưỡng phân loại "cảnh báo đỏ": task nằm trong nhóm Friction Score cao nhất
# (mặc định top 25% - phần tư trên cùng của toàn bộ task IT có đủ dữ liệu).
RED_FLAG_PERCENTILE = 0.75

# Các cột lý do muốn giữ vai trò con người dùng để tính Human Agency
# resistance. Chỉ chọn 3 lý do phản ánh trực tiếp "không muốn nhường AI"
# (Control, Empathy, Ethical) theo mô tả trong phân công nhiệm vụ; các lý do
# còn lại (Physical, Domain Knowledge, Quality Oversight, Dynamic) thiên về
# đặc điểm công việc hơn là thái độ phản kháng.
HUMAN_AGENCY_RESISTANCE_COLS = [
    "Share_HumanAgency_Control",
    "Share_HumanAgency_Empathy",
    "Share_HumanAgency_Ethical",
]

# Các cột nhân khẩu học / thái độ dùng để phân tích rủi ro theo nhóm
GROUP_BY_COLS = [
    "AI Suffering Attitude",
    "AI Job Importance Attitude",
    "AI Tedious Work Attitude",
    "Experience",
]


# ==========
# 2. LOAD
# ==========
def load_processed_data() -> dict[str, pd.DataFrame]:
    """Đọc it_master.csv và it_worker_level.csv do TV1 xuất ra.

    Returns
    -------
    dict[str, pd.DataFrame]
        {"master": ..., "worker_level": ...}
    """
    master = pd.read_csv(PROCESSED_DIR / "it_master.csv")
    worker_level = pd.read_csv(PROCESSED_DIR / "it_worker_level.csv")
    logger.info(
        "Loaded processed shapes -> master:%s worker_level:%s",
        master.shape, worker_level.shape,
    )
    return {"master": master, "worker_level": worker_level}


# ============
# 2. HELPERS
# ============
def _minmax_normalize(series: pd.Series) -> pd.Series: # hàm chuẩn hóa dữ liệu
    """Chuẩn hóa 1 cột về [0, 1] bằng min-max scaling.

    Nếu toàn bộ giá trị bằng nhau (max == min), trả về 0.5 cho mọi dòng
    thay vì chia cho 0 -> tránh NaN lan sang Friction Score.
    """
    lo, hi = series.min(), series.max()
    if pd.isna(lo) or pd.isna(hi) or hi == lo:
        return pd.Series(0.5, index=series.index)
    return (series - lo) / (hi - lo)


def filter_scoreable_tasks(master: pd.DataFrame) -> pd.DataFrame:
    """Chỉ giữ lại các task IT có ĐỦ cả expert rating lẫn worker rating.

    Friction Score cần so sánh 2 phía (AI làm được vs người lao động muốn),
    nên task thiếu 1 trong 2 phía (Has_Expert_Rating=False hoặc
    Has_Worker_Rating=False) không đủ điều kiện tính điểm -> loại ra và log
    cảnh báo thay vì tự impute, để không làm sai lệch phân bố điểm.
    """
    mask = master["Has_Expert_Rating"] & master["Has_Worker_Rating"]
    n_dropped = int((~mask).sum())
    if n_dropped:
        logger.info(
            "friction_score: loai %s/%s task IT vi thieu Expert hoac Worker rating "
            "(khong du dieu kien tinh Friction Score).", n_dropped, len(master),
        )
    return master[mask].copy()


# ---------------------------------------------------------------------------
# 3. TÍNH FRICTION SCORE (cấp Task)
# ---------------------------------------------------------------------------
def compute_friction_components(df: pd.DataFrame) -> pd.DataFrame:
    """Tính 4 thành phần của Friction Score, đã chuẩn hóa về [0, 1].

    - Capacity_Desire_Gap: Expert Automation Capacity - Worker Automation
      Desire, chỉ giữ phần dương (AI làm được NHIỀU HƠN mức người lao động
      MUỐN nhường); phần âm (worker muốn tự động hóa nhiều hơn AI làm được)
      không phải là "lực cản" nên được cắt về 0 trước khi chuẩn hóa.
    - JobSecurity_Concern: Job Security Rating càng THẤP (càng lo mất việc)
      -> concern càng cao, nên đảo chiều (1 - normalize) trước khi dùng.
      Giả định thang đo: rating cao = cảm thấy AN TOÀN hơn; nếu bảng câu hỏi
      gốc của WORKBank định nghĩa ngược lại, chỉ cần đảo dấu ở bước này.
    - Enjoyment_Attachment: Enjoyment Rating càng cao -> người lao động càng
      thích task -> càng không muốn nhường cho AI -> chuẩn hóa trực tiếp
      (không đảo chiều).
    - HumanAgency_Resistance: trung bình tỷ lệ worker nêu lý do Control /
      Empathy / Ethical khi muốn giữ vai trò con người (đã là tỷ lệ 0-1 sẵn
      từ TV1, chuẩn hóa lại theo phân bố của tập task IT để đồng nhất thang
      đo với 3 thành phần còn lại).
    """
    out = df.copy()

    raw_gap = out["Expert_Automation Capacity Rating"] - out["Worker_Automation Desire Rating"]
    out["Capacity_Desire_Gap_Raw"] = raw_gap
    out["Capacity_Desire_Gap_Norm"] = _minmax_normalize(raw_gap.clip(lower=0))

    out["JobSecurity_Concern_Norm"] = 1 - _minmax_normalize(out["Worker_Job Security Rating"])
    out["Enjoyment_Attachment_Norm"] = _minmax_normalize(out["Worker_Enjoyment Rating"])

    human_agency_raw = out[HUMAN_AGENCY_RESISTANCE_COLS].mean(axis=1)
    out["HumanAgency_Resistance_Raw"] = human_agency_raw
    out["HumanAgency_Resistance_Norm"] = _minmax_normalize(human_agency_raw)

    return out


def compute_friction_score(df: pd.DataFrame) -> pd.DataFrame:
    """Cộng có trọng số 4 thành phần -> Friction Score thang điểm 0-100,
    kèm cột 'Lý do chính' (thành phần đóng góp nhiều nhất vào điểm)."""
    out = df.copy()

    contrib = pd.DataFrame({
        "Chênh lệch AI làm được vs người lao động muốn": WEIGHT_CAPACITY_DESIRE_GAP * out["Capacity_Desire_Gap_Norm"],
        "Lo ngại mất việc (Job Security)": WEIGHT_JOB_SECURITY * out["JobSecurity_Concern_Norm"],
        "Gắn bó/yêu thích task (Enjoyment)": WEIGHT_ENJOYMENT * out["Enjoyment_Attachment_Norm"],
        "Muốn giữ vai trò con người (Control/Empathy/Ethical)": WEIGHT_HUMAN_AGENCY * out["HumanAgency_Resistance_Norm"],
    })

    out["Friction Score"] = (contrib.sum(axis=1) * 100).round(2)
    out["Lý do chính"] = contrib.idxmax(axis=1)

    threshold = out["Friction Score"].quantile(RED_FLAG_PERCENTILE)
    out["Canh_Bao"] = np.where(out["Friction Score"] >= threshold, "Đỏ", "Xanh")
    logger.info(
        "friction_score: nguong canh bao do = %.2f diem (top %.0f%%), "
        "%s/%s task duoc gan co Do.",
        threshold, (1 - RED_FLAG_PERCENTILE) * 100,
        int((out["Canh_Bao"] == "Đỏ").sum()), len(out),
    )
    return out


def build_friction_table(master: pd.DataFrame) -> pd.DataFrame:
    """Pipeline con: lọc task đủ điều kiện -> tính component -> tính điểm
    -> chọn cột output cuối cùng cho Tab 1 Dashboard."""
    scoreable = filter_scoreable_tasks(master)
    with_components = compute_friction_components(scoreable)
    scored = compute_friction_score(with_components)

    cols = [
        "Task ID", "Occupation (O*NET-SOC Title)", "Task",
        "Expert_Automation Capacity Rating", "Worker_Automation Desire Rating",
        "Capacity_Desire_Gap_Raw", "Worker_Job Security Rating", "Worker_Enjoyment Rating",
        "HumanAgency_Resistance_Raw", "Friction Score", "Canh_Bao", "Lý do chính",
        "Expert_N_Raters", "Worker_N_Respondents",
    ]
    return scored[cols].sort_values("Friction Score", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4. PHÂN TÍCH RỦI RO THEO NHÓM (dùng it_worker_level.csv)
# ---------------------------------------------------------------------------
def build_friction_by_group(friction_table: pd.DataFrame, worker_level: pd.DataFrame) -> pd.DataFrame:
    """Gắn Friction Score (cấp Task) vào từng dòng worker-level (đã có sẵn
    nhân khẩu học/thái độ AI từ TV1), rồi gộp trung bình theo từng nhóm
    (AI Suffering Attitude, AI Job Importance Attitude, AI Tedious Work
    Attitude, Experience) để TV4 giải thích 'vì sao' friction cao ở nhóm nào.

    LƯU Ý: merge theo Task ID (không phải User ID), vì Friction Score là chỉ
    số cấp TASK; mỗi worker trong it_worker_level.csv sẽ nhận cùng 1 điểm
    Friction Score với các worker khác từng chấm cùng task đó.
    """
    merged = worker_level.merge(
        friction_table[["Task ID", "Friction Score", "Canh_Bao"]],
        on="Task ID", how="inner",
    )

    rows = []
    for group_col in GROUP_BY_COLS:
        agg = merged.groupby(group_col, observed=True).agg(
            Avg_Friction_Score=("Friction Score", "mean"),
            Pct_Canh_Bao_Do=("Canh_Bao", lambda s: round((s == "Đỏ").mean() * 100, 1)),
            N_Worker_Responses=("Friction Score", "size"),
        ).reset_index()
        agg.insert(0, "Nhom_Phan_Tich", group_col)
        agg = agg.rename(columns={group_col: "Gia_Tri"})
        rows.append(agg)

    out = pd.concat(rows, ignore_index=True)
    return out.sort_values(["Nhom_Phan_Tich", "Avg_Friction_Score"], ascending=[True, False]).reset_index(drop=True)


# ===================
# 5. DATA DICTIONARY
# ===================
def build_data_dictionary() -> pd.DataFrame:
    """Giải thích ý nghĩa các cột chính trong friction_score.csv và
    friction_score_by_group.csv, để TV2/TV4 dùng lại không cần hỏi lại TV3."""
    rows = [
        ("Task ID / Occupation / Task", "friction_score", "Định danh task, giữ nguyên từ it_master.csv."),
        ("Capacity_Desire_Gap_Raw", "friction_score", "Expert_Automation Capacity Rating trừ Worker_Automation Desire Rating (chưa chuẩn hóa); dương = AI làm được nhiều hơn mức worker muốn nhường."),
        ("HumanAgency_Resistance_Raw", "friction_score", "Trung bình tỷ lệ worker nêu lý do Control/Empathy/Ethical để giữ vai trò con người (0-1)."),
        ("Friction Score", "friction_score", "Điểm lực cản tổng hợp, thang 0-100, = 40% Capacity-Desire Gap + 20% Job Security Concern + 20% Enjoyment Attachment + 20% Human Agency Resistance (mỗi thành phần đã min-max normalize)."),
        ("Canh_Bao", "friction_score", "'Đỏ' nếu Friction Score nằm trong top 25% cao nhất của các task IT đủ dữ liệu, ngược lại 'Xanh'."),
        ("Lý do chính", "friction_score", "Thành phần đóng góp nhiều điểm nhất (sau khi nhân trọng số) vào Friction Score của task đó."),
        ("Expert_N_Raters / Worker_N_Respondents", "friction_score", "Số lượng chuyên gia / worker đã chấm task - dùng đánh giá độ tin cậy của điểm."),
        ("Nhom_Phan_Tich", "friction_score_by_group", "Tên biến nhân khẩu học/thái độ dùng để nhóm (vd 'AI Suffering Attitude')."),
        ("Gia_Tri", "friction_score_by_group", "Giá trị cụ thể của biến nhóm (vd 'Agree', 'Disagree')."),
        ("Avg_Friction_Score", "friction_score_by_group", "Friction Score trung bình (tính trên các worker-response thuộc nhóm này)."),
        ("Pct_Canh_Bao_Do", "friction_score_by_group", "% worker-response thuộc nhóm này rơi vào task có cảnh báo Đỏ."),
        ("N_Worker_Responses", "friction_score_by_group", "Số lượng worker-response thuộc nhóm này (mẫu số của trung bình)."),
    ]
    return pd.DataFrame(rows, columns=["Cot", "Xuat_hien_trong_file", "Y_nghia"])


# ====================
# 6. MAIN PIPELINE
# ====================
def build_friction_outputs() -> dict[str, pd.DataFrame]:
    """Chạy toàn bộ pipeline: load -> lọc -> tính component -> tính điểm ->
    phân tích theo nhóm.

    Returns
    -------
    dict[str, pd.DataFrame]
        {"friction_score": ..., "friction_score_by_group": ...}
    """
    data = load_processed_data()
    friction_table = build_friction_table(data["master"])
    by_group = build_friction_by_group(friction_table, data["worker_level"])
    return {"friction_score": friction_table, "friction_score_by_group": by_group}


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    DICTIONARY_DIR.mkdir(parents=True, exist_ok=True)

    tables = build_friction_outputs()

    # Dataset chính cho Dashboard
    friction_path = PROCESSED_DIR / "friction_score.csv"

    # Output phục vụ phân tích
    group_path = ANALYSIS_DIR / "friction_score_by_group.csv"

    # Data dictionary
    dict_path = DICTIONARY_DIR / "friction_score_data_dictionary.csv"

    tables["friction_score"].to_csv(
        friction_path,
        index=False,
        encoding="utf-8-sig",
    )

    tables["friction_score_by_group"].to_csv(
        group_path,
        index=False,
        encoding="utf-8-sig",
    )

    build_data_dictionary().to_csv(
        dict_path,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"[OK] Friction Score -> {friction_path}")
    print(f"[OK] Group Analysis -> {group_path}")
    print(f"[OK] Data Dictionary -> {dict_path}")


if __name__ == "__main__":
    main()