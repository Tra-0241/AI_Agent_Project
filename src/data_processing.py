"""
data_processing.py
Phụ trách: Thành viên 1 - Data Engineer

Đọc 4 file CSV từ WORKBank, merge theo Task ID / User ID, lọc riêng các
Occupation thuộc khối IT, làm sạch dữ liệu và xuất ra:
    data/processed/it_master.csv        -> input cho TV2 (ROI Index) và TV3 (Friction Score)
    data/processed/it_worker_level.csv  -> input phụ cho TV3 khi cần breakdown theo
                                            nhân khẩu học / thái độ AI của từng worker

Cách chạy:
    python data_processing.py
(mặc định đọc từ ../data/raw và ghi ra ../data/processed so với vị trí file này;
chỉnh RAW_DIR / PROCESSED_DIR bên dưới nếu cấu trúc repo khác)
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


# ---------------------------------------------------------------------------
# 0. DANH SÁCH NGHỀ THUỘC KHỐI IT
# ---------------------------------------------------------------------------
# Lọc theo mã O*NET-SOC Code (đáng tin cậy hơn lọc theo tên chuỗi, vì tên
# occupation có thể gõ sai/khác hoa-thường). Nhóm chuẩn "Computer
# Occupations" của SOC là 15-1200 -> 15-1299, bổ sung 11-3021.00 (Computer
# and Information Systems Managers) vì đây là quản lý trực tiếp khối IT.
#
# Các nghề CÓ chữ "Computer" trong tên nhưng KHÔNG thuộc khối IT vận hành/
# phát triển phần mềm nên KHÔNG đưa vào danh sách:
#   - Computer Hardware Engineers (17-2061.00)                -> kỹ thuật phần cứng
#   - Computer Science Teachers, Postsecondary (25-1021.00)   -> giáo dục
#   - Computer, Automated Teller, and Office Machine Repairers (49-2011.00) -> sửa chữa thiết bị
#   - Computer Numerically Controlled Tool Operators/Programmers (51-91xx) -> vận hành máy CNC
IT_OCCUPATION_SOC_CODES: dict[str, str] = {
    "11-3021.00": "Computer and Information Systems Managers",
    "15-1211.00": "Computer Systems Analysts",
    "15-1212.00": "Information Security Analysts",
    "15-1221.00": "Computer and Information Research Scientists",
    "15-1231.00": "Computer Network Support Specialists",
    "15-1232.00": "Computer User Support Specialists",
    "15-1241.00": "Computer Network Architects",
    "15-1242.00": "Database Administrators",
    "15-1243.00": "Database Architects",
    "15-1243.01": "Data Warehousing Specialists",
    "15-1244.00": "Network and Computer Systems Administrators",
    "15-1251.00": "Computer Programmers",
    "15-1253.00": "Software Quality Assurance Analysts and Testers",
    "15-1254.00": "Web Developers",
    "15-1299.01": "Web Administrators",
    "15-1299.02": "Geographic Information Systems Technologists and Technicians",
    "15-1299.08": "Computer Systems Engineers/Architects",
    "15-1299.09": "Information Technology Project Managers",
}
IT_OCCUPATION_TITLES = set(IT_OCCUPATION_SOC_CODES.values())

REASON_AUTO_DESIRE_COLS = [
    "Reasons for Automation Desire - Free Time",
    "Reasons for Automation Desire - Repetitive",
    "Reasons for Automation Desire - Human Error",
    "Reasons for Automation Desire - Stress",
    "Reasons for Automation Desire - Difficulty",
    "Reasons for Automation Desire - Scale",
]

REASON_HUMAN_AGENCY_COLS = [
    "Reasons for Human Agency - Physical",
    "Reasons for Human Agency - Control",
    "Reasons for Human Agency - Domain Knowledge",
    "Reasons for Human Agency - Empathy",
    "Reasons for Human Agency - Quality Oversight",
    "Reasons for Human Agency - Dynamic",
    "Reasons for Human Agency - Ethical",
]

# Các cột trùng tên giữa expert_rated (chuyên gia chấm) và
# domain_worker_desires (worker tự chấm) - cần prefix riêng để tránh đè cột.
EXPERT_SHARED_COLS = [
    "Automation Capacity Rating",
    "Physical Action Requirement",
    "Involved Uncertainty",
    "Domain Expertise Requirement",
    "Interpersonal Communication Requirement",
    "Human Agency Scale Rating",
]

WORKER_SHARED_COLS = [
    "Automation Desire Rating",
    "Time",
    "Core Skill Rating",
    "Job Security Rating",
    "Enjoyment Rating",
    "Physical Action Requirement",
    "Interpersonal Communication Requirement",
    "Involved Uncertainty",
    "Domain Expertise Requirement",
    "Human Agency Scale Rating",
]


# ---------------------------------------------------------------------------
# 1. LOAD
# ---------------------------------------------------------------------------
def load_raw_data() -> dict[str, pd.DataFrame]:
    """Đọc 4 file CSV gốc từ data/raw/.

    Returns
    -------
    dict[str, pd.DataFrame]
        {"task": ..., "expert": ..., "desires": ..., "metadata": ...} - dữ liệu thô.
    """
    data = {
        "task": pd.read_csv(RAW_DIR / "task_statement_with_metadata.csv"),
        "expert": pd.read_csv(RAW_DIR / "expert_rated_technological_capability.csv"),
        "desires": pd.read_csv(RAW_DIR / "domain_worker_desires.csv"),
        "metadata": pd.read_csv(RAW_DIR / "domain_worker_metadata.csv"),
    }
    logger.info(
        "Loaded raw shapes -> task:%s expert:%s desires:%s metadata:%s",
        data["task"].shape, data["expert"].shape, data["desires"].shape, data["metadata"].shape,
    )
    return data


# ---------------------------------------------------------------------------
# 2. CLEANING HELPERS
# ---------------------------------------------------------------------------
def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Loại các dòng trùng hoàn toàn trong một DataFrame bất kỳ.

    Helper nhỏ này giữ API mà bộ test và notebook cũ đang sử dụng; các hàm
    làm sạch theo từng nguồn dữ liệu bên dưới vẫn chịu trách nhiệm chuẩn hóa
    schema chuyên biệt.
    """
    return df.drop_duplicates().reset_index(drop=True)


