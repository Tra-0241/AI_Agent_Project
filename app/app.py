"""
app.py
Phụ trách: Thành viên 4 - Product/Dashboard Developer

Streamlit Dashboard 2 tab cho đề tài "AI Agent Deployment Blueprint":
- Tab 1 (Doanh nghiệp): bản đồ chiến lược ROI Index x Friction Score theo 4
  góc phần tư, KPI tổng quan, filter theo nghề / mức lương / mức rủi ro.
- Tab 2 (Nhân sự): gợi ý vai trò AI Agent & kỹ năng con người cần nâng cấp.

"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from ftfy import fix_text

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
DATA_DIR = ROOT_DIR / "data" / "processed"

load_dotenv(ROOT_DIR / ".env")

sys.path.insert(0, str(ROOT_DIR))
from src.agent_rules import build_agent_recommendation_table  # noqa: E402

# ---------------------------------------------------------------------------
# DESIGN TOKENS — nền sáng, accent gắn với ý nghĩa dữ liệu (không phải trang trí)
# ---------------------------------------------------------------------------
COLOR_BG = "#F5F7FB"
COLOR_SURFACE = "#FFFFFF"
COLOR_SIDEBAR_BG = "#F5F7FB"   # nền tím-xanh nhạt cho sidebar 
COLOR_BORDER = "#E3E8F0"
COLOR_INPUT_BORDER = "#D6DAF0"
COLOR_TEXT = "#101828"
COLOR_TEXT_MUTED = "#667085"
COLOR_ACCENT = "#293681"       # Indigo — thương hiệu chung của dashboard
COLOR_ROI_HIGH = "#0F766E"     # Teal — "Tự động hóa ngay" / vùng ưu tiên
COLOR_ROI_MED = "#D97706"      # Amber — "Cân nhắc" / cần thận trọng
COLOR_ROI_LOW = "#94A3B8"      # Gray — "Giữ nguyên / Theo dõi"
COLOR_ROI_NA = "#CBD5E1"       # Gray nhạt — "Chưa đủ dữ liệu"
COLOR_RISK_RED = "#DC2626"     # Đỏ — cảnh báo Friction cao
COLOR_RISK_GREEN = "#059669"   # Xanh — friction thấp, an toàn

STRATEGY_COLOR_MAP = {
    "Tự động hóa ngay": COLOR_ROI_HIGH,
    "Cân nhắc": COLOR_ROI_MED,
    "Giữ nguyên / Theo dõi": COLOR_ROI_LOW,
    "Chưa đủ dữ liệu": COLOR_ROI_NA,
}

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');

html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], p, span, label, div {{
    font-family: 'Inter', sans-serif;
}}
h1, h2, h3 {{
    font-family: 'Sora', sans-serif !important;
    color: {COLOR_TEXT};
}}
[data-testid="stAppViewContainer"] {{
    background-color: {COLOR_BG};
}}
[data-testid="stSidebar"] {{
    background-color: {COLOR_SIDEBAR_BG};
    border-right: 1px solid {COLOR_BORDER};
}}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    color: #000000 !important;
    font-weight: 700 !important;
}}
[data-testid="stSidebar"] label {{
    color: {COLOR_TEXT} !important;
    font-weight: 500;
    font-size: 0.95rem !important;
}}
/* Khung select / multiselect: nền trắng, viền mảnh, bo góc (giống mẫu tham khảo) */
[data-testid="stSidebar"] [data-baseweb="select"] > div {{
    background-color: {COLOR_SURFACE} !important;
    border: 1px solid {COLOR_INPUT_BORDER} !important;
    border-radius: 10px !important;
    font-size: 0.95rem !important;
}}
/* Chip đã chọn trong multiselect: màu xám trung tính thay vì indigo */
[data-testid="stSidebar"] [data-baseweb="tag"] {{
    background-color: #64748B !important;
    border-radius: 6px !important;
}}
[data-testid="stSidebar"] [data-baseweb="tag"] span {{
    color: #FFFFFF !important;
    font-size: 0.85rem !important;
}}
[data-testid="stSidebar"] [data-baseweb="tag"] svg {{
    fill: #FFFFFF !important;
}}

/* --- SLIDER: CSS dưới đây được viết đúng theo mã nguồn thật của Streamlit
   (đã tra trực tiếp trong file Slider.js đóng gói trong thư viện), không
   còn đoán mò data-testid/thuộc tính không tồn tại như 2 lần sửa trước. */

/* 1) Số hiển thị giá trị phía trên 2 núm kéo (vd 64990 / 187990):
   Streamlit gắn đúng data-testid="stSliderThumbValue" cho phần tử này. */
[data-testid="stSidebar"] [data-testid="stSliderThumbValue"] {{
    color: #111827 !important;
}}

/* 2) Đường line của slider: phần tử Track không có data-testid riêng,
   nhưng luôn đứng ngay TRƯỚC 2 núm kéo (role="slider") trong DOM, nên
   chọn nó bằng quan hệ "div đứng liền trước [role=slider]" thay vì đoán
   tên class (tên class do Streamlit build ra, đổi theo từng phiên bản). */
[data-testid="stSidebar"] [data-testid="stSlider"] div:has(+ [role="slider"]) {{
    background: #111827 !important;
}}

/* 3) Hai núm kéo (thumb) */
[data-testid="stSidebar"] [data-testid="stSlider"] [role="slider"] {{
    background-color: #111827 !important;
    border-color: #111827 !important;
}}
/* Bỏ padding-top mặc định của Streamlit để banner sát lên trên hơn */
.block-container {{
    padding-top: 1.6rem !important;
    padding-bottom: 2.5rem !important;
}}

/* --- HEADER / BANNER --- */
.app-banner {{
    background: linear-gradient(135deg, {COLOR_ACCENT} 0%, #1B2456 100%);
    border-radius: 16px;
    padding: 22px 28px;
    margin-bottom: 22px;
    box-shadow: 0 4px 14px rgba(41,54,129,0.18);
}}
.app-header {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 4px;
}}
.app-badge {{
    font-size: 1.35rem;
    line-height: 1;
}}
.app-header h1 {{
    color: #FFFFFF !important;
    font-size: 1.5rem !important;
    letter-spacing: -0.01em;
}}
.app-subtitle {{
    color: rgba(255,255,255,0.82);
    font-size: 0.92rem;
    max-width: 780px;
    line-height: 1.5;
    margin-top: 2px;
}}
.app-tags {{
    display: flex;
    gap: 8px;
    margin-top: 14px;
    flex-wrap: wrap;
}}
.app-tag {{
    background: rgba(255,255,255,0.12);
    color: #FFFFFF;
    font-size: 0.72rem;
    font-weight: 500;
    padding: 4px 10px;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.18);
}}

/* --- SECTION TITLE --- */
.section-block {{
    margin-top: 6px;
    margin-bottom: 4px;
}}
.section-title {{
    font-family: 'Sora', sans-serif;
    font-size: 1.05rem;
    font-weight: 600;
    color: {COLOR_TEXT};
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
}}
.section-icon {{ font-size: 1rem; }}
.section-rule {{
    height: 3px; width: 48px; border-radius: 2px;
    background: {COLOR_ACCENT};
    margin: 6px 0 16px 0;
}}

/* --- KPI CARDS --- */
.kpi-card {{
    background: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-top: 3px solid var(--accent, {COLOR_ACCENT});
    border-radius: 12px;
    padding: 14px 16px 16px 16px;
    box-shadow: 0 1px 2px rgba(16,24,40,0.04);
    margin-bottom: 14px;
    transition: box-shadow 0.15s ease, transform 0.15s ease;
}}
.kpi-card:hover {{
    box-shadow: 0 6px 16px rgba(16,24,40,0.09);
    transform: translateY(-1px);
}}
.kpi-top {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
}}
.kpi-label {{
    font-size: 0.70rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: {COLOR_TEXT_MUTED};
    font-weight: 600;
}}
.kpi-icon {{
    font-size: 1rem;
    opacity: 0.85;
}}
.kpi-value {{
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
    font-size: 1.65rem;
    color: {COLOR_TEXT};
    line-height: 1.1;
}}
.kpi-sub {{
    font-size: 0.74rem;
    color: {COLOR_TEXT_MUTED};
    margin-top: 4px;
}}

/* --- TABS: dạng segmented control --- */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    gap: 4px;
    background: {COLOR_BORDER}55;
    padding: 5px;
    border-radius: 12px;
    margin-bottom: 6px;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    height: 42px;
    border-radius: 9px !important;
    padding: 0 18px;
    background: transparent;
    color: {COLOR_TEXT_MUTED};
    font-weight: 600;
    font-size: 0.9rem;
    border: none !important;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    background: {COLOR_SURFACE} !important;
    color: {COLOR_ACCENT} !important;
    box-shadow: 0 1px 3px rgba(16,24,40,0.10);
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
    background-color: transparent !important;
}}

/* --- EXPANDER --- */
[data-testid="stExpander"] {{
    border: 1px solid {COLOR_BORDER} !important;
    border-radius: 10px !important;
    background: {COLOR_SURFACE};
    box-shadow: 0 1px 2px rgba(16,24,40,0.03);
}}
[data-testid="stExpander"] summary {{
    font-weight: 600;
    color: {COLOR_TEXT};
}}

/* --- DATAFRAME --- */
[data-testid="stDataFrame"] {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
    overflow: hidden;
}}

/* --- ALERTS (info/error) bo góc đồng bộ --- */
[data-testid="stAlert"] {{
    border-radius: 10px;
}}

/* --- SIDEBAR chi tiết --- */
.sidebar-title {{
    font-family: 'Sora', sans-serif;
    font-weight: 700;
    font-size: 1.15rem;
    color: {COLOR_TEXT};
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 2px;
}}
.sidebar-caption {{
    color: {COLOR_TEXT_MUTED};
    font-size: 0.88rem;
    margin-bottom: 16px;
}}
.sidebar-divider {{
    height: 1px;
    background: {COLOR_BORDER};
    margin: 16px 0 14px 0;
    border: none;
}}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
    background: {COLOR_SURFACE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 8px 10px;
    margin-top: 8px;
    font-size: 0.88rem !important;
}}

/* --- FOOTER --- */
.app-footer {{
    margin-top: 28px;
    padding-top: 14px;
    border-top: 1px solid {COLOR_BORDER};
    color: {COLOR_TEXT_MUTED};
    font-size: 0.78rem;
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 6px;
}}
</style>
"""

