"""
app.py
Phụ trách: Thành viên 4 - Product/Dashboard Developer

Streamlit Dashboard 2 tab:
  - Tab 1 (Doanh nghiệp): bản đồ phân vùng task theo ROI Index & Friction Score
  - Tab 2 (Nhân sự): gợi ý vai trò AI Agent & kỹ năng cần học

Chạy: streamlit run app/app.py
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# Cho phép import từ src/ khi chạy `streamlit run app/app.py` ở thư mục gốc repo
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from src.agent_rules import build_agent_recommendation_table  # noqa: E402

PROCESSED_DIR = ROOT_DIR / "data" / "processed"

st.set_page_config(
    page_title="AI Agent Deployment Blueprint - IT",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_data():
    master = pd.read_csv(PROCESSED_DIR / "it_master.csv")
    roi = pd.read_csv(PROCESSED_DIR / "roi_index.csv")
    friction = pd.read_csv(PROCESSED_DIR / "friction_score.csv")

    combined = roi.merge(
        friction, on=["Occupation (O*NET-SOC Title)", "Task"], how="outer"
    )
    return master, combined


def sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Bộ lọc")

    occupations = sorted(df["Occupation (O*NET-SOC Title)"].dropna().unique())
    selected_occ = st.sidebar.multiselect("Nghề (Occupation)", occupations, default=occupations)

    zones = sorted(df.get("Strategy Zone", pd.Series(dtype=str)).dropna().unique())
    selected_zone = st.sidebar.multiselect("Vùng chiến lược", zones, default=zones) if zones else zones

    flags = sorted(df.get("Flag", pd.Series(dtype=str)).dropna().unique())
    selected_flag = st.sidebar.multiselect("Mức rủi ro (Friction Flag)", flags, default=flags) if flags else flags

    filtered = df[df["Occupation (O*NET-SOC Title)"].isin(selected_occ)]
    if selected_zone:
        filtered = filtered[filtered["Strategy Zone"].isin(selected_zone)]
    if selected_flag:
        filtered = filtered[filtered["Flag"].isin(selected_flag)]

    return filtered


def tab_business(df: pd.DataFrame):
    st.subheader("Bản đồ phân vùng Task theo ROI Index & Friction Score")

    col1, col2, col3 = st.columns(3)
    col1.metric("Số task đang xem", len(df))
    col2.metric("ROI Index trung bình", f"{df['ROI Index'].mean():.2f}" if "ROI Index" in df else "-")
    col3.metric("Friction Score trung bình", f"{df['Friction Score'].mean():.2f}" if "Friction Score" in df else "-")

    if {"ROI Index", "Friction Score"}.issubset(df.columns):
        fig = px.scatter(
            df,
            x="ROI Index",
            y="Friction Score",
            color="Strategy Zone" if "Strategy Zone" in df else None,
            hover_data=["Occupation (O*NET-SOC Title)", "Task"],
            title="ROI Index vs Friction Score theo Task",
        )
        st.plotly_chart(fig, use_container_width=True)

    if "Strategy Zone" in df.columns:
        bar_df = df.groupby("Strategy Zone").size().reset_index(name="Số task")
        fig_bar = px.bar(bar_df, x="Strategy Zone", y="Số task", title="Số lượng task theo vùng chiến lược")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.dataframe(df, use_container_width=True)


def tab_hr(master: pd.DataFrame):
    st.subheader("Gợi ý tính năng AI Agent & Kỹ năng cần học")

    recs = build_agent_recommendation_table(master)
    st.dataframe(recs, use_container_width=True)

    if "Suggested AI Agent Role" in recs.columns:
        role_counts = recs["Suggested AI Agent Role"].value_counts().reset_index()
        role_counts.columns = ["Vai trò AI Agent gợi ý", "Số lượng task"]
        fig = px.bar(
            role_counts,
            x="Số lượng task",
            y="Vai trò AI Agent gợi ý",
            orientation="h",
            title="Phân bổ vai trò AI Agent gợi ý",
        )
        st.plotly_chart(fig, use_container_width=True)


def main():
    st.title("AI Agent Deployment Blueprint — Khối ngành IT")
    st.caption(
        "Mô hình tối ưu hóa ROI kinh tế và quản trị lực cản nhân sự khi triển khai AI Agent"
    )

    try:
        master, combined = load_data()
    except FileNotFoundError:
        st.warning(
            "Chưa tìm thấy dữ liệu đã xử lý. Hãy chạy `python -m src.data_processing`, "
            "`python -m src.roi_index` và `python -m src.friction_score` trước."
        )
        st.stop()

    filtered = sidebar_filters(combined)

    tab1, tab2 = st.tabs(["📊 Tab 1 - Doanh nghiệp", "👥 Tab 2 - Nhân sự"])
    with tab1:
        tab_business(filtered)
    with tab2:
        tab_hr(master)


if __name__ == "__main__":
    main()
