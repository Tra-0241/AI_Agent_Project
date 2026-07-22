"""
agent_rules.py
Phụ trách: Thành viên 4 - Product/Dashboard Developer

Bộ luật gợi ý vai trò AI Agent phù hợp dựa trên tỷ lệ (Share_AutoDesire_*),
và gợi ý kỹ năng con người cần nâng cấp dựa trên Human Agency Scale Rating cao.

LƯU Ý: File này chạy trên it_master.csv (bảng đã gộp/aggregate theo Task của TV1)
"""

import pandas as pd

# Bộ luật: (điều kiện các cờ Share_AutoDesire_* đang chiếm tỷ lệ cao) -> gợi ý vai trò AI Agent
AGENT_SUGGESTION_RULES = [
    (
        {"Share_AutoDesire_Repetitive", "Share_AutoDesire_Human Error"},
        "Trợ lý kiểm tra lỗi / QA Agent tự động",
    ),
    (
        {"Share_AutoDesire_Stress", "Share_AutoDesire_Difficulty"},
        "Trợ lý xử lý tác vụ khó / giảm tải công việc",
    ),
    (
        {"Share_AutoDesire_Scale"},
        "Agent xử lý hàng loạt / batch processing",
    ),
    (
        {"Share_AutoDesire_Free Time"},
        "Trợ lý tự động hóa tác vụ định kỳ (scheduling/reporting Agent)",
    ),
]

# Kỹ năng con người gợi ý nâng cấp khi Human Agency Scale Rating cao
HUMAN_SKILL_SUGGESTIONS = {
    "Share_HumanAgency_Empathy": "Giao tiếp & thấu cảm với khách hàng/đồng nghiệp",
    "Share_HumanAgency_Dynamic": "Xử lý tình huống phức tạp, thay đổi linh hoạt",
    "Share_HumanAgency_Domain Knowledge": "Đào sâu chuyên môn ngành, ra quyết định dựa trên kinh nghiệm",
    "Share_HumanAgency_Control": "Kỹ năng giám sát, kiểm soát chất lượng đầu ra AI",
    "Share_HumanAgency_Quality Oversight": "Review & đảm bảo chất lượng (QA cấp cao)",
    "Share_HumanAgency_Ethical": "Ra quyết định đạo đức / tuân thủ",
}

# Ngưỡng để coi 1 lý do (Share_*) là "chiếm ưu thế" trong nhóm worker của task đó.
# Share_* là tỷ lệ 0-1; theo phân phối thực tế trong it_master.csv (mean ~0.31,
# 75th percentile ~0.5), 0.4 tương ứng mức "đáng kể, hơn khoảng 1/3 worker nêu lý do này".
SHARE_ACTIVE_THRESHOLD = 0.4

# Ngưỡng Human Agency Scale Rating để coi là "cao". Thang gốc là 1-5, nhưng vì
# it_master.csv là điểm trung bình đã gộp theo task, khoảng giá trị quan sát được
# hẹp hơn (~1.6 - 3.8, mean ~2.85). 3.2 tương ứng khoảng top một phần tư task có
# Human Agency cao nhất — nên cân nhắc lại ngưỡng này nếu phân phối dữ liệu thay đổi.
HUMAN_AGENCY_HIGH_THRESHOLD = 3.2

# Cột rating dùng để đánh giá "Human Agency cao" — có thể đổi thành cột Expert_
# hoặc lấy trung bình 2 cột nếu muốn kết hợp góc nhìn chuyên gia + worker.
HUMAN_AGENCY_RATING_COL = "Worker_Human Agency Scale Rating"


def suggest_agent_role(row: pd.Series) -> str:
    """Gợi ý vai trò AI Agent dựa trên các cột Share_AutoDesire_* vượt ngưỡng."""
    active_flags = {
        col
        for col in row.index
        if col.startswith("Share_AutoDesire_") and pd.notna(row[col]) and row[col] >= SHARE_ACTIVE_THRESHOLD
    }

    best_match, best_overlap = "Chưa xác định - cần xem xét thủ công", 0
    for rule_flags, suggestion in AGENT_SUGGESTION_RULES:
        overlap = len(rule_flags & active_flags)
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = suggestion

    return best_match


def suggest_human_skills(row: pd.Series) -> list[str]:
    """Gợi ý kỹ năng con người cần nâng cấp khi Human Agency Scale Rating cao."""
    rating = row.get(HUMAN_AGENCY_RATING_COL)
    if pd.isna(rating) or rating < HUMAN_AGENCY_HIGH_THRESHOLD:
        return []

    return [
        suggestion
        for flag_col, suggestion in HUMAN_SKILL_SUGGESTIONS.items()
        if pd.notna(row.get(flag_col)) and row.get(flag_col) >= SHARE_ACTIVE_THRESHOLD
    ]


def build_agent_recommendation_table(master: pd.DataFrame) -> pd.DataFrame:
    df = master.copy()
    df["Suggested AI Agent Role"] = df.apply(suggest_agent_role, axis=1)
    df["Suggested Human Skills"] = df.apply(lambda r: ", ".join(suggest_human_skills(r)) or "-", axis=1)

    cols = [
        "Occupation (O*NET-SOC Title)",
        "Task",
        "Suggested AI Agent Role",
        "Suggested Human Skills",
    ]
    return df[[c for c in cols if c in df.columns]].drop_duplicates()