ID_COLS = ["Task ID", "Occupation (O*NET-SOC Title)", "Task"]


def repair_mojibake(value):
    """Repair one or more layers of UTF-8/Windows mojibake safely."""
    if not isinstance(value, str):
        return value
    return fix_text(value)


def read_processed_csv(path: Path) -> pd.DataFrame:
    """Read a processed CSV and normalize legacy mojibake in headers/values."""
    frame = pd.read_csv(path, encoding="utf-8-sig")
    frame.columns = [repair_mojibake(column) for column in frame.columns]
    text_columns = frame.select_dtypes(include=["object", "str"]).columns
    for column in text_columns:
        frame[column] = frame[column].map(repair_mojibake)
    return frame


# ---------------------------------------------------------------------------
# 1. LOAD & MERGE DỮ LIỆU
# ---------------------------------------------------------------------------
@st.cache_data
def load_merged_data() -> pd.DataFrame:
    """Merge 3 nguồn (agent_rules, roi_index, friction_score) thành 1 bảng.

    Dùng LEFT JOIN bắt đầu từ roi_index.csv (186 task, tập lớn nhất) để không
    âm thầm loại bỏ task chỉ vì thiếu Friction Score (TV3 lọc còn 131/186 task
    do yêu cầu đủ cả Expert lẫn Worker rating). Task thiếu Friction Score vẫn
    hiển thị trên Tab 1, nhưng được đánh dấu rõ "Chưa đủ dữ liệu" thay vì bị ẩn.
    """
    it_master = read_processed_csv(DATA_DIR / "it_master.csv")
    roi = read_processed_csv(DATA_DIR / "roi_index.csv")
    friction = read_processed_csv(DATA_DIR / "friction_score.csv")
    agent = build_agent_recommendation_table(it_master)

    friction_cols = ["Task ID", "Friction Score", "Canh_Bao", "Lý do chính"]
    merged = roi.merge(
        friction[friction_cols], on="Task ID", how="left", suffixes=("", "_friction")
    )
    merged = merged.merge(
        agent, on=["Occupation (O*NET-SOC Title)", "Task"], how="left"
    )

    merged["Canh_Bao"] = merged["Canh_Bao"].fillna("Chưa đủ dữ liệu")
    merged["Suggested AI Agent Role"] = merged["Suggested AI Agent Role"].fillna(
        "Chưa xác định - cần xem xét thủ công"
    )
    merged["Suggested Human Skills"] = merged["Suggested Human Skills"].fillna("-")

    return merged