def _parse_str_list(value) -> list:
    """Chuyển chuỗi dạng "['a', 'b']" thành list Python thật.

    Cột 'Skill' và 'Skill ID (O*NET Generalized Work Activity ID)' được lưu
    dưới dạng chuỗi biểu diễn list. Hàm parse an toàn, trả [] nếu rỗng/hỏng.
    """
    if pd.isna(value):
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = ast.literal_eval(value)
        return list(parsed) if isinstance(parsed, (list, tuple)) else [parsed]
    except (ValueError, SyntaxError):
        return [value]


def _clean_other_reason_text(value):
    """Chuẩn hóa cột tự do 'Other Reason for ...'.

    Khi worker KHÔNG điền lý do khác, giá trị gốc là chuỗi "FALSE" (không
    phải NaN, không phải boolean False thật) -> convert về NaN thực sự để
    không bị hiểu nhầm là một lý do có nội dung.
    """
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    return np.nan if (text.upper() == "FALSE" or text == "") else text


def _clean_zip(value):
    """Chuẩn hóa Zip Code: giữ nguyên dạng ZIP+4 (vd '85023-6767'),
    đệm 0 cho ZIP 5 số bị đọc thành số (vd 1010 -> '01010')."""
    if pd.isna(value):
        return np.nan
    s = str(value).strip()
    if "-" in s:
        return s
    try:
        return str(int(float(s))).zfill(5)
    except ValueError:
        return s


