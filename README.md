# AI Agent Deployment Blueprint — Khối ngành IT

Mô hình tối ưu hóa ROI kinh tế và quản trị lực cản nhân sự khi triển khai AI Agent trong khối ngành IT, dựa trên bộ dữ liệu [WORKBank](https://huggingface.co/datasets/SALT-NLP/WORKBank).

## 1. Mục tiêu

- Đo lường **ROI Index**: mức độ đáng tự động hóa của từng task IT (dựa trên lương, số nhân sự, tần suất, khả năng AI làm được).
- Đo lường **Friction Score**: độ lệch pha giữa "AI làm được" (expert rating) và "người lao động muốn" (worker desire).
- Gợi ý **vai trò AI Agent** phù hợp cho từng nhóm task, và kỹ năng con người cần nâng cấp.
- Trực quan hóa toàn bộ qua **Streamlit Dashboard** 2 tab (Doanh nghiệp / Nhân sự).

## 2. Cấu trúc thư mục

```text
ai-agent-it-roi-dashboard/
├── app/
│   └── app.py                      # Streamlit Dashboard
│
├── data/
│   ├── raw/                        # Dữ liệu gốc từ WORKBank/O*NET
│   └── processed/                  # Dữ liệu sau xử lý (it_master.csv, ...)
│
├── docs/
│   ├── screenshots/                # Ảnh dashboard, biểu đồ phục vụ báo cáo
│   └── phan_cong_nhiem_vu.docx      # Phân công công việc nhóm
│
├── notebooks/
│   ├── 01_exploration.ipynb         # Khám phá dữ liệu (EDA)
│   ├── 02_ROI_Index.ipynb           # Xây dựng và kiểm tra ROI Index
│   └── 03_Friction_Score.ipynb      # Xây dựng và kiểm tra Friction Score
│
├── outputs/
│   ├── analysis/                   # Kết quả phân tích
│   ├── dictionaries/               # Data dictionary, mô tả biến
│   └── sensitivity/                # Kết quả phân tích độ nhạy
│
├── src/
│   ├── __init__.py
│   ├── agent_rules.py              # Luật gợi ý AI Agent & Action Plan
│   ├── data_processing.py          # Tiền xử lý và hợp nhất dữ liệu
│   ├── friction_score.py           # Tính Friction Score
│   ├── roi_index.py                # Tính ROI Index
│   └── sensitivity_analysis.py     # Phân tích độ nhạy Friction Score
│
├── tests/
│   ├── test_app_data_loading.py
│   ├── test_data_processing.py
│   ├── test_friction_score.py
│   └── test_roi_index.py
│
├── .streamlit/
│   └── config.toml                 # Cấu hình giao diện Streamlit
│
├── .gitignore
├── README.md
├── requirements.txt
└── tmp_save_chart_source.txt
```

## 3. Phân công (tương ứng file `phan_cong_nhiem_vu.docx`)

| Thành viên | Vai trò | File chính phụ trách |
|---|---|---|
| TV1 | Data Engineer | `src/data_processing.py` → xuất `data/processed/it_master.csv` |
| TV2 | Data Analyst (Kinh tế) | `src/roi_index.py` |
| TV3 | Data Analyst (Nhân sự & Rủi ro) | `src/friction_score.py` |
| TV4 | Product/Dashboard Developer | `src/agent_rules.py`, `app/app.py` |

Chi tiết nhiệm vụ xem trong `docs/phan_cong_nhiem_vu.docx`.

## 4. Cài đặt & chạy thử

```bash
# 1. Tạo môi trường ảo (khuyến nghị)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Cài thư viện
pip install -r requirements.txt

# 3. Đặt 4 file CSV gốc vào data/raw/
#    task_statement_with_metadata.csv
#    expert_rated_technological_capability.csv
#    domain_worker_desires.csv
#    domain_worker_metadata.csv

# 4. Chạy pipeline xử lý dữ liệu (tạo it_master.csv)
python -m src.data_processing

# 5. Chạy Streamlit Dashboard
streamlit run app/app.py
```

## 5. Deploy

Deploy miễn phí qua [Streamlit Community Cloud](https://streamlit.io/cloud):
1. Push repo này lên GitHub (public hoặc kết nối repo private).
2. Vào Streamlit Community Cloud → New app → chọn repo, branch `main`, file `app/app.py`.
3. Thêm 4 file CSV vào `data/raw/` trong repo (hoặc dùng cơ chế upload/secrets nếu dữ liệu nhạy cảm).

## 6. Nguồn dữ liệu

- https://huggingface.co/datasets/SALT-NLP/WORKBank
- https://futureofwork.saltlab.stanford.edu/
- https://github.com/SALT-NLP/workbank