def wage_bucket_bounds(df: pd.DataFrame) -> tuple[float, float]:
    wage = pd.to_numeric(df["Occupation Mean Annual Wage"], errors="coerce")
    return float(wage.min(skipna=True)), float(wage.max(skipna=True))


# ---------------------------------------------------------------------------
# 2. UI HELPERS
# ---------------------------------------------------------------------------
@st.cache_resource
def get_gemini_client(api_key: str):
    """Create one Gemini client and reuse it across Streamlit reruns."""
    from google import genai

    return genai.Client(api_key=api_key)


def build_action_plan_prompt(row: pd.Series) -> str:
    """Ground the LLM response in the selected task's calculated metrics."""

    def value(column: str, fallback: str = "Chưa có dữ liệu") -> str:
        result = row.get(column, fallback)
        return fallback if pd.isna(result) else str(result)

    return f"""
Bạn là chuyên gia triển khai AI Agent cho doanh nghiệp. Hãy tạo Action Plan thực tế,
ngắn gọn bằng tiếng Việt cho đúng một task dưới đây.

DỮ LIỆU ĐÃ ĐƯỢC TÍNH TOÁN (không được tự thay đổi hoặc bịa thêm chỉ số):
- Nghề nghiệp: {value("Occupation (O*NET-SOC Title)")}
- Task: {value("Task")}
- ROI Index: {value("ROI Index")}
- Vùng chiến lược: {value("Strategy Zone")}
- Friction Score: {value("Friction Score")}
- Cảnh báo Friction: {value("Canh_Bao")}
- Lý do chính: {value("Lý do chính")}
- Vai trò AI Agent gợi ý từ bộ luật: {value("Suggested AI Agent Role")}
- Kỹ năng con người cần nâng cấp: {value("Suggested Human Skills")}

Trả lời bằng Markdown và chỉ dùng đúng 5 mục sau. Giữ nguyên chính xác tên các
tiêu đề, diễn đạt tự nhiên, rõ ràng và phù hợp với người đọc trong doanh nghiệp:
### 1. Mục tiêu triển khai
Viết thật ngắn gọn trong 1-3 dòng, nêu trực tiếp kết quả cần cải thiện và không tự
bịa số phần trăm.

### 2. AI Agent sẽ hỗ trợ những gì?
Nêu rõ các công việc cụ thể AI Agent sẽ hỗ trợ. Tập trung vào chức năng và giá trị
mang lại; không trình bày giới hạn của AI Agent hoặc cơ chế ghi đè.

### 3. Lộ trình triển khai
Đưa ra 4-6 bước theo thứ tự, bắt đầu bằng thử nghiệm phạm vi nhỏ.

### 4. Con người giám sát và ra quyết định
Nêu những nội dung con người cần theo dõi, kiểm tra, phê duyệt và kỹ năng cần có.

### 5. Chỉ số cần theo dõi
Đề xuất KPI vận hành; nhắc lại ROI Index và Friction Score hiện có. Nếu một chỉ số
chưa có dữ liệu thì nói rõ là cần thu thập baseline, tuyệt đối không tự tạo số liệu.
Trong toàn bộ Action Plan, không đề cập cơ chế override hoặc cơ chế ghi đè.
""".strip()


