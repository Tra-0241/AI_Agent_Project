"""
app.py
Phụ trách: Thành viên 4 - Product/Dashboard Developer

Streamlit Dashboard 2 tab cho đề tài "AI Agent Deployment Blueprint":
- Tab 1 (Doanh nghiệp): bản đồ chiến lược ROI Index x Friction Score theo 4
  góc phần tư, KPI tổng quan, filter theo nghề / mức lương / mức rủi ro.
- Tab 2 (Nhân sự): gợi ý vai trò AI Agent & kỹ năng con người cần nâng cấp.

"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
DATA_DIR = ROOT_DIR / "data" / "processed"

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
    it_master = pd.read_csv(DATA_DIR / "it_master.csv")
    roi = pd.read_csv(DATA_DIR / "roi_index.csv")
    friction = pd.read_csv(DATA_DIR / "friction_score.csv")
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
    roi_median = plot_df["ROI Index"].median()
    friction_valid = plot_df["Friction Score"].dropna()
    friction_median = float(friction_valid.median()) if not friction_valid.empty else 50.0

    fig = px.scatter(
        plot_df,
        x="ROI Index",
        y="Friction Score",
        color="Strategy Zone",
        symbol="Canh_Bao",
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

    y_top = max(100.0, float(plot_df["Friction Score"].max(skipna=True) or 100) + 5)
    x_left, x_right = -0.03, 1.03

    quadrants = [
        (roi_median, x_right, friction_median, 0, COLOR_ROI_HIGH,
         "Ưu tiên triển khai AI Agent"),
        (roi_median, x_right, y_top, friction_median, COLOR_ROI_MED,
         "Triển khai thận trọng — quản lý phản ứng nhân sự"),
        (x_left, roi_median, friction_median, 0, COLOR_ROI_LOW,
         "Chưa cấp thiết"),
        (x_left, roi_median, y_top, friction_median, COLOR_RISK_RED,
         "Không nên tự động hóa sớm"),
    ]
    for x0, x1, y1, y0, color, label in quadrants:
        fig.add_shape(
            type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
            fillcolor=color, opacity=0.06, line_width=0, layer="below",
        )
        fig.add_annotation(
            x=(x0 + x1) / 2, y=y1 - (y1 - y0) * 0.06 if y1 > y0 else y1 + 4,
            text=label, showarrow=False,
            font=dict(size=10, color=COLOR_TEXT_MUTED), opacity=0.9,
        )

    fig.add_vline(x=roi_median, line_dash="dot", line_color=COLOR_ROI_LOW, line_width=1)
    fig.add_hline(y=friction_median, line_dash="dot", line_color=COLOR_ROI_LOW, line_width=1)

    fig.update_layout(
        height=420,
        plot_bgcolor=COLOR_SURFACE,
        paper_bgcolor=COLOR_SURFACE,
        font=dict(family="Inter, sans-serif", color=COLOR_TEXT),
        legend_title_text="Vùng chiến lược",
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="ROI Index",
        yaxis_title="Friction Score",
    )
    fig.update_xaxes(range=[x_left, x_right], gridcolor=COLOR_BORDER)
    fig.update_yaxes(gridcolor=COLOR_BORDER)
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
            Mô hình tối ưu hóa ROI kinh tế và quản trị lực cản nhân sự khi triển khai
            AI Agent trong khối ngành IT trong dữ liệu WORKBank.
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
    placeholder="Tất cả nghề IT",
)

st.sidebar.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)

wage_min, wage_max = wage_bucket_bounds(data)
selected_wage = st.sidebar.slider(
    "Mức lương trung bình (USD/năm)",
    min_value=int(wage_min), max_value=int(wage_max),
    value=(int(wage_min), int(wage_max)), step=1000,
)

st.sidebar.markdown('<hr class="sidebar-divider">', unsafe_allow_html=True)

risk_options = ["Đỏ", "Xanh", "Chưa đủ dữ liệu"]
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

    render_kpi_row([
        ("Tổng số task IT", f"{total_tasks:,}", COLOR_ACCENT, "sau khi áp bộ lọc", ""),
        ("ROI Index trung bình", f"{avg_roi:.2f}" if pd.notna(avg_roi) else "—",
         COLOR_ROI_HIGH, "thang 0.00 – 1.00", ""),
        ("Task ưu tiên tự động hóa", f"{pct_automate_now:.0f}%", COLOR_ROI_MED,
         "trong vùng \"Tự động hóa ngay\"", ""),
        ("Task cảnh báo Friction đỏ", f"{pct_red:.0f}%", COLOR_RISK_RED,
         "cần quản trị phản ứng nhân sự", ""),
    ])

    plot_df = filtered.dropna(subset=["ROI Index"]).copy()
    missing_friction = int(plot_df["Friction Score"].isna().sum())

    render_section("Bản đồ chiến lược: ROI Index x Friction Score", icon="")
    col_main, col_side = st.columns([2, 1])
    with col_main:
        with st.container(border=True):
            if plot_df.empty:
                st.info("Không có task nào khớp bộ lọc hiện tại.")
            else:
                st.plotly_chart(build_quadrant_scatter(plot_df), use_container_width=True)
                if missing_friction:
                    st.caption(
                        f"ℹ️ {missing_friction} task có ROI Index nhưng chưa có Friction Score "
                        "(thiếu Expert hoặc Worker rating) — vẫn hiển thị, không loại bỏ."
                    )
    with col_side:
        with st.container(border=True):
            if plot_df.empty:
                st.caption("Không có dữ liệu để hiển thị phân bố vùng chiến lược.")
            else:
                st.plotly_chart(build_strategy_zone_bar(plot_df), use_container_width=True)

    with st.expander("Xem bảng chi tiết theo task"):
        display_cols = [
            "Occupation (O*NET-SOC Title)", "Task", "ROI Index", "Strategy Zone",
            "Data Confidence", "Friction Score", "Canh_Bao", "Lý do chính",
        ]
        st.dataframe(
            filtered[[c for c in display_cols if c in filtered.columns]]
            .sort_values("ROI Index", ascending=False, na_position="last"),
            use_container_width=True, hide_index=True,
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

    render_kpi_row([
        ("Vai trò AI Agent gợi ý", f"{n_roles}", COLOR_ACCENT, "vai trò khác nhau", ""),
        ("Task cần xem xét thủ công", f"{pct_manual:.0f}%", COLOR_ROI_LOW,
         "chưa khớp luật gợi ý nào", ""),
        ("Task cần nâng kỹ năng người", f"{n_skill_tasks:,}", COLOR_ROI_MED,
         "Human Agency Rating cao", ""),
    ])

    render_section("Vai trò AI Agent được gợi ý nhiều nhất", icon="")
    col_role, col_reason = st.columns([1, 1])
    with col_role:
        with st.container(border=True):
            st.plotly_chart(build_agent_role_bar(filtered), use_container_width=True)
    with col_reason:
        with st.container(border=True):
            st.markdown("** Lý do chính khiến Friction cao (task cảnh báo đỏ)**")
            high_friction = filtered[filtered["Canh_Bao"] == "Đỏ"]
            if high_friction.empty:
                st.info("Không có task cảnh báo đỏ trong bộ lọc hiện tại.")
            else:
                reason_counts = (
                    high_friction["Lý do chính"].value_counts()
                    .rename_axis("Lý do chính").reset_index(name="Số task")
                )
                st.dataframe(reason_counts, use_container_width=True, hide_index=True)

    with st.expander("Xem bảng chi tiết gợi ý theo task"):
        tab2_cols = [
            "Occupation (O*NET-SOC Title)", "Task", "Suggested AI Agent Role",
            "Suggested Human Skills", "Friction Score", "Canh_Bao", "Lý do chính",
        ]
        st.dataframe(
            filtered[[c for c in tab2_cols if c in filtered.columns]],
            use_container_width=True, hide_index=True,
        )

st.markdown(
    """
    <div class="app-footer">
        <span>Nguồn dữ liệu: WORKBank — it_master.csv, roi_index.csv, friction_score.csv</span>
    </div>
    """,
    unsafe_allow_html=True,
)