def clean_task_statement(task: pd.DataFrame) -> pd.DataFrame:
    """Làm sạch bảng task_statement_with_metadata.

    - Ép kiểu Task ID (int), Occupation/O*NET-SOC Code (strip khoảng trắng).
    - Parse Date (MM/YYYY) -> datetime.
    - Parse cột dạng "list-as-string" (Skill, Skill ID) thành list rồi
      join lại bằng ';' để lưu CSV an toàn.
    - Gắn cờ Wage_Missing/Employment_Missing thay vì tự ý impute, vì đây
      là input trực tiếp cho công thức ROI của TV2.
    """
    df = task.copy()
    df["O*NET-SOC Code"] = df["O*NET-SOC Code"].str.strip()
    df["Occupation (O*NET-SOC Title)"] = df["Occupation (O*NET-SOC Title)"].str.strip()
    df["Task ID"] = df["Task ID"].astype("int64")
    df["Task"] = df["Task"].str.strip()
    df["Task Type"] = df["Task Type"].str.strip().astype("category")
    df["Date"] = pd.to_datetime(df["Date"], format="%m/%Y", errors="coerce")

    for col in ["Category", "Frequency", "Importance", "Relevance",
                "Occupation Mean Annual Wage", "Occupation Employment"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    skill_list = df["Skill (O*NET Work Activity)"].apply(_parse_str_list)
    skill_id_list = df["Skill ID (O*NET Generalized Work Activity ID)"].apply(_parse_str_list)
    df["Skill (O*NET Work Activity)"] = skill_list.apply(lambda lst: "; ".join(lst))
    df["Skill ID (O*NET Generalized Work Activity ID)"] = skill_id_list.apply(lambda lst: "; ".join(lst))

    df["Wage_Missing"] = df["Occupation Mean Annual Wage"].isna()
    df["Employment_Missing"] = df["Occupation Employment"].isna()

    n_missing = int(df["Wage_Missing"].sum())
    if n_missing:
        logger.info(
            "task_statement: %s/%s dong thieu Occupation Mean Annual Wage "
            "(giu NaN + flag Wage_Missing=True, KHONG impute).", n_missing, len(df),
        )
    return df


def clean_expert_rated(expert: pd.DataFrame) -> pd.DataFrame:
    """Làm sạch bảng expert_rated_technological_capability.

    - Ép kiểu Task ID (int), User ID (str), Date (YYYY/M/D -> datetime).
    - Ép các cột rating về numeric.
    - Loại dòng trùng lặp hoàn toàn (lỗi nhập liệu, không phải 2 lượt chấm khác nhau).
    """
    df = expert.copy()
    df["Task ID"] = df["Task ID"].astype("int64")
    df["Occupation (O*NET-SOC Title)"] = df["Occupation (O*NET-SOC Title)"].str.strip()
    df["User ID"] = df["User ID"].astype(str).str.strip()
    df["Date"] = pd.to_datetime(df["Date"], format="%Y/%m/%d", errors="coerce")

    for col in EXPERT_SHARED_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    before = len(df)
    df = df.drop_duplicates()
    if len(df) != before:
        logger.info("expert_rated: da loai %s dong trung lap hoan toan.", before - len(df))
    return df


def clean_domain_worker_desires(desires: pd.DataFrame) -> pd.DataFrame:
    """Làm sạch bảng domain_worker_desires.

    - Ép kiểu Task ID (int), User ID (str), Date (datetime).
    - Ép các cột Reason (Automation Desire / Human Agency) về bool thật.
    - Chuẩn hóa 2 cột tự do 'Other Reason for ...' ("FALSE" chuỗi -> NaN).
    - Ép các cột rating số về numeric.
    """
    df = desires.copy()
    df["Task ID"] = df["Task ID"].astype("int64")
    df["Occupation (O*NET-SOC Title)"] = df["Occupation (O*NET-SOC Title)"].str.strip()
    df["User ID"] = df["User ID"].astype(str).str.strip()
    df["Date"] = pd.to_datetime(df["Date"], format="%Y/%m/%d", errors="coerce")

    for col in REASON_AUTO_DESIRE_COLS + REASON_HUMAN_AGENCY_COLS:
        df[col] = df[col].astype(bool)

    df["Other Reason for Automation Desire"] = df["Other Reason for Automation Desire"].apply(_clean_other_reason_text)
    df["Other Reason for Human Agency"] = df["Other Reason for Human Agency"].apply(_clean_other_reason_text)

    numeric_cols = [
        "Automation Desire Rating", "Time", "Core Skill Rating", "Job Security Rating",
        "Enjoyment Rating", "Physical Action Requirement", "Interpersonal Communication Requirement",
        "Involved Uncertainty", "Domain Expertise Requirement", "Human Agency Scale Rating",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["Self-reported Expertise"] = df["Self-reported Expertise"].str.strip().astype("category")

    before = len(df)
    df = df.drop_duplicates()
    if len(df) != before:
        logger.info("domain_worker_desires: da loai %s dong trung lap hoan toan.", before - len(df))
    return df


def clean_domain_worker_metadata(metadata: pd.DataFrame) -> pd.DataFrame:
    """Làm sạch bảng domain_worker_metadata.

    - Ép kiểu User ID (str), chuẩn hóa Zip Code (giữ string, không ép int cứng).
    - Cột 'LLM Usage by Type - *' bị thiếu (~272 dòng, do worker chọn
      "không dùng LLM trong công việc" ở câu hỏi trước) -> điền
      "Not Applicable" thay vì để NaN, tránh nhầm là thiếu dữ liệu.
    """
    df = metadata.copy()
    df["User ID"] = df["User ID"].astype(str).str.strip()
    df["Occupation (O*NET-SOC Title)"] = df["Occupation (O*NET-SOC Title)"].str.strip()
    df["Zip Code"] = df["Zip Code"].apply(_clean_zip)

    llm_type_cols = [c for c in df.columns if c.startswith("LLM Usage by Type")]
    df[llm_type_cols] = df[llm_type_cols].fillna("Not Applicable")

    category_cols = [
        "Gender", "Race", "Income", "Education", "Experience",
        "AI Tedious Work Attitude", "AI Job Importance Attitude",
        "AI Daily Interest Attitude", "AI Suffering Attitude",
        "Political Affiliation", "LLM Familiarity", "LLM Use in Work",
        "Recruitment Source",
    ]
    for col in category_cols:
        df[col] = df[col].astype("category")

    before = len(df)
    df = df.drop_duplicates(subset=["User ID"])
    if len(df) != before:
        logger.info("domain_worker_metadata: da loai %s dong User ID trung lap.", before - len(df))
    return df


# ---------------------------------------------------------------------------
# 3. IT FILTER + CONSISTENCY CHECK
# ---------------------------------------------------------------------------
def filter_it_occupations(df: pd.DataFrame, soc_col: str = "O*NET-SOC Code") -> pd.DataFrame:
    """Lọc các dòng thuộc khối nghề IT dựa trên IT_OCCUPATION_SOC_CODES.

    Ưu tiên lọc theo mã SOC (đáng tin cậy hơn tên chuỗi). Nếu bảng không có
    cột mã SOC (expert/desires chỉ có tên Occupation), lọc theo tên thay thế.
    """
    if soc_col in df.columns:
        mask = df[soc_col].isin(IT_OCCUPATION_SOC_CODES.keys())
    else:
        mask = df["Occupation (O*NET-SOC Title)"].isin(IT_OCCUPATION_TITLES)
    return df[mask].copy()


def check_task_occupation_consistency(task: pd.DataFrame, other: pd.DataFrame, other_name: str) -> pd.DataFrame:
    """Kiểm tra mismatch tên Occupation giữa task_statement và 1 bảng khác
    cho cùng Task ID (đề bài cảnh báo có thể có "Task ID ở desires nhưng
    Occupation ghi khác tên"). Chỉ log cảnh báo, KHÔNG tự sửa dữ liệu gốc.
    """
    left = task[["Task ID", "Occupation (O*NET-SOC Title)"]].drop_duplicates()
    right = other[["Task ID", "Occupation (O*NET-SOC Title)"]].drop_duplicates()
    merged = left.merge(right, on="Task ID", suffixes=("_task", f"_{other_name}"))
    mismatch = merged[
        merged["Occupation (O*NET-SOC Title)_task"] != merged[f"Occupation (O*NET-SOC Title)_{other_name}"]
    ]
    if len(mismatch):
        logger.warning(
            "Phat hien %s Task ID co ten Occupation KHONG khop giua task_statement va %s.",
            len(mismatch), other_name,
        )
    else:
        logger.info("Khong phat hien mismatch ten Occupation giua task_statement va %s.", other_name)
    return mismatch


# ---------------------------------------------------------------------------
# 4. AGGREGATION -> IT_MASTER (cấp Task)
# ---------------------------------------------------------------------------
# LƯU Ý QUAN TRỌNG: 1 Task ID có thể được NHIỀU expert và NHIỀU worker chấm.
# Nếu merge thẳng task -> expert -> desires theo Task ID mà KHÔNG aggregate
# trước, sẽ tạo tích Descartes (1 task x 3 expert x 5 worker = 15 dòng thay
# vì đại diện đúng cho 1 task) làm sai lệch toàn bộ ROI/Friction ở bước sau.
# Vì vậy bắt buộc phải groupby("Task ID") để aggregate expert và desires
# VỀ CẤP TASK trước khi merge vào task_statement.
def aggregate_expert_by_task(expert_it: pd.DataFrame) -> pd.DataFrame:
    """Gộp expert_rated_technological_capability theo Task ID: lấy trung
    bình các rating + số lượng chuyên gia đã chấm."""
    agg = expert_it.groupby("Task ID")[EXPERT_SHARED_COLS].mean(numeric_only=True)
    agg.columns = [f"Expert_{c}" for c in agg.columns]
    agg["Expert_N_Raters"] = expert_it.groupby("Task ID").size()
    return agg.reset_index()


def aggregate_desires_by_task(desires_it: pd.DataFrame) -> pd.DataFrame:
    """Gộp domain_worker_desires theo Task ID: trung bình rating số, tỷ lệ
    True cho các cờ Reason, và số lượng worker đã trả lời."""
    numeric_agg = desires_it.groupby("Task ID")[WORKER_SHARED_COLS].mean(numeric_only=True)
    numeric_agg.columns = [f"Worker_{c}" for c in numeric_agg.columns]

    reason_auto = desires_it.groupby("Task ID")[REASON_AUTO_DESIRE_COLS].mean()
    reason_auto.columns = ["Share_" + c.replace("Reasons for Automation Desire - ", "AutoDesire_") for c in reason_auto.columns]

    reason_agency = desires_it.groupby("Task ID")[REASON_HUMAN_AGENCY_COLS].mean()
    reason_agency.columns = ["Share_" + c.replace("Reasons for Human Agency - ", "HumanAgency_") for c in reason_agency.columns]

    out = numeric_agg.join(reason_auto).join(reason_agency)
    out["Worker_N_Respondents"] = desires_it.groupby("Task ID").size()
    return out.reset_index()


def build_it_master(task_it: pd.DataFrame, expert_agg: pd.DataFrame, desires_agg: pd.DataFrame) -> pd.DataFrame:
    """Ghép task_it (đã lọc IT + làm sạch) với 2 bảng đã aggregate theo
    Task ID -> bảng master ở cấp TASK (1 dòng / Task ID).

    Dùng left join từ task_it để giữ toàn bộ task IT, kể cả task chưa được
    expert/worker nào chấm (cột rating sẽ là NaN, đánh dấu qua
    Has_Expert_Rating / Has_Worker_Rating).
    """
    master = task_it.merge(expert_agg, on="Task ID", how="left")
    master = master.merge(desires_agg, on="Task ID", how="left")
    master["Has_Expert_Rating"] = master["Expert_N_Raters"].fillna(0) > 0
    master["Has_Worker_Rating"] = master["Worker_N_Respondents"].fillna(0) > 0
    return master.sort_values(["Occupation (O*NET-SOC Title)", "Task ID"]).reset_index(drop=True)


def build_it_worker_level(desires_it: pd.DataFrame, metadata_clean: pd.DataFrame) -> pd.DataFrame:
    """Ghép domain_worker_desires (đã lọc IT) với domain_worker_metadata
    theo User ID -> bảng chi tiết cấp (Task ID x User ID), giữ nguyên nhân
    khẩu học / thái độ AI của từng worker.

    LƯU Ý: đây là merge THEO USER ID CỦA WORKER (UUID trong desires/metadata),
    HOÀN TOÀN KHÁC với User ID của expert (dạng tên mã như "RedTiger") trong
    file expert_rated_technological_capability -> KHÔNG được lẫn 2 bảng này
    khi merge, nếu không kết quả join sẽ sai/rỗng.
    """
    meta_cols = [c for c in metadata_clean.columns if c != "Occupation (O*NET-SOC Title)"]
    merged = desires_it.merge(metadata_clean[meta_cols], on="User ID", how="left")
    return merged.sort_values(["Task ID", "User ID"]).reset_index(drop=True)

def build_data_dictionary() -> pd.DataFrame:
    """Tạo bảng giải thích ý nghĩa từng cột chính trong it_master.csv và
    it_worker_level.csv, để TV2/TV3/TV4 dùng lại không cần hỏi lại TV1.
    """
    rows = [
        ("Task ID", "it_master, it_worker_level", "Mã định danh duy nhất của 1 task (giữ nguyên từ WORKBank)."),
        ("O*NET-SOC Code", "it_master", "Mã nghề chuẩn O*NET-SOC, dùng để xác định nghề IT."),
        ("Occupation (O*NET-SOC Title)", "it_master, it_worker_level", "Tên nghề theo O*NET-SOC Title."),
        ("Task", "it_master, it_worker_level", "Nội dung mô tả công việc cụ thể (task statement)."),
        ("Occupation Mean Annual Wage", "it_master", "Lương trung bình năm (USD) của nghề - dùng tính ROI."),
        ("Occupation Employment", "it_master", "Số lượng nhân sự đang làm nghề này - dùng tính ROI theo quy mô."),
        ("Wage_Missing / Employment_Missing", "it_master", "Cờ True nếu Wage/Employment gốc bị thiếu - TV2 tự xử lý, KHÔNG tự impute."),
        ("Frequency", "it_master", "Tần suất xuất hiện của task trong công việc."),
        ("Importance", "it_master", "Mức độ quan trọng của task."),
        ("Relevance", "it_master", "Mức độ liên quan/phổ biến của task với nghề (0-100)."),
        ("Expert_Automation Capacity Rating", "it_master", "Trung bình điểm chuyên gia chấm AI có thể làm được task (1-5, cao = AI làm tốt)."),
        ("Expert_Human Agency Scale Rating", "it_master", "Trung bình điểm chuyên gia chấm mức độ cần con người kiểm soát/tham gia."),
        ("Expert_N_Raters", "it_master", "Số lượng chuyên gia đã chấm task này."),
        ("Worker_Automation Desire Rating", "it_master, it_worker_level", "Mức độ NGƯỜI LAO ĐỘNG muốn tự động hóa task (1-5)."),
        ("Worker_Human Agency Scale Rating", "it_master, it_worker_level", "Mức độ worker cho rằng cần con người tham gia/kiểm soát."),
        ("Worker_Time", "it_master, it_worker_level", "Thời gian worker bỏ ra cho task - input tính giờ tiết kiệm được."),
        ("Worker_Job Security Rating", "it_master, it_worker_level", "Mức độ lo ngại mất việc - input tính Friction Score."),
        ("Worker_Enjoyment Rating", "it_master, it_worker_level", "Mức độ yêu thích task - input tính Friction Score."),
        ("Worker_N_Respondents", "it_master", "Số lượng worker đã tự đánh giá task này."),
        ("Share_AutoDesire_*", "it_master, it_worker_level (dạng bool)", "Tỷ lệ/cờ lý do MUỐN tự động hóa: Free Time, Repetitive, Human Error, Stress, Difficulty, Scale."),
        ("Share_HumanAgency_*", "it_master, it_worker_level (dạng bool)", "Tỷ lệ/cờ lý do MUỐN GIỮ con người: Physical, Control, Domain Knowledge, Empathy, Quality Oversight, Dynamic, Ethical."),
        ("Has_Expert_Rating / Has_Worker_Rating", "it_master", "Cờ True nếu task có ít nhất 1 lượt chấm - dùng lọc task đủ dữ liệu trước khi tính ROI/Friction."),
        ("Gender, Race, Age, Education, Experience, Income", "it_worker_level", "Nhân khẩu học worker - dùng phân tích rủi ro theo nhóm."),
        ("AI Suffering/Job Importance/Tedious/Daily Interest Attitude", "it_worker_level", "Thái độ chủ quan của worker với AI."),
        ("LLM Familiarity / LLM Use in Work / LLM Usage by Type - *", "it_worker_level", "Mức độ và cách worker đang dùng LLM trong công việc."),
    ]
    return pd.DataFrame(rows, columns=["Cot", "Xuat_hien_trong_file", "Y_nghia"])

# ---------------------------------------------------------------------------
# 5. MAIN PIPELINE
# ---------------------------------------------------------------------------
def build_master_table() -> dict[str, pd.DataFrame]:
    """Chạy toàn bộ pipeline: load -> clean -> filter IT -> aggregate -> merge.

    Returns
    -------
    dict[str, pd.DataFrame]
        {"it_master": ..., "it_worker_level": ...}
    """
    raw = load_raw_data()

    task_clean = clean_task_statement(raw["task"])
    expert_clean = clean_expert_rated(raw["expert"])
    desires_clean = clean_domain_worker_desires(raw["desires"])
    metadata_clean = clean_domain_worker_metadata(raw["metadata"])

    check_task_occupation_consistency(task_clean, expert_clean, "expert")
    check_task_occupation_consistency(task_clean, desires_clean, "desires")

    task_it = filter_it_occupations(task_clean)
    expert_it = filter_it_occupations(expert_clean)
    desires_it = filter_it_occupations(desires_clean)

    logger.info(
        "Sau khi loc IT -> task_it:%s expert_it:%s desires_it:%s "
        "(%s nghe IT / %s nghe tong, %s task IT / %s task tong)",
        task_it.shape, expert_it.shape, desires_it.shape,
        task_it["Occupation (O*NET-SOC Title)"].nunique(), task_clean["Occupation (O*NET-SOC Title)"].nunique(),
        task_it["Task ID"].nunique(), task_clean["Task ID"].nunique(),
    )

    expert_agg = aggregate_expert_by_task(expert_it)
    desires_agg = aggregate_desires_by_task(desires_it)

    it_master = build_it_master(task_it, expert_agg, desires_agg)
    it_worker_level = build_it_worker_level(desires_it, metadata_clean)

    return {"it_master": it_master, "it_worker_level": it_worker_level}


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    tables = build_master_table()

    master_path = PROCESSED_DIR / "it_master.csv"
    worker_path = PROCESSED_DIR / "it_worker_level.csv"
    dict_path = PROCESSED_DIR / "it_master_data_dictionary.csv"

    tables["it_master"].to_csv(master_path, index=False, encoding="utf-8-sig")
    tables["it_worker_level"].to_csv(worker_path, index=False, encoding="utf-8-sig")
    build_data_dictionary().to_csv(dict_path, index=False, encoding="utf-8-sig")

    print(f"[OK] Da xuat {len(tables['it_master']):,} dong ra {master_path}")
    print(f"[OK] Da xuat {len(tables['it_worker_level']):,} dong ra {worker_path}")
    print(f"[OK] Da xuat data dictionary ra {dict_path}") 


if __name__ == "__main__":
    main()