def generate_action_plan(row: pd.Series) -> str:
    api_key = (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GG_API_KEY", "").strip()
    )
    if not api_key:
        raise RuntimeError(
            "Không tìm thấy GEMINI_API_KEY hoặc GG_API_KEY trong file .env."
        )

    model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
    client = get_gemini_client(api_key)
    interaction = client.interactions.create(
        model=model,
        input=build_action_plan_prompt(row),
    )
    if not interaction.output_text:
        raise RuntimeError("Gemini không trả về nội dung Action Plan.")
    return interaction.output_text


def render_kpi_row(items: list[tuple[str, str, str, str]] | list[tuple[str, str, str, str, str]]) -> None:
    """items: list of (label, value, accent_color, sub_caption[, icon])."""
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        label, value, accent, sub = item[:4]
        icon = item[4] if len(item) > 4 else ""
        with col:
            st.markdown(
                f"""
                <div class="kpi-card" style="--accent:{accent};">
                    <div class="kpi-top">
                        <div class="kpi-label">{label}</div>
                        <div class="kpi-icon">{icon}</div>
                    </div>
                    <div class="kpi-value">{value}</div>
                    <div class="kpi-sub">{sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_section(title: str, icon: str = "") -> None:
    icon_html = f'<span class="section-icon">{icon}</span>' if icon else ""
    st.markdown(
        f'<div class="section-block"><div class="section-title">{icon_html}{title}</div>'
        '<div class="section-rule"></div></div>',
        unsafe_allow_html=True,
    )


def build_quadrant_scatter(plot_df: pd.DataFrame) -> go.Figure:
    """Bản đồ chiến lược ROI Index (X) x Friction Score (Y), chia 4 góc phần
    tư theo trung vị của chính tập dữ liệu đang hiển thị — mỗi góc là một
    khuyến nghị triển khai, đúng với khung "vùng chiến lược" của đề tài.
    """
    # Tạo cột gộp tên Legend 
    plot_df = plot_df.copy()
    if "Canh_Bao" in plot_df.columns:
        risk_map = {"Đỏ": "Rủi ro cao", "Xanh": "An toàn", "Chưa đủ dữ liệu": "Thiếu dữ liệu"}
        plot_df["Mức rủi ro"] = plot_df["Canh_Bao"].map(risk_map).fillna(plot_df["Canh_Bao"])
    else:
        plot_df["Mức rủi ro"] = "An toàn"

    roi_median = plot_df["ROI Index"].median()
    friction_valid = plot_df["Friction Score"].dropna()
    friction_median = float(friction_valid.median()) if not friction_valid.empty else 50.0

    fig = px.scatter(
        plot_df,
        x="ROI Index",
        y="Friction Score",
        color="Strategy Zone",
        symbol="Mức rủi ro",  # Sử dụng tên đã map 
        size="Occupation Employment",
        size_max=28,
        color_discrete_map=STRATEGY_COLOR_MAP,
        hover_data={
            "Occupation (O*NET-SOC Title)": True,
            "Task": True,
            "Data Confidence": True,
            "Lý do chính": True,
            "Occupation Employment": False,
        },
    )

    # Cố định đỉnh Y cao hơn 
    y_top = 105.0
    x_left, x_right = -0.03, 1.03

    quadrants = [
        # (x0, x1, y0, y1, color, label, text_y_pos)
        (roi_median, x_right, 0, friction_median, COLOR_ROI_HIGH, 
         "Ưu tiên triển khai AI Agent", friction_median * 0.15),
        
        (roi_median, x_right, friction_median, y_top, COLOR_ROI_MED, 
         "Triển khai thận trọng\n(Quản trị phản ứng)", y_top - 4),
        
        (x_left, roi_median, 0, friction_median, COLOR_ROI_LOW, 
         "Chưa cấp thiết", friction_median * 0.15),
        
        (x_left, roi_median, friction_median, y_top, COLOR_RISK_RED, 
         "Không nên tự động hóa", y_top - 4),
    ]

    for x0, x1, y0, y1, color, label, text_y in quadrants:
        # Vẽ hình chữ nhật làm nền góc phần tư
        fig.add_shape(
            type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
            fillcolor=color, opacity=0.06, line_width=0, layer="below",
        )
        # Thêm nhãn tên góc phần tư với vị trí Y 
        fig.add_annotation(
            x=(x0 + x1) / 2, 
            y=text_y,
            text=label.replace("\n", "<br>"),  
            showarrow=False,
            font=dict(size=10, color=COLOR_TEXT_MUTED, family="Inter, sans-serif"),
            opacity=0.85,
            align="center",
        )

    # Đường phân cách Trung vị (Median)
    fig.add_vline(x=roi_median, line_dash="dot", line_color=COLOR_ROI_LOW, line_width=1)
    fig.add_hline(y=friction_median, line_dash="dot", line_color=COLOR_ROI_LOW, line_width=1)

    # Tăng margin top (t=50) và cố định dải hiển thị Y (range)
    fig.update_layout(
        height=450,
        plot_bgcolor=COLOR_SURFACE,
        paper_bgcolor=COLOR_SURFACE,
        font=dict(family="Inter, sans-serif", color=COLOR_TEXT),
        legend_title_text="Vùng chiến lược & Rủi ro",
        margin=dict(l=15, r=15, t=50, b=15),  # Tăng t lên 50 để rộng khoảng trên
        xaxis_title="ROI Index",
        yaxis_title="Friction Score",
    )
    fig.update_xaxes(range=[x_left, x_right], gridcolor=COLOR_BORDER)
    fig.update_yaxes(range=[-3, y_top + 2], gridcolor=COLOR_BORDER) # Khóa range Y chuẩn
    
    return fig


def build_strategy_zone_bar(df: pd.DataFrame) -> go.Figure:
    counts = df["Strategy Zone"].value_counts().reset_index()
    counts.columns = ["Vùng chiến lược", "Số task"]
    fig = px.bar(
        counts, x="Số task", y="Vùng chiến lược", orientation="h",
        color="Vùng chiến lược", color_discrete_map=STRATEGY_COLOR_MAP,
        text="Số task",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=420,
        plot_bgcolor=COLOR_SURFACE, paper_bgcolor=COLOR_SURFACE,
        font=dict(family="Inter, sans-serif", color=COLOR_TEXT),
        showlegend=False,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="", xaxis_title="Số task",
    )
    fig.update_xaxes(gridcolor=COLOR_BORDER)
    return fig


def build_agent_role_bar(df: pd.DataFrame) -> go.Figure:
    counts = df["Suggested AI Agent Role"].value_counts().reset_index()
    counts.columns = ["Vai trò AI Agent gợi ý", "Số task"]
    fig = px.bar(
        counts, x="Số task", y="Vai trò AI Agent gợi ý", orientation="h",
        text="Số task",
    )
    fig.update_traces(marker_color=COLOR_ACCENT, textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=420,
        plot_bgcolor=COLOR_SURFACE, paper_bgcolor=COLOR_SURFACE,
        font=dict(family="Inter, sans-serif", color=COLOR_TEXT),
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="", xaxis_title="Số task",
    )
    fig.update_xaxes(gridcolor=COLOR_BORDER)
    return fig


# ---------------------------------------------------------------------------
# 3. PAGE SETUP
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Agent Deployment Blueprint",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="app-banner">
        <div class="app-header">
            <span class="app-badge"></span>
            <h1>AI Agent Deployment Blueprint</h1>
        </div>
        <div class="app-subtitle">
            Giải pháp tối ưu ROI và quản trị lực cản nhân sự 
            trong quá trình áp dụng AI Agent cho ngành IT.
        </div>
        <div class="app-tags">
            <span class="app-tag"> ROI Index</span>
            <span class="app-tag"> Friction Score</span>
            <span class="app-tag"> Gợi ý AI Agent</span>
            <span class="app-tag"> Kỹ năng cần nâng cấp</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    data = load_merged_data()
except FileNotFoundError as exc:
    st.error(
        f"Không tìm thấy file dữ liệu: {exc}. Hãy chắc chắn it_master.csv, "
        "roi_index.csv, friction_score.csv đã có trong data/processed/."
    )
    st.stop()

# --- Sidebar: filter dùng chung cho cả 2 tab ---
st.sidebar.markdown('<div class="sidebar-title"> Bộ lọc dữ liệu</div>', unsafe_allow_html=True)
st.sidebar.markdown(
    '<div class="sidebar-caption">Áp dụng đồng thời cho cả Tab Doanh nghiệp và Tab Nhân sự.</div>',
    unsafe_allow_html=True,
)

occupations = sorted(data["Occupation (O*NET-SOC Title)"].dropna().unique())
selected_occupations = st.sidebar.multiselect(
    "Nghề (Occupation)", options=occupations, default=[],
    placeholder="Tất cả ngành nghề",
)

st.sidebar.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)

wage_min, wage_max = wage_bucket_bounds(data)
selected_wage = st.sidebar.slider(
    "Mức lương trung bình (USD/năm)",
    min_value=int(wage_min), max_value=int(wage_max),
    value=(int(wage_min), int(wage_max)), step=1000,
)

st.sidebar.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)

risk_options = ["Rủi ro cao (Đỏ)", "Rủi ro thấp (Xanh)", "Chưa đủ dữ liệu"]
selected_risk = st.sidebar.multiselect(
    "Mức rủi ro (Cảnh báo Friction)", options=risk_options, default=risk_options,
    placeholder="Chọn mức rủi ro",
)

filtered = data.copy()
if selected_occupations:
    filtered = filtered[filtered["Occupation (O*NET-SOC Title)"].isin(selected_occupations)]
filtered = filtered[
    filtered["Occupation Mean Annual Wage"].between(selected_wage[0], selected_wage[1])
    | filtered["Occupation Mean Annual Wage"].isna()
]
if selected_risk:
    filtered = filtered[filtered["Canh_Bao"].isin(selected_risk)]

st.sidebar.caption(f" Đang hiển thị **{len(filtered):,}** / {len(data):,} task")

tab1, tab2 = st.tabs(["Tab 1: Doanh nghiệp", "Tab 2: Nhân sự"])

# ---------------------------------------------------------------------------
# TAB 1 — DOANH NGHIỆP
# ---------------------------------------------------------------------------
with tab1:
    total_tasks = len(filtered)
    avg_roi = filtered["ROI Index"].mean(skipna=True)
    pct_automate_now = (
        (filtered["Strategy Zone"] == "Tự động hóa ngay").mean() * 100 if total_tasks else 0
    )
    pct_red = (filtered["Canh_Bao"] == "Đỏ").mean() * 100 if total_tasks else 0

    # CẬP NHẬT WORDING VÀ LABEL CHO KPI METRICS
    render_kpi_row([
        ("Tổng số task IT", f"{total_tasks:,}", COLOR_ACCENT, "Theo bộ lọc hiện tại", ""),
        ("ROI Index trung bình", f"{avg_roi:.2f}" if pd.notna(avg_roi) else "—",
         COLOR_ROI_HIGH, "Thang điểm 0.0 - 1.0", ""),
        ("Task ưu tiên tự động hóa", f"{pct_automate_now:.0f}%", COLOR_ROI_MED,
         "Thuộc nhóm \"Tự động hóa ngay\"", ""),
        ("Task rủi ro Friction cao", f"{pct_red:.0f}%", COLOR_RISK_RED,
         "Cần quản trị phản ứng nhân sự", ""),
    ])

    plot_df = filtered.dropna(subset=["ROI Index"]).copy()
    missing_friction = int(plot_df["Friction Score"].isna().sum())

    render_section("Bản đồ chiến lược: ROI Index x Friction Score", icon="")

    #  CHUYỂN DẠNG TOGGLE/CAROUSEL VIEW 
    if "tab1_chart_view" not in st.session_state:
        st.session_state.tab1_chart_view = "Bản đồ 4 góc phần tư"

    with st.container(border=True):
        col_title, col_toggle = st.columns([2.2, 1.8])
        
        # Mapping tiêu đề nhảy theo góc nhìn
        title_map = {
            "Bản đồ 4 góc phần tư": " Ma trận Chiến lược (ROI x Friction)",
            "Phân bố Vùng chiến lược": " Thống kê Phân bố Vùng chiến lược"
        }
        current_title = title_map.get(
            st.session_state.tab1_chart_view, 
            " Bản đồ chiến lược: ROI Index x Friction Score"
        )
        
        with col_title:
            st.markdown(f"### {current_title}")
            
        with col_toggle:
            selected_view_tab1 = st.radio(
                "Chọn góc nhìn Tab 1",
                options=["Bản đồ 4 góc phần tư", "Phân bố vùng chiến lược"],
                key="tab1_chart_view_radio",
                horizontal=True,
                label_visibility="collapsed",
            )
            st.session_state.tab1_chart_view = selected_view_tab1

        st.divider()

        # VIEW 1: SCATTER PLOT 4 GÓC PHẦN TƯ 
        if st.session_state.tab1_chart_view == "Bản đồ 4 góc phần tư":
            if plot_df.empty:
                st.info("Không có task nào khớp bộ lọc hiện tại.")
            else:
                st.plotly_chart(
                    build_quadrant_scatter(plot_df), 
                    use_container_width=True, 
                    key="tab1_scatter_quadrant"
                )
                if missing_friction:
                    st.caption(
                        f"ℹ️ {missing_friction} task có ROI Index nhưng chưa có Friction Score "
                        "(thiếu Expert hoặc Worker rating) — vẫn hiển thị, không loại bỏ."
                    )

        # VIEW 2: BIỂU ĐỒ CỘT THỐNG KÊ PHÂN BỐ 
        elif st.session_state.tab1_chart_view == "Phân bố Vùng chiến lược":
            if plot_df.empty:
                st.caption("Không có dữ liệu để hiển thị phân bố vùng chiến lược.")
            else:
                st.plotly_chart(
                    build_strategy_zone_bar(plot_df), 
                    use_container_width=True, 
                    key="tab1_bar_strategy"
                )

    # BẢNG CHI TIẾT THEO TASK 
    with st.expander("Xem bảng chi tiết theo task"):
        display_cols = [
            "Occupation (O*NET-SOC Title)", "Task", "ROI Index", "Strategy Zone",
            "Data Confidence", "Friction Score", "Canh_Bao", "Lý do chính",
        ]
        
        df_to_show = filtered[[c for c in display_cols if c in filtered.columns]].sort_values(
            "ROI Index", ascending=False, na_position="last"
        )

        st.dataframe(
            df_to_show,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Occupation (O*NET-SOC Title)": st.column_config.TextColumn("Vị trí công việc", width="medium"),
                "Task": st.column_config.TextColumn("Mô tả Task", width="large"),
                "ROI Index": st.column_config.NumberColumn("ROI Index", format="%.2f", width="small"),
                "Strategy Zone": st.column_config.TextColumn("Vùng chiến lược", width="medium"),
                "Data Confidence": st.column_config.NumberColumn("Độ tin cậy DL", format="%.2f", width="small"),
                "Friction Score": st.column_config.NumberColumn("Friction Score", format="%.1f", width="small"),
                "Canh_Bao": st.column_config.TextColumn("Mức rủi ro", width="small"),
                "Lý do chính": st.column_config.TextColumn("Yếu tố rủi ro (Friction)", width="large"),
            }
        )

# ---------------------------------------------------------------------------
# TAB 2 — NHÂN SỰ
# ---------------------------------------------------------------------------
with tab2:
    n_roles = filtered.loc[
        filtered["Suggested AI Agent Role"] != "Chưa xác định - cần xem xét thủ công",
        "Suggested AI Agent Role",
    ].nunique()
    pct_manual = (
        (filtered["Suggested AI Agent Role"] == "Chưa xác định - cần xem xét thủ công").mean() * 100
        if len(filtered) else 0
    )
    n_skill_tasks = int((filtered["Suggested Human Skills"] != "-").sum())

    # CẬP NHẬT WORDING KPI METRICS
    render_kpi_row([
        ("Vai trò AI Agent gợi ý", f"{n_roles}", COLOR_ACCENT, "Vai trò khác nhau", ""),
        ("Tỷ lệ task cần xem xét thủ công", f"{pct_manual:.0f}%", COLOR_ROI_LOW,
         "Chưa khớp quy tắc gợi ý", ""),
        ("Task cần nâng cao kỹ năng", f"{n_skill_tasks:,}", COLOR_ROI_MED,
         "Chỉ số Human Agency cao", ""),
    ])

    render_section("Phân tích chuyên sâu về Nhân sự", icon="")

    # 1. Khởi tạo state cho góc nhìn (mặc định chọn Vai trò AI)
    if "tab2_chart_view" not in st.session_state:
        st.session_state.tab2_chart_view = "Vai trò AI đề xuất"

    with st.container(border=True):
        col_title, col_toggle = st.columns([2.2, 1.8])
        
        # Mapping tiêu đề theo nút bấm (hoặc bạn có thể dùng 1 tên cố định)
        title_map = {
            "Vai trò AI đề xuất": "Phân bổ Vai trò AI Agent",
            "Yếu tố rủi ro (Friction)": "Yếu tố gây rủi ro Friction"
        }
        current_title = title_map.get(
            st.session_state.tab2_chart_view, 
            "Phân tích Vai trò AI Agent & Rủi ro Friction"
        )
        
        with col_title:
            st.markdown(f"### {current_title}")
            
        with col_toggle:
            selected_view = st.radio(
                "Chọn góc nhìn",
                options=["Vai trò AI đề xuất", "Yếu tố rủi ro (Friction)"],
                key="tab2_chart_view_radio",
                horizontal=True,
                label_visibility="collapsed",
            )
            st.session_state.tab2_chart_view = selected_view

        st.divider()

        # VIEW 1: BIỂU ĐỒ VAI TRÒ AI AGENT
        if st.session_state.tab2_chart_view == "Vai trò AI đề xuất":
            st.plotly_chart(build_agent_role_bar(filtered), use_container_width=True)

        # VIEW 2: BẢNG LÝ DO FRICTION CAO
        elif st.session_state.tab2_chart_view == "Yếu tố rủi ro (Friction)":
            high_friction = filtered[filtered["Canh_Bao"] == "Đỏ"].copy()
            if high_friction.empty:
                st.info("Không có task rủi ro cao trong bộ lọc hiện tại.")
            else:
                reason_map = {
                    "Lo ngại mất việc (Job Security)": "Lo ngại an toàn việc làm (Job Security)",
                    "Gắn bó/yêu thích task (Enjoyment)": "Mức độ gắn kết công việc (Enjoyment)",
                    "Chênh lệch AI làm được vs người lao động muốn": "Khoảng cách giữa năng lực AI & kỳ vọng",
                    "Muốn giữ vai trò con người (Control/Empathy/Ethical)": "Nhu cầu duy trì kiểm soát của con người",
                }
                if "Lý do chính" in high_friction.columns:
                    high_friction["Lý do chính"] = high_friction["Lý do chính"].replace(reason_map)

                reason_counts = (
                    high_friction["Lý do chính"].value_counts()
                    .rename_axis("Lý do chính").reset_index(name="Số task")
                )
                
                st.dataframe(
                    reason_counts,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Lý do chính": st.column_config.TextColumn(
                            "Yếu tố tạo ra rủi ro / kháng cự nhân sự", width="large"
                        ),
                        "Số task": st.column_config.NumberColumn(
                            "Số lượng task bị ảnh hưởng", format="%d task", width="medium"
                        ),
                    }
                )
    # Design cho phần Action Plan theo task
    render_section("Action Plan theo task", icon="")
    st.caption(
        "Chọn một task để hệ thống (AI Agent) tự động lập kế hoạch triển khai chi tiết "
        "dựa trên chỉ số ROI, Friction Score và vai trò AI đề xuất."
    )

    if "action_plan_task_key" not in st.session_state:
        st.session_state.action_plan_task_key = None
    if "action_plan_content" not in st.session_state:
        st.session_state.action_plan_content = None
    if "action_plan_error" not in st.session_state:
        st.session_state.action_plan_error = None

    task_col, plan_col = st.columns([1, 1.6], gap="large")

    with task_col:
        st.markdown("#### Danh sách task đang lọc")
        st.caption(f"{len(filtered):,} task phù hợp với bộ lọc hiện tại")

        with st.container(height=560, border=True):
            if filtered.empty:
                st.info("Không có task nào phù hợp với bộ lọc hiện tại.")

            for row_index, row in filtered.iterrows():
                task_key = str(row.get("Task ID", row_index))
                occupation = str(row.get("Occupation (O*NET-SOC Title)", ""))
                task_name = str(row.get("Task", "Task chưa có tên"))

                st.markdown(f"**{task_name}**")
                st.caption(occupation)
                if st.button(
                    "Tạo Action Plan",
                    key=f"create_action_plan_{task_key}_{row_index}",
                    use_container_width=True,
                    type=(
                        "primary"
                        if st.session_state.action_plan_task_key == task_key
                        else "secondary"
                    ),
                ):
                    st.session_state.action_plan_task_key = task_key
                    st.session_state.action_plan_content = None
                    st.session_state.action_plan_error = None
                    with st.spinner("AI Agent đang xây dựng Action Plan..."):
                        try:
                            st.session_state.action_plan_content = generate_action_plan(row)
                        except Exception as exc:
                            st.session_state.action_plan_error = str(exc)
                st.divider()

    with plan_col:
        selected_key = st.session_state.action_plan_task_key
        if selected_key is None:
            with st.container(height=560, border=True):
                st.markdown("#### Action Plan Chi Tiết")
                st.info("Vui lòng chọn **Tạo Action Plan** ở danh sách bên trái để xem kế hoạch chi tiết.")
        else:
            selected_rows = filtered[
                filtered.apply(
                    lambda item: str(item.get("Task ID", item.name)) == selected_key,
                    axis=1,
                )
            ]

            with st.container(border=True):
                header_col, clear_col = st.columns([4, 1])
                with header_col:
                    st.markdown("#### Action Plan Chi Tiết")
                with clear_col:
                    if st.button("Bỏ chọn", use_container_width=True):
                        st.session_state.action_plan_task_key = None
                        st.session_state.action_plan_content = None
                        st.session_state.action_plan_error = None
                        st.rerun()

                if selected_rows.empty:
                    st.warning(
                        "Task đã chọn không còn nằm trong bộ lọc hiện tại. "
                        "Hãy bấm **Bỏ chọn** hoặc điều chỉnh lại bộ lọc."
                    )
                else:
                    selected_row = selected_rows.iloc[0]
                    st.markdown(f"**{selected_row['Task']}**")
                    st.caption(selected_row["Occupation (O*NET-SOC Title)"])
                    st.divider()

                    if st.session_state.action_plan_error:
                        st.error(
                            "Không thể tạo Action Plan: "
                            f"{st.session_state.action_plan_error}"
                        )
                    elif st.session_state.action_plan_content:
                        st.markdown(st.session_state.action_plan_content)
                    else:
                        st.info("Đang chờ nội dung Action Plan...")

st.markdown(
    """
    <div class="app-footer">
        <span>Nguồn dữ liệu: WORKBank — it_master.csv, roi_index.csv, friction_score.csv</span>
    </div>
    """,
    unsafe_allow_html=True,
)