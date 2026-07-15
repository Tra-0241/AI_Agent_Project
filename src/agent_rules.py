"""
agent_rules.py
Phụ trách: Thành viên 4 - Product/Dashboard Developer

Bộ luật gợi ý vai trò AI Agent phù hợp dựa trên Reasons for Automation Desire,
và gợi ý kỹ năng con người cần nâng cấp dựa trên Human Agency Scale Rating cao.
"""

import pandas as pd

# Bộ luật: (điều kiện cờ Automation Desire) -> gợi ý vai trò AI Agent
AGENT_SUGGESTION_RULES = [
    (
        {"Reasons for Automation Desire - Repetitive", "Reasons for Automation Desire - Human Error"},
        "Trợ lý kiểm tra lỗi / QA Agent tự động",
    ),
    (
        {"Reasons for Automation Desire - Stress", "Reasons for Automation Desire - Difficulty"},
        "Trợ lý xử lý tác vụ khó / giảm tải công việc",
    ),
    (
        {"Reasons for Automation Desire - Scale"},
        "Agent xử lý hàng loạt / batch processing",
    ),
    (
        {"Reasons for Automation Desire - Free Time"},
        "Trợ lý tự động hóa tác vụ định kỳ (scheduling/reporting Agent)",
    ),
]

# Kỹ năng con người gợi ý nâng cấp khi Human Agency Scale Rating cao
HUMAN_SKILL_SUGGESTIONS = {
    "Reasons for Human Agency - Empathy": "Giao tiếp & thấu cảm với khách hàng/đồng nghiệp",
    "Reasons for Human Agency - Dynamic": "Xử lý tình huống phức tạp, thay đổi linh hoạt",
    "Reasons for Human Agency - Domain Knowledge": "Đào sâu chuyên môn ngành, ra quyết định dựa trên kinh nghiệm",
    "Reasons for Human Agency - Control": "Kỹ năng giám sát, kiểm soát chất lượng đầu ra AI",
    "Reasons for Human Agency - Quality Oversight": "Review & đảm bảo chất lượng (QA cấp cao)",
    "Reasons for Human Agency - Ethical": "Ra quyết định đạo đức / tuân thủ",
}

HUMAN_AGENCY_HIGH_THRESHOLD = 4  # trên thang 1-5, ví dụ


def suggest_agent_role(row: pd.Series) -> str:
    """Gợi ý vai trò AI Agent dựa trên các cờ Reasons for Automation Desire đang bật."""
    active_flags = {col for col in row.index if col.startswith("Reasons for Automation Desire") and row.get(col)}

    best_match, best_overlap = "Chưa xác định - cần xem xét thủ công", 0
    for rule_flags, suggestion in AGENT_SUGGESTION_RULES:
        overlap = len(rule_flags & active_flags)
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = suggestion

    return best_match


def suggest_human_skills(row: pd.Series) -> list[str]:
    """Gợi ý kỹ năng con người cần nâng cấp khi Human Agency Scale Rating cao."""
    if (row.get("Human Agency Scale Rating", 0) or 0) < HUMAN_AGENCY_HIGH_THRESHOLD:
        return []

    return [
        suggestion
        for flag_col, suggestion in HUMAN_SKILL_SUGGESTIONS.items()
        if row.get(flag_col, False)
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
